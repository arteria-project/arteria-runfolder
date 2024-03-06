import unittest
import logging
import mock

from arteria.web.state import State

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

    def _is_older_wrapper(self, path, age):
        return self._valid_runfolder(path)

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
        runfolder_svc._file_exists_and_is_older_than = self._is_older_wrapper
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
        runfolder_svc._file_exists_and_is_older_than = self._is_older_wrapper
        runfolder_svc._subdirectories = lambda path: ["runfolder001"]
        runfolder_svc._host = lambda: "localhost"

        # Test
        runfolder = runfolder_svc.next_runfolder()
        expected = "ready: /data/testarteria1/mon1/runfolder001@localhost"
        self.assertEqual(str(runfolder), expected)

    def test_monitored_directory_validates(self):
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)

        runfolder = "/data/testarteria1/runfolders/runfolder1"
        # passes if no exception:
        runfolder_svc._validate_is_being_monitored(runfolder)

        # Doesn't matter if the configuration specifies an extra separator:
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders/"]
        runfolder_svc._validate_is_being_monitored(runfolder)

    def test_get_reagent_kit_barcode_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {'RunParameters': {'ReagentKitBarcode': 'ABC-123'}}

        # Test
        self.assertEqual(runfolder_svc.get_reagent_kit_barcode('/path/to/runfolder/', runparameters_dict), 'ABC-123')

    def test_get_reagent_kit_barcode_not_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {'RunParameters': {'OtherLabel': 'ABC-123'}}

        # Test
        self.assertEqual(runfolder_svc.get_reagent_kit_barcode('/path/to/runfolder/', runparameters_dict), None)

    def test_get_library_tube_barcode_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {'RunParameters': {'RfidsInfo': {'LibraryTubeSerialBarcode': 'NV0012345-LIB'}}}

        # Test
        self.assertEqual(runfolder_svc.get_library_tube_barcode('/path/to/runfolder/', runparameters_dict), 'NV0012345-LIB')

    def test_get_novaseqxplus_library_tube_barcode_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {
                                "RunParameters": {
                                    "ConsumableInfo": {
                                        "ConsumableInfo": [
                                            {"Type": "SampleTube", "SerialNumber": "LC1037822-LC1"}
                                        ]
                                    }
                                }
                            }

        # Test
        self.assertEqual(runfolder_svc.get_library_tube_barcode('/path/to/runfolder/', runparameters_dict), 'LC1037822-LC1')

    def test_get_library_tube_barcode_not_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {'RunParameters': {'OtherLabel': 'ABC-123'}}

        # Test
        self.assertEqual(runfolder_svc.get_library_tube_barcode('/path/to/runfolder/', runparameters_dict), None)

    def test_get_metadata_values_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {'RunParameters': { 'ReagentKitBarcode': 'ABC-123',
                                                 'RfidsInfo': {'LibraryTubeSerialBarcode': 'NV0012345-LIB'}}}

        # Test
        with mock.patch.object(RunfolderService, 'read_run_parameters', return_value = runparameters_dict):
            metadata_dict = runfolder_svc.get_metadata('/path/to/runfolder/')
            self.assertEqual(metadata_dict['reagent_kit_barcode'], 'ABC-123')
            self.assertEqual(metadata_dict['library_tube_barcode'], 'NV0012345-LIB')

    def test_get_metadata_values_not_found(self):
        # Setup
        configuration_svc = dict()
        configuration_svc["monitored_directories"] = ["/data/testarteria1/runfolders"]
        runfolder_svc = RunfolderService(configuration_svc, logger)
        runparameters_dict = {'RunParameters': {'OtherLabel': 'ABC-123'}}

        # Test
        with mock.patch.object(RunfolderService, 'read_run_parameters', return_value = runparameters_dict):
            metadata_dict = runfolder_svc.get_metadata('/path/to/runfolder/')
            self.assertEqual(metadata_dict, {})

if __name__ == '__main__':
    unittest.main()
