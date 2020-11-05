#!/usr/bin/env python3

import time
import uldaq

import visualize_vispy as visualizer_backend

# [DaqDeviceDescriptor]
[d] = uldaq.get_daq_device_inventory(uldaq.InterfaceType.USB)

# DaqDevice
dev = uldaq.DaqDevice(d)

# CtrDevice
ctrdev = dev.get_ctr_device()

dev.connect()

CHANNELS = 1
SECONDS = 5
# SAMPLES = 5000
SAMPLES_PER_SECOND = 10**5
#SAMPLES = SECONDS * SAMPLES_PER_SECOND
SAMPLES = 1000

buf = uldaq.create_int_buffer(CHANNELS, SAMPLES)
for i in range(CHANNELS*SAMPLES):
    buf[i] = -1


START_CTR = 0
END_CTR = START_CTR + (CHANNELS-1)

for i in range(START_CTR, END_CTR+1):
    ctrdev.c_config_scan(
            0,
            uldaq.CounterMeasurementType.COUNT,
            uldaq.CounterMeasurementMode.CLEAR_ON_READ, # seems to have no effect though?!
            uldaq.CounterEdgeDetection.RISING_EDGE,
            0, # CounterTickSize -> ignored
            0, # DebounceMode -> NONE
            0, # DebounceTime -> ignored
            4) #4) # Flag -> 64Bit

scanrate = ctrdev.c_in_scan(
        START_CTR,
        END_CTR,
        SAMPLES,
        SAMPLES_PER_SECOND,
        uldaq.ScanOption.CONTINUOUS, # ScanOption
        0, # CInScanFlag
        buf)

print(f"Scanning {scanrate}/s samples continuously to {SAMPLES} buffer")



try:
    visualizer_backend.visualize(buf, ctrdev, SAMPLES_PER_SECOND, SAMPLES)
finally:
    ctrdev.scan_stop()


"""
#visualize_matplotlib

import matplotlib
matplotlib.use('GTK3Agg') 

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

# TODO: the following code is not multichannel!!!
# TODO: height
npbuf = (SAMPLES_PER_SECOND / 250) * np.ones([SAMPLES])


fig = plt.figure()

x = np.linspace(0, SAMPLES, SAMPLES)
barcollection = plt.bar(x, npbuf)

# np.savetxt("scan.csv", delimiter=",")

#https://kb.mccdaq.com/KnowledgebaseArticle50758.aspx

last_drawn_index = 0
max_index = SAMPLES-1

# TODO: needs red bar
def animate(i):
    global last_drawn_index
    global max_index
    (_, transferstatus) = ctrdev.get_scan_status()
    last_valid_index = transferstatus.current_index - 1
    if last_valid_index < last_drawn_index:
        for i in range(last_drawn_index, max_index):
            barcollection[i].set_height(buf[i])
        last_drawn_index = 0
    for i in range(last_drawn_index, last_valid_index):
        barcollection[i].set_height(buf[i])
    last_drawn_index = last_valid_index


ani = animation.FuncAnimation(fig,animate,interval=1,blit=False)
plt.show()
"""
