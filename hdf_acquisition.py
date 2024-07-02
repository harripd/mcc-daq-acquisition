import time

import numpy as np

from visualize_vispy_lines import get_filename

import write_hdf5
# from config import *

from config import CHANNELS, ACQUISITION_RATE, PLAIN_BUFFER_SIZE, BUFFER_SIZE

processing_first_half = True
midpoint = PLAIN_BUFFER_SIZE // 2
current_time = 0

timestamps = list()
detectors = list()

acquisition = False


# TODO: is it better to convert it into photon arrival times now or later?

def toggle_acquisition():
    global acquisition, timestamps, detectors, current_time
    acquisition = not acquisition
    print("Acquisition as HDF5" + "started" if acquisition else "stopped")
    if not acquisition:
        # User just turned off acquisition
        if len(timestamps) == 0:
            print("Nothing recorded permanently yet, not saving.")
        else:
            print("amount of timestamps:", current_time)
            print("amount of photons:", len(detectors) // CHANNELS)
            np_timestamps = np.array(timestamps, dtype=np.int64)
            np_detectors = np.array(detectors, dtype=np.uint8)
            timestamps_unit = 1 / ACQUISITION_RATE
            write_hdf5.write_file(np_timestamps, np_detectors, timestamps_unit, fname=get_filename())

        # reset measurement
        timestamps = []
        detectors = []
        current_time = 0


def update_callback_fn(buf, valid_idx, total_seconds):
    global current_time, processing_first_half

    if not acquisition:
        return True

    # TODO: test if enough points collected
    #       if yes, stop acquisition

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

        if current_time // ACQUISITION_RATE >= total_seconds:
            # End of acquisition has been reached
            toggle_acquisition()
            return False

        # iterate over all channels
        for n in range(CHANNELS):
            timestamps.extend([current_time] * buf[idx+n])
            detectors.extend([n] * buf[idx+n])

        current_time += 1
        return True

    if processing_first_half and valid_idx > midpoint:
        for i in range(0, midpoint, CHANNELS):
            if not copy(i):
                return False
        processing_first_half = False
    if not processing_first_half and valid_idx < midpoint:
        for i in range(midpoint, BUFFER_SIZE, CHANNELS):
            if not copy(i):
                return False
        processing_first_half = True

    return True
