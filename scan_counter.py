#!/usr/bin/env python3

import os
import numpy as np

import visualize_vispy_lines as visualizer_backend
from config import *

import write_hdf5

import time

if os.name == "posix":
    from counter_api_linux import CounterAPI
elif os.name == "nt":
    from counter_api_windows import CounterAPI
else:
    print("Operating System not supported!")
    exit(0)

try:
    counterAPI = CounterAPI()

    counterAPI.setup()
    buf = counterAPI.get_buf()
    get_idx_fn = counterAPI.get_idx_fn

    scanrate = counterAPI.start_scan()
except:
    # if we had an error we use mock data

    print("Exception while initializing Counter")
    print("Press any key to continue with mock data...")
    input()

    import threading
    import numpy as np
    
    class MockCounter(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.buf = np.zeros(PLAIN_BUFFER_SIZE)
            self.idx = 0

        def run(self):
            self.stop = False
            while not self.stop:
                sinargs = np.arange(self.idx, self.idx+SAMPLES_PER_BIN) * 2*np.pi / BUFFER_SIZE
                sin = np.sin(sinargs) * 200
                sin += (np.random.rand(SAMPLES_PER_BIN) - 0.5) * 20
                buf[self.idx:self.idx+SAMPLES_PER_BIN*2:2] = (sin + 1000) / SAMPLES_PER_BIN

                noise = (np.random.rand(SAMPLES_PER_BIN) * 15 + 200)

                buf[self.idx+1:self.idx+SAMPLES_PER_BIN*2+1:2] = (noise + 200) / SAMPLES_PER_BIN

                self.idx = (self.idx + SAMPLES_PER_BIN*CHANNELS) % (PLAIN_BUFFER_SIZE)
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
    global acquisition, timestamps, detectors, current_time
    acquisition = not acquisition
    print("Acquisition", "started" if acquisition else "stopped")
    if not acquisition:
        # User just turned off acquisition
        if len(timestamps) == 0:
            print("Nothing recorded permanently yet, not saving.")
        else:
            print("amount of timestamps:", current_time)
            np_timestamps = np.array(timestamps) 
            np_detectors = np.array(detectors)
            timestamps_unit = 1/ACQUISITION_RATE 
            write_hdf5.write_file(np_timestamps, np_detectors, timestamps_unit, fname=f'measurements_{int(time.time())}')

        # reset measurement
        timestamps = []
        detectors = []
        current_time = 0


def update_callback_fn(buf, valid_idx):
    global current_time, processing_first_half

    if not acquisition:
        return

    #print(f"update callback called, idx={valid_idx}")
    if processing_first_half and valid_idx > midpoint:
        for i in range(0, midpoint, CHANNELS):
            if buf[i] != 1:
                #print(f"Binsize too big, {buf[i]} photons couldn't be distinguished")
                pass
            if buf[i] != 0:
                timestamps.append(current_time)
                detectors.append(0)
            if buf[i+1] != 0:
                timestamps.append(current_time)
                detectors.append(1)
            current_time += 1
        processing_first_half = False
    if not processing_first_half and valid_idx < midpoint:
        for i in range(midpoint, BUFFER_SIZE, CHANNELS):
            if buf[i] != 1:
                #print(f"Binsize too big, {buf[i]} photons couldn't be distinguished")
                pass
            if buf[i] != 0:
                timestamps.append(current_time)
                detectors.append(0)
            if buf[i+1] != 0:
                timestamps.append(current_time)
                detectors.append(1)
            current_time += 1
        processing_first_half = True

visualizer_backend.visualize(
        buf,
        get_idx_fn,
        update_callback_fn,
        keys=dict(space=toggle_acquisition))
print("Ended Visualization")
