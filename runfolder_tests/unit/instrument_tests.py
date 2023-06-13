import unittest
import logging
import mock


from runfolder.lib.instrument import InstrumentFactory, Instrument


logger = logging.getLogger(__name__)

class InstrumentTestCase(unittest.TestCase):
    def test_get_instrument_by_id(self):
        # HiSeqX
        instrument_attr = {
            'Setup': {
                'ScannerID': 'ST-E123'
            }
        }
        run_parameters = {
            'RunParameters': instrument_attr
        }

        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'HiSeqX')
        self.assertEqual(i.completed_marker_file(), 'RTAComplete.txt')

        # HiSeq
        run_parameters['RunParameters']['Setup']['ScannerID'] = 'D999'
        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'HiSeq')
        self.assertEqual(i.completed_marker_file(), 'RTAComplete.txt')

        # NovaSeq
        run_parameters = {
            'RunParameters': {
                'InstrumentName': 'ABC'
            }
        }
        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'NovaSeq')
        self.assertEqual(i.completed_marker_file(), 'CopyComplete.txt')

        #NovaSeqXPlus
        run_parameters = {
            'RunParameters': {
                'InstrumentSerialNumber': 'LH123'
            }
        }
        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'NovaSeqXPlus')
        self.assertEqual(i.completed_marker_file(), 'CopyComplete.txt')

        # iSeq
        run_parameters = {
            'RunParameters': {
                'InstrumentId': 'FS1'
            }
        }
        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'ISeq')
        self.assertEqual(i.completed_marker_file(), 'CopyComplete.txt')

        # MiSeq
        run_parameters = {
            'RunParameters': {
                'ScannerID': 'M1'
            }
        }
        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'MiSeq')
        self.assertEqual(i.completed_marker_file(), 'RTAComplete.txt')

        # Default
        run_parameters = {
            'RunParameters': {
                'ScannerID': 'foo'
            }
        }
        i = InstrumentFactory.get_instrument(run_parameters)
        self.assertEqual(i.__class__.__name__, 'Instrument')
        self.assertEqual(i.completed_marker_file(), 'RTAComplete.txt')


if __name__ == '__main__':
    unittest.main()
