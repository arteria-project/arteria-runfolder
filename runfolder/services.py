import os.path
import socket
import logging

class RunfolderInfo:
    """Information about a runfolder. Status can be:
            none: Not ready for processing or invalid
            ready: Ready for processing by Arteria
            started: Arteria started processing the runfolder
            done: Arteria is done processing the runfolder
            error: Arteria started processing the runfolder but there was an error
    """

    STATE_NONE = "none"
    STATE_READY = "ready"
    STATE_STARTED = "started"
    STATE_DONE = "done"
    STATE_ERROR = "error"

    def __init__(self, host, path, state):
        self.host = host
        self.path = path
        self.state = state

    def __str__(self):
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
        monitored = any([path.startswith(mon) for mon in self._monitored_directories()])
        if not monitored:
            raise PathNotMonitored("The path {0} is not being monitored".format(path))

    def create_runfolder(self, path):
        """
        Creates a runfolder at the path.

        Provided for integration tests only.

        :raises PathNotMonitored
        :raises DirectoryAlreadyExists
        """
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

        Provided for integration tests only.

        :raises DirectoryDoesNotExist
        :raises CannotOverrideFile
        """
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
        RunfolderInfo.STATE_NONE if nothing is available
        """
        state_file = os.path.join(runfolder, ".arteria", "state")
        if self._file_exists(state_file):
            with open(state_file, 'r') as f:
                state = f.read()
                state = state.strip()
                return state
        else:
            return RunfolderInfo.STATE_NONE

    def get_runfolder_state(self, runfolder):
        """
        Returns the state of a runfolder. The possible states are defined in
        RunfolderInfo.STATE_*.

        If the file .arteria/state exists, it will determine the state. If it doesn't
        exist, the existence of the marker file RTAComplete.txt determines the state.
        """
        state = self._get_runfolder_state_from_state_file(runfolder)
        if state == RunfolderInfo.STATE_NONE:
            completed_marker = os.path.join(runfolder, "RTAComplete.txt")
            ready = self._file_exists(completed_marker)
            if ready:
                state = RunfolderInfo.STATE_READY
        return state

    @staticmethod
    def set_runfolder_state(runfolder, state):
        """Sets the state of a runfolder"""
        arteria_dir = os.path.join(runfolder, ".arteria")
        state_file = os.path.join(arteria_dir, "state")
        if not os.path.exists(arteria_dir):
            os.makedirs(arteria_dir)
        with open(state_file, 'w') as f:
            f.write(state)

    def is_runfolder_ready(self, directory):
        state = self.get_runfolder_state(directory)
        self._logger.debug("Checking {0}. state={1}".format(directory, state))
        return state == RunfolderInfo.STATE_READY

    def _monitored_directories(self):
        return self._configuration_svc["monitored_directories"]

    def next_runfolder(self):
        """Pulls for available run folders"""
        available = self.list_available_runfolders()
        try:
            first = available.next()
        except StopIteration:
            first = None

        self._logger.info(
            "Searching for next available runfolder, found: {0}".format(first))
        return first

    def list_available_runfolders(self):
        """Lists all the available runfolders on the host"""
        self._logger.debug("get_available_runfolder")
        for monitored_root in self._monitored_directories():
            self._logger.debug("Checking subdirectories of {0}".format(monitored_root))
            for subdir in self._subdirectories(monitored_root):
                directory = os.path.join(monitored_root, subdir)
                self._logger.debug("Found potential runfolder {0}".format(directory))
                state = self.get_runfolder_state(directory)
                if state == RunfolderInfo.STATE_READY:
                    info = RunfolderInfo(self._host(),
                                         directory, RunfolderInfo.STATE_READY)
                    yield info

class CannotOverrideFile(Exception):
    pass

class DirectoryDoesNotExist(Exception):
    pass

class PathNotMonitored(Exception):
    pass

class DirectoryAlreadyExists(Exception):
    pass

