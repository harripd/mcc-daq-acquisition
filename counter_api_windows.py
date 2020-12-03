# Windows setup code
from mcculw import ul
from mcculw.enums import CounterChannelType, ScanOptions, CounterMode, FunctionType, InterfaceType, CounterEdgeDetection, CounterDebounceTime, ErrorCode
from mcculw.ul import ULError
from mcculw.device_info import DaqDeviceInfo

from ctypes import cast, POINTER, c_ulong, c_ulonglong

class CounterAPI():

    def setup():
        self.board_num = 0
    
        # configure first detected device
        ul.ignore_instacal()
        devices = ul.get_daq_device_inventory(InterfaceType.USB)
        if not devices:
            raise ULError(ErrorCode.BADBOARD)
        ul.create_daq_device(board_num, devices[0])

        device_info = DaqDeviceInfo(board_num)
        counter_info = device_info.get_ctr_info()
        
        self.memhandle = ul.win_buf_alloc_64(BUFFER_SIZE * CHANNELS)

        if not self.memhandle:
            raise Exception("Could not allocate memory")

        for i in range(START_CTR, END_CTR+1):
            ul.c_config_scan(
                    self.board_num,
                    i,
                    CounterMode.CLEAR_ON_READ,
                    CounterDebounceTime.DEBOUNCE_NONE, # debounce_time
                    0, # debounce_mode
                    CounterEdgeDetection.RISING_EDGE, 
                    0, # tick_size
                    i) # mapped_channel (should be ignored by CounterMode)

    def start_scan():
        scanrate = ul.c_in_scan(
                board_num,
                START_CTR,
                END_CTR,
                BUFFER_SIZE*CHANNELS,
                ACQUISITION_RATE,
                self.memhandle,
                ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS | ScanOptions.CTR64BIT)
        return scanrate

    def stop_scan():
        raise ValueError("Not implemented! Shutting down")

    def get_idx_fn():
        (_,_, cur_idx) = ul.get_status(self.board_num, FunctionType.CTRFUNCTION)
        return cur_idx

    def get_buf():
        buf = cast(memhandle, POINTER(c_ulonglong))
        return buf

