#!/usr/bin/env python3

import time
import uldaq

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

CHANNELS = 1 # 2
SAMPLES = 1000
SAMPLES_PER_SECOND = 10**4

buf = uldaq.create_int_buffer(CHANNELS, SAMPLES)
for i in range(CHANNELS*SAMPLES):
    buf[i] = -1


START_CTR = 1
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

scanrate = ctrdev.c_in_scan(START_CTR, END_CTR, SAMPLES, SAMPLES_PER_SECOND, 0, 0, buf)

print(f"Scanning with {scanrate}/s")

class MyCounter:
    def __init__(self, num_channels, num_samples):
        self.vals = np.zeros([num_channels, num_samples])
        self.idx_valid = 1
        self.total = np.zeros((num_channels), dtype=int)
        self.channels = num_channels
        self.samples = num_samples

    def reset(self):
        self.vals.fill(0)
        self.idx_valid = 1
        self.total.fill(0)

    def return_valid(self):
        return self.vals[:,:idx_valid]

    def update_from_uldaq_scan_buf(self, buf):
        # Assertion: 0 is never a valid received counter value
        for index in range(self.idx_valid*self.channels, (self.samples*self.channels)-1, self.channels):
            if buf[index] == 2**64-1: break
            for c in range(self.channels):
                v = buf[index+c]
                v -= self.total[c]
                self.total[c] += v
                self.vals[c, int(index/self.channels)] = v
            self.idx_valid += 1


myctr = MyCounter(CHANNELS, SAMPLES)
# myctr.update_from_uldaq_scan_buf(buf)
time.sleep(2)
myctr.update_from_uldaq_scan_buf(buf)

print(myctr.vals)
print(",".join(map(str, buf)))


fig = plt.figure()
ax1 = fig.add_subplot(1,1,1)

# TODO: animation (for longer measurements)

for i in range(START_CTR, END_CTR+1):
    i -= START_CTR
    plt.bar(np.linspace(0,SAMPLES,SAMPLES)+0.2, myctr.vals[i], width=0.2)
#    plt.bar(np.linspace(0,SAMPLES,SAMPLES)-0.2, myctr.vals[1], width=0.2)

plt.show()
