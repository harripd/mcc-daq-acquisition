#!/usr/bin/env python3

import time
import uldaq

import matplotlib
matplotlib.use('GTK3Agg') 

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

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
SAMPLES_PER_SECOND = 10**3
SAMPLES = SECONDS * SAMPLES_PER_SECOND

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
        0, # ScanOption
        0, # CInScanFlag
        buf)

print(f"Scanning {SAMPLES} in {SECONDS}s with {scanrate}/s")
time.sleep(SECONDS + 1)

npbuf = np.zeros([CHANNELS * SAMPLES])
for (idx,val) in enumerate(buf):
    npbuf[idx] = val

npbuf = npbuf.reshape((CHANNELS, SAMPLES))
print(npbuf)

fig = plt.figure()
ax1 = fig.add_subplot(1,1,1)

# TODO: animation (for longer measurements)

width = 0.9/CHANNELS
for i in range(START_CTR, END_CTR+1):
    i -= START_CTR
    plt.bar(np.linspace(0,SAMPLES,SAMPLES)+width*i, npbuf[i], width=width)

# np.savetxt("scan.csv", delimiter=",")

plt.show()
