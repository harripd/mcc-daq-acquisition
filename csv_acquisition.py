import csv
import time

from config import *

processing_first_half = True
midpoint = PLAIN_BUFFER_SIZE // 2
current_time = 0

acquisition = False

csv_file = None
csv_writer = None


def toggle_acquisition():
    global acquisition, current_time, csv_file, csv_writer
    acquisition = not acquisition
    print(f"Acquisition as CSV", "started" if acquisition else "stopped")
    if acquisition:
        # User just turned on acquisition
        csv_file = open(f'measurement_{int(time.time())}.csv', 'w+', newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["time", "green", "red"])
    else:
        # User just turned off acquisition
        csv_file.close()

        print(f"saved {csv_file.name}")
        print("amount of timestamps:", current_time)

        # reset measurement
        current_time = 0
        csv_writer = None
        csv_file = None


def update_callback_fn(buf, valid_idx):
    global current_time, processing_first_half

    if not acquisition:
        return

    if csv_writer is None:
        print("Error in Acquisition, please restart!")
        return

    def write(idx):
        global current_time
        csv_writer.writerow([current_time, buf[idx], buf[idx+1]])
        current_time += 1

    if processing_first_half and valid_idx > midpoint:
        for i in range(0, midpoint, CHANNELS):
            write(i)
        processing_first_half = False
    if not processing_first_half and valid_idx < midpoint:
        for i in range(midpoint, BUFFER_SIZE, CHANNELS):
            write(i)
        processing_first_half = True

