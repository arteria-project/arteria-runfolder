import arteria
from arteria.web.handlers import BaseRestHandler
from runfolder.services import *
import tornado.web

class BaseRunfolderHandler(BaseRestHandler):
    """Provides core logic for all runfolder handlers"""
    def append_runfolder_link(self, runfolder_info):
        runfolder_info.link = self.create_runfolder_link(runfolder_info.path)

    def create_runfolder_link(self, path):
        return "{0:s}/runfolders/path{1:s}".format(self.api_link(), path)

    def initialize(self, runfolder_svc, config_svc):
        self.runfolder_svc = runfolder_svc
        self.config_svc = config_svc

class ListAvailableRunfoldersHandler(BaseRunfolderHandler):
    """Handles listing all available runfolders"""
    def get(self):
        """List all available runfolders"""
        runfolder_infos = list(self.runfolder_svc.list_available_runfolders())
        for runfolder_info in runfolder_infos:
            self.append_runfolder_link(runfolder_info)

        self.write_object(runfolder_infos)

class NextAvailableRunfolderHandler(BaseRunfolderHandler):
    def get(self):
        """Returns the next runfolder to process"""
        runfolder_info = self.runfolder_svc.next_runfolder()
        self.append_runfolder_link(runfolder_info)
        self.write_object(runfolder_info)

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
        Sets the state of the runfolder
        """
        self.runfolder_svc.set_runfolder_state(path, "TODO")

    @arteria.undocumented
    def put(self, path):
        """
        NOTE: put is provided for test purposes only.

        TODO: Discuss if it should be disabled in production
        """
        try:
            self.runfolder_svc.create_runfolder(path)
        except PathNotMonitored:
            raise tornado.web.HTTPError("400", "Path {0} is not monitored".format(path))

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
        self.runfolder_svc.add_sequencing_finished_marker(path)


