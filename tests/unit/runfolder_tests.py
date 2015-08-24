import unittest
import logging
from runfolder.services import RunfolderService

logger = logging.getLogger(__name__)

class RunfolderServiceTestCase(unittest.TestCase):

    def _valid_runfolder(self, path):
        if path.endswith("RTAComplete.txt"):
            return True
        elif path.endswith(".arteria/state"):
            return False
        else:
            raise Exception("Unexpected path")

    def test_list_available_runfolders(self):
        # Setup
        configuration_svc = {
            "monitored_directories": [
                "/data/testarteria1/mon1",
                "/data/testarteria1/mon2"
            ]
        }
        runfolder_svc = RunfolderService(configuration_svc, logger)

        runfolder_svc._file_exists = self._valid_runfolder
        runfolder_svc._subdirectories = lambda path: ["runfolder001"]
        runfolder_svc._host = lambda: "localhost"

        # Test
        runfolders = runfolder_svc.list_available_runfolders()
        runfolders = list(runfolders)
        self.assertEqual(len(runfolders), 2)

        runfolders_str = sorted([str(runfolder) for runfolder in runfolders])
        expected = ["ready: /data/testarteria1/mon1/runfolder001@localhost",
                    "ready: /data/testarteria1/mon2/runfolder001@localhost"]
        self.assertEqual(runfolders_str, expected)

    def test_next_runfolder(self):
        # Setup
        configuration_svc = {
            "monitored_directories": [
                "/data/testarteria1/mon1"
            ]
        }

        # Since keys in configuration_svc can be directly indexed, we can mock it with a dict:
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runfolder_svc._file_exists = self._valid_runfolder
        runfolder_svc._subdirectories = lambda path: ["runfolder001"]
        runfolder_svc._host = lambda: "localhost"

        # Test
        runfolder = runfolder_svc.next_runfolder()
        expected = "ready: /data/testarteria1/mon1/runfolder001@localhost"
        self.assertEqual(str(runfolder), expected)

if __name__ == '__main__':
    unittest.main()
