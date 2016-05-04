
import tornado.web


import arteria
from arteria.web.state import State
from arteria.exceptions import InvalidArteriaStateException
from arteria.web.handlers import BaseRestHandler
from runfolder.services import *



class BaseRunfolderHandler(BaseRestHandler):
    """Provides core logic for all runfolder handlers"""

    def data_received(self, chunk):
        """Empty implementation of abstract method"""
        pass

    def append_runfolder_link(self, runfolder_info):
        """
        Adds a new attribute (link) to the runfolder_info object, that points to
        the HTTP endpoint of the runfolder
        """
        runfolder_info.link = self.create_runfolder_link(runfolder_info.path)

    def create_runfolder_link(self, path):
        """Creates an HTTP endpoint from the path"""
        return "{0:s}/runfolders/path{1:s}".format(self.api_link(), path)

    def initialize(self, app_svc, runfolder_svc, config_svc):
        """Initializes the handler's member variables"""
        self.app_svc = app_svc
        self.runfolder_svc = runfolder_svc
        self.config_svc = config_svc


class ListAvailableRunfoldersHandler(BaseRunfolderHandler):
    """Handles listing all available runfolders"""
    def get(self):
        """
        List all runfolders that are ready. Add the query parameter 'state'
        for filtering. By default, state=READY is assumed. Query for state=* to
        get all monitored runfolders.
        """
        def get_runfolders():
            try:
                # TODO: This list should be paged. The unfiltered list can be large
                state = self.get_argument("state", State.READY)
                if state == "*":
                    state = None
                for runfolder_info in self.runfolder_svc.list_runfolders(state):
                    self.append_runfolder_link(runfolder_info)
                    yield runfolder_info
            except InvalidRunfolderState:
                raise tornado.web.HTTPError(400, "The state '{}' is not accepted".format(state))

        self.write_object({"runfolders": [runfolder.__dict__ for runfolder in get_runfolders()]})


class NextAvailableRunfolderHandler(BaseRunfolderHandler):
    """Handles fetching the next available runfolder"""
    def get(self):
        """
        Returns the next runfolder to process. Note that will not lock the runfolder, and unless it's
        state is changed by the polling client quickly enough it will be presented again.
        """
        runfolder_info = self.runfolder_svc.next_runfolder()
        if runfolder_info:
            self.append_runfolder_link(runfolder_info)
        self.write_object(runfolder_info)


class PickupAvailableRunfolderHandler(BaseRunfolderHandler):
    """Handles fetching the next available runfolder"""
    def get(self):
        """
        Returns the next runfolder to process and set it's state to PENDING.
        """
        runfolder_info = self.runfolder_svc.next_runfolder()
        if runfolder_info:
            self.append_runfolder_link(runfolder_info)
            self.runfolder_svc.set_runfolder_state(runfolder_info.path, State.PENDING)
            runfolder_info.state = State.PENDING
            self.write_object(runfolder_info)
        else:
            self.write(dict())


class RunfolderHandler(BaseRunfolderHandler):
    """Handles a particular runfolder, identified by path"""
    def get(self, path):
        """
        Returns information about the runfolder at the path.

        The runfolder must a subdirectory of a monitored path.
        """
        try:
            runfolder_info = self.runfolder_svc.get_runfolder_by_path(path)
            self.append_runfolder_link(runfolder_info)
            self.write_object(runfolder_info)
        except PathNotMonitored:
            raise tornado.web.HTTPError(400, "Searching an unmonitored path '{0}'".format(path))
        except DirectoryDoesNotExist:
            raise tornado.web.HTTPError(404, "Runfolder '{0}' does not exist".format(path))

    def post(self, path):
        """
        Sets the state of the runfolder. Note that it's currently assumed that only one
        process changes the status, so the access to the runfolder is not locked.

        Accepts the following JSON message: {"state": "[NONE|READY|STARTED|DONE|ERROR]"}

        Returns: 200 if the state changed successfully
        """
        json_body = self.body_as_object(["state"])
        state = json_body["state"]

        try:
            self.runfolder_svc.set_runfolder_state(path, state)
        except InvalidArteriaStateException:
            raise tornado.web.HTTPError(400, "The state '{}' is not valid".format(state))

    @arteria.undocumented
    def put(self, path):
        """
        Creates the runfolder at the path.

        Enabled in debug mode only, to support integration tests.
        """
        try:
            self.runfolder_svc.create_runfolder(path)
            self.set_status(201, "Created a new runfolder")
        except PathNotMonitored:
            raise tornado.web.HTTPError(400, "Path {0} is not monitored".format(path))
        except ActionNotEnabled:
            raise tornado.web.HTTPError(400, "The action is not enabled")
        except DirectoryAlreadyExists:
            raise tornado.web.HTTPError(400, "Directory exists")


class TestFakeSequencerReadyHandler(BaseRunfolderHandler):
    """
    Handles setting the sequencing finished marker

    This is provided for integration tests only
    """

    @arteria.undocumented
    def put(self, path):
        """
        Marks the runfolder at the path as ready
        """
        try:
            self.runfolder_svc.add_sequencing_finished_marker(path)
        except ActionNotEnabled:
            raise tornado.web.HTTPError(400, "The action is not enabled")

