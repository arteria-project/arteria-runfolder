import os.path
import socket
import logging
import time
import xmltodict
from runfolder import __version__ as version

from arteria.web.state import State
from arteria.web.state import validate_state
from runfolder.lib.instrument import InstrumentFactory

class RunfolderInfo:
    """
    Information about a runfolder. Status must be defined in RunfolderState:
    """

    def __init__(self, host, path, state, metadata):
        """
        Initializes the object

        :param host: The host where the runfolder exists
        :param path: The file system path to the runfolder on the host
        :param state: The state of the runfolder (see RunfolderState)
        """

        self.host = host
        self.path = path
        self.state = state
        self.service_version = version
        self.metadata = metadata

    def __repr__(self):
        return "{0}: {1}@{2}".format(self.state, self.path, self.host)


class RunfolderService:
    """Watches a set of directories on the server and reacts when one of them
       has a runfolder that's ready for processing"""

    def __init__(self, configuration_svc, logger=None):
        self._configuration_svc = configuration_svc
        self._logger = logger or logging.getLogger(__name__)

    # NOTE: These methods were added so that they could be easily mocked out.
    #       It would probably be nicer to move them inline and mock the system calls
    #       or have them in a separate provider class required in the constructor
    @staticmethod
    def _host():
        return socket.gethostname()

    @staticmethod
    def _file_exists(path):
        return os.path.isfile(path)

    @staticmethod
    def _file_exists_and_is_older_than(path, minutes):
        if not os.path.isfile(path):
            return False

        modification_time = os.path.getmtime(path)
        return (time.time() - modification_time) >= minutes * 60

    @staticmethod
    def _dir_exists(path):
        return os.path.isdir(path)

    @staticmethod
    def _subdirectories(path):
        return os.listdir(path)

    def _validate_is_being_monitored(self, path):
        """
        Validate that this is a subdirectory (potentially non-existing)
        of a monitored path

        :raises PathNotMonitored
        """
        def is_parent_dir(parent_dir, child_dir):
            actual_parent = os.path.split(child_dir)[0]
            return os.path.normpath(parent_dir) == actual_parent

        monitored = list(self._monitored_directories())
        is_monitored = any([is_parent_dir(mon, path) for mon in monitored])
        if not is_monitored:
            self._logger.warn("Validation error: {} is not monitored {}".format(path, monitored))
            raise PathNotMonitored(
                "The path '{}' is not being monitored.".format(path))

    def create_runfolder(self, path):
        """
        Creates a runfolder at the path.

        Provided for integration tests only and only available if the
        config value can_create_runfolder is True.

        :raises PathNotMonitored
        :raises DirectoryAlreadyExists
        """
        self._requires_enabled("can_create_runfolder")
        self._validate_is_being_monitored(path)
        if os.path.exists(path):
            raise DirectoryAlreadyExists("The path {0} already exists and can't be overridden".format(path))
        os.makedirs(path)
        self._logger.info(
            "Created a runfolder at {0} - intended for tests only".format(path))
        runparameters_path = os.path.join(path, "runParameters.xml")
        if os.path.isfile(runparameters_path):
            raise CannotOverrideFile("runParameters.xml already exists at {0}".format(runparameters_path))

        runparameters_dict = {
                'RunParameters': {
                        'ReagentKitBarcode': 'AB1234567-123V1',
                        'RfidsInfo': {
                                'LibraryTubeSerialBarcode': 'NV0012345-LIB'
                            },
                        'ScannerID': 'M04499'
                    }
            }

        output_xml = xmltodict.unparse(runparameters_dict, pretty=True)

        with open(runparameters_path, 'a') as f:
            f.write(output_xml)

        self._logger.info(
            "Added 'runParameters.xml' to '{0}' - intended for tests only".format(runparameters_path))


    def add_sequencing_finished_marker(self, path):
        """
        Adds the marker that sets the `ready` state of a runfolder.
        This marker is generally added by the sequencer

        Provided for integration tests only and only available if the config value
        can_create_runfolder is set to True.

        :raises DirectoryDoesNotExist
        :raises CannotOverrideFile
        """
        self._requires_enabled("can_create_runfolder")
        if not os.path.isdir(path):
            raise DirectoryDoesNotExist(
                "The path '{0}' is not an existing directory".format(path))

        full_path = os.path.join(path, "RTAComplete.txt")
        if os.path.isfile(full_path):
            raise CannotOverrideFile("The complete marker already exists at {0}".format(full_path))

        open(full_path, 'a').close()
        self._logger.info(
            "Added the 'RTAComplete.txt' marker to '{0}' - intended for tests only".format(full_path))

    def get_runfolder_by_path(self, path):
        """
        Returns a RunfolderInfo by its Linux file path

        :raises PathNotMonitored
        :raises DirectoryDoesNotExist
        """
        self._logger.debug("get_runfolder_by_path({0})".format(path))
        self._validate_is_being_monitored(path)

        if not self._dir_exists(path):
            raise DirectoryDoesNotExist("Directory does not exist: '{0}'".format(path))
        info = RunfolderInfo(self._host(), path, self.get_runfolder_state(path),
                             self.get_metadata(path))
        return info

    def _get_runfolder_state_from_state_file(self, runfolder):
        """
        Reads the state in the state file at .arteria/state, returns
        State.NONE if nothing is available
        """
        state_file = os.path.join(runfolder, ".arteria", "state")
        if self._file_exists(state_file):
            with open(state_file, 'r') as f:
                state = f.read()
                state = state.strip()
                return state
        else:
            return State.NONE

    def get_runfolder_state(self, runfolder):
        """
        Returns the state of a runfolder. The possible states are defined in
        State

        If the file .arteria/state exists, it will determine the state. If it doesn't
        exist, the existence of the marker file RTAComplete.txt determines the state.
        """
        instrument = InstrumentFactory.get_instrument(self.read_run_parameters(runfolder))
        completed_marker_file = instrument.completed_marker_file()
        completed_grace_minutes = None
        try:
            completed_grace_minutes = self._configuration_svc["completed_marker_grace_minutes"]
        except KeyError:
            pass

        if completed_grace_minutes is None:
            completed_grace_minutes = 0
        state = self._get_runfolder_state_from_state_file(runfolder)
        if state == State.NONE:
            ready = True
            completed_marker = os.path.join(runfolder, completed_marker_file)
            if not self._file_exists_and_is_older_than(completed_marker, completed_grace_minutes):
                ready = False
            if ready:
                state = State.READY
        return state

    @staticmethod
    def set_runfolder_state(runfolder, state):
        """
        Sets the state of a runfolder

        :raises DirectoryDoesNotExist
        """
        validate_state(state)
        arteria_dir = os.path.join(runfolder, ".arteria")
        state_file = os.path.join(arteria_dir, "state")

        if not os.path.exists(runfolder):
            raise DirectoryDoesNotExist(
                    "Directory does not exist: '{0}'".format(runfolder))

        if not os.path.exists(arteria_dir):
            os.makedirs(arteria_dir)

        with open(state_file, 'w') as f:
            f.write(state)

    def is_runfolder_ready(self, directory):
        """Returns True if the runfolder is ready"""
        state = self.get_runfolder_state(directory)
        return state == State.READY

    def _monitored_directories(self):
        """Lists all directories monitored for new runfolders"""
        monitored = self._configuration_svc["monitored_directories"]

        if (monitored is not None) and (type(monitored) is not list):
            raise ConfigurationError("monitored_directories must be a list")

        for directory in monitored:
            yield os.path.abspath(directory)

    def next_runfolder(self):
        """Returns the next available runfolder. Returns None if there is none available."""
        available = self.list_runfolders(state=State.READY)
        try:
            first = next(available)
        except StopIteration:
            first = None

        self._logger.info(
            "Searching for next available runfolder, found: {0}".format(first))
        return first

    def list_available_runfolders(self):
        return self.list_runfolders(State.READY)

    def list_runfolders(self, state):
        """
        Lists all the runfolders on the host, filtered by state. State
        can be any of the values in RunfolderState. Specify None for no filtering.
        """
        runfolders = self._enumerate_runfolders()
        if state:
            validate_state(state)
            return (runfolder for runfolder in runfolders if runfolder.state == state)
        else:
            return runfolders

    def _enumerate_runfolders(self):
        """Enumerates all runfolders in any monitored directory"""
        for monitored_root in self._monitored_directories():
            self._logger.debug("Checking subdirectories of {0}".format(monitored_root))
            for subdir in self._subdirectories(monitored_root):
                directory = os.path.join(monitored_root, subdir)
                self._logger.debug("Found potential runfolder {0}".format(directory))
                state = self.get_runfolder_state(directory)
                info = RunfolderInfo(self._host(), directory, state,
                                     self.get_metadata(directory))
                yield info

    def _requires_enabled(self, config_key):
        """Raises an ActionNotEnabled exception if the specified config value is false"""
        if not self._configuration_svc[config_key]:
            raise ActionNotEnabled("The action {0} is not enabled".format(config_key))

    def get_metadata(self, path):
        run_parameters = self.read_run_parameters(path)
        reagent_kit_barcode = self.get_reagent_kit_barcode(path, run_parameters)
        library_tube_barcode = self.get_library_tube_barcode(path, run_parameters)
        metadata = {}
        if reagent_kit_barcode:
            metadata['reagent_kit_barcode'] = reagent_kit_barcode
        if library_tube_barcode:
            metadata['library_tube_barcode'] = library_tube_barcode
        return metadata


    def get_reagent_kit_barcode(self, path, run_parameters):
        try:
            barcode = run_parameters['RunParameters']['ReagentKitBarcode']
        except KeyError:
            # Reagent kit barcode is not available for all run types,
            # it is therefore expected to not be found in all cases
            self._logger.debug("Reagent kit barcode not found")
            return None
        except TypeError:
            self._logger.debug("[Rr]unParameters.xml not found")
            return None
        return barcode

    def get_library_tube_barcode(self, path, run_parameters):
        try:
            barcode = run_parameters['RunParameters']['RfidsInfo']['LibraryTubeSerialBarcode']
        except KeyError:
            try:
                # Novaseq X Plus barcode is located in ConsumableInfo -> SerialNumber where type is SampleTube
                consumables = run_parameters["RunParameters"]["ConsumableInfo"]["ConsumableInfo"]
                barcode = next(
                    (
                        consumable["SerialNumber"]
                        for consumable in consumables
                        if consumable['Type'] == "SampleTube"
                    ),
                    None,
                )
            except KeyError:
                # Library tube barcode is not available for all run types,
                # it is therefore expected to not be found in all cases
                self._logger.debug("Library tube barcode not found")
                return None
        except TypeError:
            self._logger.debug("[Rr]unParameters.xml not found")
            return None
        return barcode

    def read_run_parameters(self, path):
        alt_1 = os.path.join(path, "runParameters.xml")
        alt_2 = os.path.join(path, "RunParameters.xml")
        if os.path.exists(alt_1):
            with open(alt_1) as f:
                return xmltodict.parse(f.read())
        elif os.path.exists(alt_2):
            with open(alt_2) as f:
                return xmltodict.parse(f.read())
        else:
            return None

class CannotOverrideFile(Exception):
    pass


class DirectoryDoesNotExist(Exception):
    pass


class PathNotMonitored(Exception):
    pass


class DirectoryAlreadyExists(Exception):
    pass


class ActionNotEnabled(Exception):
    pass


class InvalidRunfolderState(Exception):
    pass


class ConfigurationError(Exception):
    pass
