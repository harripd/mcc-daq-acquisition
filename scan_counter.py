#!/usr/bin/env python3

# PyInstaller fix.
# must be toplevel in this file!
import multiprocessing
multiprocessing.freeze_support()

import os
import threading
import time
import traceback

import numpy as np

import visualize_vispy_lines as visualizer_backend
import hdf_acquisition
import csv_acquisition

from config import *

try:
    if os.name == "posix":
        from counter_api_linux import CounterAPI
    elif os.name == "nt":
        from counter_api_windows import CounterAPI
    else:
        raise Exception("Operating System not Supported! Must be one of POSIX or NT")
except:
    print("uldaq not installed, must proceed with mock data")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Calculate auto/cross corelation of times")
    parser.add_argument('-c', '--cross', help="Display cross correlation", action="store_true")
    parser.add_argument('-a', '--auto', help="Display auto correlation", action="store_true")
    args = parser.parse_args()
    
    print("(C) Philipp Klocke")

    try:
        counter_api = CounterAPI()

        counter_api.setup()
        buf = counter_api.get_buf()
        get_idx_fn = counter_api.get_idx_fn

        scan_rate = counter_api.start_scan()
        print(f"scanning with {scan_rate}/s")
    except:
        # if we had an error we use mock data
        traceback.print_exc()

        print("Exception while initializing Counter")
        print("Press any key to continue with mock data...")
        input()
            

        class MockCounter(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.buf = np.zeros(PLAIN_BUFFER_SIZE, dtype=int)
                self.idx = 0
                self.stop = False

            def run(self):
                
                while not self.stop:
                    buf[self.idx:self.idx+SAMPLES_PER_BIN*2:2] = 0
                    if np.random.poisson(0.1):
                        bins = np.zeros(SAMPLES_PER_BIN, dtype=np.int64)
                        burst_center = np.random.randint(0, SAMPLES_PER_BIN)
                        for n in range(CHANNELS):
                            ph_locs = np.random.normal(burst_center, scale=1e-3*ACQUISITION_RATE, size=np.random.poisson(50)).astype(np.int64)
                            for loc in ph_locs:
                                if loc < 0 or loc >= bins.size:
                                    continue
                                buf[self.idx+CHANNELS*loc+n] += 1
                    
                    
                    self.idx = (self.idx + SAMPLES_PER_BIN*CHANNELS) % PLAIN_BUFFER_SIZE
                    time.sleep(1 / BIN_SIZE)

            def get_idx(self):
                return self.idx

            def get_buf(self):
                return self.buf

        mock = MockCounter()
        buf = mock.get_buf()
        get_idx_fn = mock.get_idx
        mock.start()

    def update_callback_fn(buf, valid_idx):
        cont = True
        if visualizer_backend.measurement_type == "HDF5":
            cont = hdf_acquisition.update_callback_fn(buf, valid_idx, visualizer_backend.measurement_time_seconds)
        else:
            cont = csv_acquisition.update_callback_fn(buf, valid_idx, visualizer_backend.measurement_time_seconds)
        if not cont:
            visualizer_backend.stop_measurement()

    def toggle_acquisition():
        # TODO: rather than toggle we should probably call stop/start here.
        if visualizer_backend.measurement_type == "HDF5":
            hdf_acquisition.toggle_acquisition()
        else:
            csv_acquisition.toggle_acquisition()
    
    if CHANNELS == 1 and args.cross:
        print("Cannot show cross correlation for single channel setups")
    else:
        visualizer_backend.visualize(
                buf,
                get_idx_fn,
                update_callback_fn,
                acquisition_fun=toggle_acquisition,
                correlate=args.cross or args.auto,
                cross=args.cross, auto=args.auto)

    print("Ended Visualization")


if __name__ == "__main__":
    main()
    input()
