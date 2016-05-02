import unittest
import time
from arteria.testhelpers import TestFunctionDelta, BaseRestTest
import os
import logging
import requests
import jsonpickle
import mock
from runfolder.services import RunfolderState

log = logging.getLogger(__name__)


class RestApiTestCase(BaseRestTest):
    def _base_url(self):
        # TODO: It would be clearer to share these settings via a config file
        key = "ARTERIA_RUNFOLDER_SVC_URL"
        if key in os.environ:
            return os.environ[key]
        else:
            return "http://localhost:10800/api/1.0"

    def _get_monitored_dir(self):
        key = "ARTERIA_RUNFOLDER_MONITORED_DIR"
        if key in os.environ:
            return os.environ[key]
        else:
            path_to_test_dir = os.path.dirname(os.path.realpath(__file__))
            return "{0}/monitored".format(path_to_test_dir)

    def _get_log_file_path(self):
        key = "ARTERIA_RUNFOLDER_LOG_FILE"
        if key in os.environ:
            return os.environ[key]
        else:
            return "./runfolder.log"

    # NOTE: Also tests log files, so currently needs to run from the server
    # itself, and the log files being tested against are assumed to be small
    # These tests are intended to be full integration tests, mocking nothing
    def setUp(self):
        def line_count(path):
            count = 0
            for _ in open(path).xreadlines():
                count += 1
            return count

        # Disable the log check if not running locally:
        if not self._base_url().startswith("http://localhost"):
            self.messages_logged = mock.MagicMock()
            self.messages_logged.assert_changed_by_total = lambda x: None
        else:
            self.messages_logged = TestFunctionDelta(
                lambda: line_count(self._get_log_file_path()), self, 0.1)

    def test_can_change_log_level(self):
        self.put("./admin/log_level", {"log_level": "DEBUG"})
        resp = self.get("./admin/log_level")
        self.assertEqual(resp.body_obj["log_level"], "DEBUG")

        # For the rest of the test, and by default, we should have log level WARNING
        self.put("./admin/log_level", {"log_level": "WARNING"})

    def test_next_throws_no_error_if_empty(self):
        """
        Regression test: Calling next when the list of items is empty
        resulted in a 500 error, rather than returning None

        NOTE: This test assumes synchronous testing. If other tests add
        runfolders in the ready state while this is running, it might fail
        """

        self._mark_all_runfolders(RunfolderState.STARTED)

        # Ensure that we don't get an error message from /next:
        resp = self.get("./runfolders/next", expect=200)

        self.assertTrue(resp.body_obj is None)

    def test_not_monitored_path_returns_400(self):
        self.get("./runfolders/path/notmonitored/dir/", expect=400)
        # Tornado currently writes two entries for 400, for tornado.general and tornado.access
        self.messages_logged.assert_changed_by_total(3)

    def test_can_create_and_update_state(self):
        # First, we want to make sure it's not there now, resulting in 404 warn log:
        file_postfix = int(1000 * time.time())
        # Ensure that we can create a random runfolder at one of the mountpoints
        path = "{0}/runfolder_inttest_{1}".format(self._get_monitored_dir(), file_postfix)

        self.get("./runfolders/path{0}".format(path), expect=404)

        # Now, create the folder
        self.put("./runfolders/path{0}".format(path), expect=201)
        # Create the complete marker
        self.put("./runfolders/test/markasready/path{0}".format(path))

        # The runfolder should show up in /runfolders
        resp = self.get("./runfolders")
        runfolders = resp.body_obj["runfolders"]
        matching = [runfolder for runfolder in runfolders if runfolder["path"] == path]
        self.assertEqual(len(matching), 1)

        # TODO: Change state to "processing" and ensure it doesn't show up in /runfolders
        self.messages_logged.assert_changed_by_total(2)

    def test_updating_state_removes_runfolder_from_candidates(self):
        """
        Gets a list of runfolders ready for processing, fetches the
        runfolder that should be processed next, marks it as ready
        and then ensures that the runfolder doesn't show up in the
        list of all runfolders
        """
        path = self._create_ready_runfolder()
        self.assertTrue(self._exists(path))
        # Mark the folder as processing
        self.post("./runfolders/path{}".format(path), {"state": "STARTED"}, expect=200)
        # Ensure that the folder is not listed anymore:
        self.assertFalse(self._exists(path))

    def test_invalid_state_is_not_accepted(self):
        path = self._create_ready_runfolder()
        self.assertTrue(self._exists(path))
        self.post("./runfolders/path{}".format(path), {"state": "NOT-AVAILABLE"}, expect=400)

    def _mark_all_runfolders(self, state):
        resp = self.get("./runfolders")
        runfolders = resp.body_obj["runfolders"]
        for runfolder in runfolders:
            self.post("./runfolders/path{}".format(runfolder["path"]), {"state": state}, expect=200)

    def _exists(self, path):
        resp = self.get("./runfolders")
        runfolders = resp.body_obj["runfolders"]
        matching = len([runfolder for runfolder in runfolders if runfolder["path"] == path]) == 1
        return matching

    def _create_ready_runfolder(self):
        file_postfix = int(1000 * time.time())
        path = "{0}/runfolder_inttest_{1}".format(self._get_monitored_dir(), file_postfix)
        self.put("./runfolders/path{0}".format(path), expect=201)
        self.put("./runfolders/test/markasready/path{0}".format(path))
        return path

    def post(self, relative_url, obj, expect=200):
        # TODO: Add to base object
        full_url = self._get_full_url(relative_url)
        json = jsonpickle.encode(obj)
        resp = requests.post(full_url, json)
        self._validate_response(resp, expect)


if __name__ == '__main__':
    unittest.main()
