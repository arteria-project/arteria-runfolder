# Typically, an Illumina machine writes a RTAComplete.txt file when it has
# finished the sequencing process. However, some instruments may use another
# completed_marker_file, for instance one that indicates that files have
# been transferred.

import re


class InstrumentFactory():
    @staticmethod
    def get_id(run_parameters):
        run_parameters = run_parameters.get('RunParameters', None)

        # HiSeq / HiSeq X instrument stored in Setup#ScannerID
        val = run_parameters.get('Setup', {}).get('ScannerID')
        if val:
            return val

        # Other instrument id's are at the top level of RunParameters
        for key in ["InstrumentName", "InstrumentId", "ScannerID"]:
            if key in run_parameters.keys():
                return run_parameters.get(key)

    @staticmethod
    def get_instrument(run_parameters):
        if not run_parameters:
            return Instrument()

        instrument_id = InstrumentFactory.get_id(run_parameters)

        if not instrument_id:
            return Instrument()

        if re.search(NovaSeq.ID_PATTERN, instrument_id):
            return NovaSeq()
        if re.search(NovaSeqXPlus.ID_PATTERN, instrument_id):
            return NovaSeqXPlus()
        if re.search(ISeq.ID_PATTERN, instrument_id):
            return ISeq()
        if re.search(MiSeq.ID_PATTERN, instrument_id):
            return MiSeq()
        if re.search(HiSeq.ID_PATTERN, instrument_id):
            return HiSeq()
        if re.search(HiSeqX.ID_PATTERN, instrument_id):
            return HiSeqX()
        return Instrument()


class Instrument():
    COMPLETED_MARKER_FILE_RTA_COMPLETE = 'RTAComplete.txt'
    COMPLETED_MARKER_FILE_COPY_COMPLETE = 'CopyComplete.txt'

    @staticmethod
    def completed_marker_file():
        return Instrument.COMPLETED_MARKER_FILE_RTA_COMPLETE


class NovaSeq(Instrument):
    ID_PATTERN = '^A'

    @staticmethod
    def completed_marker_file():
        return Instrument.COMPLETED_MARKER_FILE_COPY_COMPLETE

class NovaSeqXPlus(Instrument):
    ID_PATTERN = '^LH'

    @staticmethod
    def completed_marker_file():
        return Instrument.COMPLETED_MARKER_FILE_COPY_COMPLETE

class ISeq(Instrument):
    ID_PATTERN = '^FS'

    @staticmethod
    def completed_marker_file():
        return Instrument.COMPLETED_MARKER_FILE_COPY_COMPLETE


class MiSeq(Instrument):
    ID_PATTERN = '^M'


class HiSeq(Instrument):
    ID_PATTERN = '^D'


class HiSeqX(HiSeq):
    ID_PATTERN = '^ST-E'
