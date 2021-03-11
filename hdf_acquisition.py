import time

import numpy as np

import write_hdf5
from config import *

processing_first_half = True
midpoint = PLAIN_BUFFER_SIZE // 2
current_time = 0

timestamps = []
detectors = []

acquisition = False


def toggle_acquisition():
    global acquisition, timestamps, detectors, current_time
    acquisition = not acquisition
    print(f"Acquisition as HDF5", "started" if acquisition else "stopped")
    if not acquisition:
        # User just turned off acquisition
        if len(timestamps) == 0:
            print("Nothing recorded permanently yet, not saving.")
        else:
            print("amount of timestamps:", current_time)
            print("amount of photons:", len(detectors) // CHANNELS)
            np_timestamps = np.array(timestamps)
            np_detectors = np.array(detectors)
            timestamps_unit = 1 / ACQUISITION_RATE
            write_hdf5.write_file(np_timestamps, np_detectors, timestamps_unit, fname=f'measurement_{int(time.time())}')

        # reset measurement
        timestamps = []
        detectors = []
        current_time = 0


def update_callback_fn(buf, valid_idx):
    global current_time, processing_first_half

    if not acquisition:
        return

    def copy(idx):
        global current_time
        # if buf[idx] > 1:
        #    print(f"GREEN: Acquisition too coarse, {buf[idx]} photons couldn't be distinguished")
        # if buf[idx + 1] > 1:
        #    print(f"RED:   Acquisition too coarse, {buf[idx+1]} photons couldn't be distinguished")

        # If your analysis software does not allow multiple photons to have the same timestamp,
        # You will have to adapt the following lines to not blindly repeat the arrival times and
        # instead spread them over multiple timestamps. This also means that the resolution has
        # to be changed. Like current_time += 10 (and changes in the hdf5 file)

        # green
        timestamps.extend([current_time] * buf[idx])
        detectors.extend([0] * buf[idx])

        # red
        timestamps.extend([current_time] * buf[idx + 1])
        detectors.extend([1] * buf[idx])

        current_time += 1

    if processing_first_half and valid_idx > midpoint:
        for i in range(0, midpoint, CHANNELS):
            copy(i)
        processing_first_half = False
    if not processing_first_half and valid_idx < midpoint:
        for i in range(midpoint, BUFFER_SIZE, CHANNELS):
            copy(i)
        processing_first_half = True

