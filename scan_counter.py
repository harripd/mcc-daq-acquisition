#!/usr/bin/env python3

import os
import time

import visualize_vispy_lines as visualizer_backend

from config import *

if os.name == "posix":
    # Linux setup code
    import uldaq

    # [DaqDeviceDescriptor]
    [d] = uldaq.get_daq_device_inventory(uldaq.InterfaceType.USB)

    # DaqDevice
    dev = uldaq.DaqDevice(d)

    # CtrDevice
    ctrdev = dev.get_ctr_device()

    dev.connect()

    buf = uldaq.create_int_buffer(CHANNELS, SAMPLES)
    for i in range(CHANNELS*SAMPLES):
        buf[i] = -1


    for i in range(START_CTR, END_CTR+1):
        ctrdev.c_config_scan(
                i,
                uldaq.CounterMeasurementType.COUNT,
                uldaq.CounterMeasurementMode.CLEAR_ON_READ, # seems to have no effect though?!
                uldaq.CounterEdgeDetection.RISING_EDGE,
                0, # CounterTickSize -> ignored
                0, # DebounceMode -> NONE
                0, # DebounceTime -> ignored
                4) # Flag -> 64Bit

    scanrate = ctrdev.c_in_scan(
            START_CTR,
            END_CTR,
            SAMPLES,
            SAMPLES_PER_SECOND,
            uldaq.ScanOption.CONTINUOUS, # ScanOption
            0, # CInScanFlag
            buf)

    def get_idx_fn():
        (_, transferstatus) = ctrdev.get_scan_status()
        return transferstatus.current_index - 1

elif os.name == "nt":
    # Windows setup code
    from mcculw import ul
    from mcculw.enums import CounterChannelType, ScanOptions, CounterMode, FunctionType, InterfaceType, CounterEdgeDetection, CounterDebounceTime, ErrorCode
    from mcculw.ul import ULError
    from mcculw.device_info import DaqDeviceInfo

    from ctypes import cast, POINTER, c_ulong, c_ulonglong

    board_num = 0
    
    # configure first detected device
    ul.ignore_instacal()
    devices = ul.get_daq_device_inventory(InterfaceType.USB)
    if not devices:
        raise ULError(ErrorCode.BADBOARD)
    ul.create_daq_device(board_num, devices[0])

    device_info = DaqDeviceInfo(board_num)
    counter_info = device_info.get_ctr_info()
    
    memhandle = ul.win_buf_alloc_64(SAMPLES * CHANNELS)

    if not memhandle:
        raise Exception("Could not allocate memory")

    for i in range(START_CTR, END_CTR+1):
        ul.c_config_scan(
                board_num,
                i,
                CounterMode.CLEAR_ON_READ,
                CounterDebounceTime.DEBOUNCE_NONE, # debounce_time
                0, # debounce_mode
                CounterEdgeDetection.RISING_EDGE, 
                0, # tick_size
                i) # mapped_channel (should be ignored by CounterMode)

    scanrate = ul.c_in_scan(board_num, START_CTR, END_CTR, SAMPLES*CHANNELS,
                             SAMPLES_PER_SECOND, memhandle,
                             ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS | ScanOptions.CTR64BIT)

    def get_idx_fn():
        (_,_, cur_idx) = ul.get_status(board_num, FunctionType.CTRFUNCTION)
        return cur_idx

    buf = cast(memhandle, POINTER(c_ulonglong))

print(f"Scanning {scanrate}/s samples continuously to {SAMPLES} buffer")

visualizer_backend.visualize(buf, get_idx_fn)

