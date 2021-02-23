#!/usr/bin/env python3

import os
import threading
import time

import numpy as np

import visualize_vispy_lines as visualizer_backend
import write_hdf5
from config import *

if os.name == "posix":
    from counter_api_linux import CounterAPI
elif os.name == "nt":
    from counter_api_windows import CounterAPI
else:
    raise Exception("Operating System not Supported! Must be one of POSIX or NT")

def main():

    try:
        counter_api = CounterAPI()

        counter_api.setup()
        buf = counter_api.get_buf()
        get_idx_fn = counter_api.get_idx_fn

        scan_rate = counter_api.start_scan()
        print(f"scanning with {scan_rate}/s")
    except:
        # if we had an error we use mock data

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
                    sinargs = np.arange(self.idx, self.idx+SAMPLES_PER_BIN) * 20*np.pi / BUFFER_SIZE
                    sin = np.sin(sinargs) * 2000
                    sin += (np.random.rand(SAMPLES_PER_BIN) - 0.5) * 20
                    buf[self.idx:self.idx+SAMPLES_PER_BIN*2:2] = (sin + 250) / SAMPLES_PER_BIN

                    noise = (np.random.rand(SAMPLES_PER_BIN) * 1500)

                    buf[self.idx+1:self.idx+SAMPLES_PER_BIN*2+1:2] = (noise + 2000) / SAMPLES_PER_BIN

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

    # TODO: is it better to convert it into photon arrival times now or later?

    processing_first_half = True
    midpoint = PLAIN_BUFFER_SIZE // 2
    current_time = 0

    timestamps = []
    detectors = []

    acquisition = False

    def toggle_acquisition():
        nonlocal acquisition, timestamps, detectors, current_time
        acquisition = not acquisition
        print("Acquisition", "started" if acquisition else "stopped")
        if not acquisition:
            # User just turned off acquisition
            if len(timestamps) == 0:
                print("Nothing recorded permanently yet, not saving.")
            else:
                print("amount of timestamps:", current_time)
                print("amount of photons:", len(detectors)//CHANNELS)
                np_timestamps = np.array(timestamps)
                np_detectors = np.array(detectors)
                timestamps_unit = 1/ACQUISITION_RATE
                write_hdf5.write_file(np_timestamps, np_detectors, timestamps_unit, fname=f'measurement_{int(time.time())}')

            # reset measurement
            timestamps = []
            detectors = []
            current_time = 0

    def update_callback_fn(buf, valid_idx):
        nonlocal current_time, processing_first_half

        if not acquisition:
            return

        # print(f"update callback called, idx={valid_idx}")
        if processing_first_half and valid_idx > midpoint:
            for i in range(0, midpoint, CHANNELS):
                if buf[i] > 1:
                    print(f"GREEN: Acquisition too coarse, {buf[i]} photons couldn't be distinguished")
                if buf[i+1] > 1:
                    print(f"RED:   Acquisition too coarse, {buf[i+1]} photons couldn't be distinguished")

                for _ in range(buf[i]):
                    timestamps.append(current_time)
                    detectors.append(0)
                for _ in range(buf[i+1]):
                    timestamps.append(current_time)
                    detectors.append(1)
                current_time += 1
            processing_first_half = False
        if not processing_first_half and valid_idx < midpoint:
            for i in range(midpoint, BUFFER_SIZE, CHANNELS):
                if buf[i] > 1:
                    print(f"GREEN: Acquisition too coarse, {buf[i]} photons couldn't be distinguished")
                if buf[i+1] > 1:
                    print(f"RED:   Acquisition too coarse, {buf[i+1]} photons couldn't be distinguished")
                for _ in range(buf[i]):
                    timestamps.append(current_time)
                    detectors.append(0)
                for _ in range(buf[i+1]):
                    timestamps.append(current_time)
                    detectors.append(1)
                current_time += 1
            processing_first_half = True

    visualizer_backend.visualize(
            buf,
            get_idx_fn,
            update_callback_fn,
            acquisition_fun=toggle_acquisition)

    print("Ended Visualization")


if __name__ == "__main__":
    main()