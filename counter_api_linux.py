# Linux setup code
import uldaq

from config import *

class CounterAPI():

    def setup(self):
        # [DaqDeviceDescriptor]
        [d] = uldaq.get_daq_device_inventory(uldaq.InterfaceType.USB)

        # DaqDevice
        self.dev = uldaq.DaqDevice(d)

        # CtrDevice
        self.ctrdev = self.dev.get_ctr_device()

        self.dev.connect()

        self.buf = uldaq.create_int_buffer(CHANNELS, SAMPLES)

        for i in range(START_CTR, END_CTR+1):
            self.ctrdev.c_config_scan(
                    i,
                    uldaq.CounterMeasurementType.COUNT,
                    uldaq.CounterMeasurementMode.CLEAR_ON_READ, # seems to have no effect though?!
                    uldaq.CounterEdgeDetection.RISING_EDGE,
                    0, # CounterTickSize -> ignored
                    0, # DebounceMode -> NONE
                    0, # DebounceTime -> ignored
                    4) # Flag -> 64Bit

    def start_scan(self):
        scanrate = self.ctrdev.c_in_scan(
                START_CTR,
                END_CTR,
                SAMPLES,
                SAMPLES_PER_SECOND,
                uldaq.ScanOption.CONTINUOUS, # ScanOption
                0, # CInScanFlag
                self.buf)
        return scanrate
    
    def stop_scan(self):
        self.ctrdev.scan_stop() 

    def get_idx_fn(self):
        (_, transferstatus) = self.ctrdev.get_scan_status()
        return transferstatus.current_index - 1

    def get_buf(self):
        return self.buf

