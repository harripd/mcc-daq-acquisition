#!/usr/bin/env python3

import argparse
import scipy.signal

import numpy as np

import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Generate burst size histogram')
parser.add_argument('filename', help='CSV file to read (should be reduced)')

args = parser.parse_args()

print("Processing", args.filename)

data = np.genfromtxt(args.filename, delimiter=',', skip_header=1)

green = data[:, 1]
red = data[:, 2]

mean = np.mean(green)
stddev = np.std(green)

peak_idxs, props = scipy.signal.find_peaks(green, height=mean+0.8*stddev)

fig, (ax1, ax2) = plt.subplots(2,1)

ax1.plot(green, color='g')
ax1.plot(red, color='r')
ax1.plot(peak_idxs, green[peak_idxs], "x", color='m')

ax2.hist(props['peak_heights'], color='g')
ax2.set_xlabel("Peak height")
ax2.set_ylabel("N")

plt.show()
