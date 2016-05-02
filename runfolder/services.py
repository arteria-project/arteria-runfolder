import os.path
import socket
import logging
from runfolder import __version__ as version


class Enum(set):
    """
    Defines an enumeration which values are a string representation of the
    specified attribute, i.e. EnumInstance.VAL1 == "VAL1"

    Usage: EnumInstance = Enum(["VAL1", "VAL2"])

    print EnumInstance.VAL1
    > "VAL1"

    if "VAL3" not in EnumInstance:
        raise ...
    """
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

    def __setattr__(self, key, value):
        raise NotImplementedError("Values cannot be set directly")

"""
NONE: Not ready for processing or invalid
READY: Ready for processing
STARTED: Started processing the runfolder
DONE: Done processing the runfolder
ERROR: Started processing the runfolder but there was an error
"""
RunfolderState = Enum(["NONE", "READY", "STARTED", "DONE", "ERROR"])


class RunfolderInfo:
    """
    Information about a runfolder. Status must be defined in RunfolderState:
    """

    def __init__(self, host, path, state):
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
        info = RunfolderInfo(self._host(), path, self.get_runfolder_state(path))
        return info

    def _get_runfolder_state_from_state_file(self, runfolder):
        """
        Reads the state in the state file at .arteria/state, returns
        RunfolderState.NONE if nothing is available
        """
        state_file = os.path.join(runfolder, ".arteria", "state")
        if self._file_exists(state_file):
            with open(state_file, 'r') as f:
                state = f.read()
                state = state.strip()
                return state
        else:
            return RunfolderState.NONE

    def get_runfolder_state(self, runfolder):
        """
        Returns the state of a runfolder. The possible states are defined in
        RunfolderState

        If the file .arteria/state exists, it will determine the state. If it doesn't
        exist, the existence of the marker file RTAComplete.txt determines the state.
        """
        state = self._get_runfolder_state_from_state_file(runfolder)
        if state == RunfolderState.NONE:
            completed_marker = os.path.join(runfolder, "RTAComplete.txt")
            ready = self._file_exists(completed_marker)
            if ready:
                state = RunfolderState.READY
        return state

    @staticmethod
    def validate_state(state):
        """Raises InvalidRunfolderState if the state is not known"""
        if state not in RunfolderState:
            raise InvalidRunfolderState("The state '{}' is not valid".format(state))

    @staticmethod
    def set_runfolder_state(runfolder, state):
        """Sets the state of a runfolder"""
        RunfolderService.validate_state(state)
        arteria_dir = os.path.join(runfolder, ".arteria")
        state_file = os.path.join(arteria_dir, "state")
        if not os.path.exists(arteria_dir):
            os.makedirs(arteria_dir)
        with open(state_file, 'w') as f:
            f.write(state)

    def is_runfolder_ready(self, directory):
        """Returns True if the runfolder is ready"""
        state = self.get_runfolder_state(directory)
        self._logger.debug("Checking {0}. state={1}".format(directory, state))
        return state == RunfolderState.READY

    def _monitored_directories(self):
        """Lists all directories monitored for new runfolders"""
        monitored = self._configuration_svc["monitored_directories"]

        if (monitored is not None) and (type(monitored) is not list):
            raise ConfigurationError("monitored_directories must be a list")

        for directory in monitored:
            yield os.path.abspath(directory)

    def next_runfolder(self):
        """Returns the next available runfolder. Returns None if there is none available."""
        available = self.list_runfolders(state=RunfolderState.READY)
        try:
            first = available.next()
        except StopIteration:
            first = None

        self._logger.info(
            "Searching for next available runfolder, found: {0}".format(first))
        return first

    def list_available_runfolders(self):
        return self.list_runfolders(RunfolderState.READY)

    def list_runfolders(self, state):
        """
        Lists all the runfolders on the host, filtered by state. State
        can be any of the values in RunfolderState. Specify None for no filtering.
        """
        runfolders = self._enumerate_runfolders()
        if state:
            RunfolderService.validate_state(state)
            return (runfolder for runfolder in runfolders if runfolder.state == state)
        else:
            return runfolders

    def get_settings(self):
        """
        Returns the settings of the service.
        """
        settings = self._configuration_svc.get_app_config()

        # The monitored_directories can be relative. Callers will be interested in the absolute path.
        settings["monitored_directories"] = list(self._monitored_directories())
        return self._configuration_svc.get_app_config()

    def _enumerate_runfolders(self):
        """Enumerates all runfolders in any monitored directory"""
        for monitored_root in self._monitored_directories():
            self._logger.debug("Checking subdirectories of {0}".format(monitored_root))
            for subdir in self._subdirectories(monitored_root):
                directory = os.path.join(monitored_root, subdir)
                self._logger.debug("Found potential runfolder {0}".format(directory))
                state = self.get_runfolder_state(directory)
                info = RunfolderInfo(self._host(), directory, state)
                yield info

    def _requires_enabled(self, config_key):
        """Raises an ActionNotEnabled exception if the specified config value is false"""
        if not self._configuration_svc[config_key]:
            raise ActionNotEnabled("The action {0} is not enabled".format(config_key))


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

