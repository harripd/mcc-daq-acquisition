#!/usr/bin/env python3

import sys
import csv

RESAMPLE_FACTOR = 2e3

with open(sys.argv[1], 'r') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    with open(sys.argv[2], 'w+', newline='') as o:
        writer = csv.writer(o)
        writer.writerow(['time', 'green', 'red'])

        samples = 0
        green = 0
        red = 0
        for row in reader:
            t, g, r = row
            green += int(g)
            red += int(r)
            samples += 1
            if samples == RESAMPLE_FACTOR:
                writer.writerow([t, green, red])
                samples = 0
                green = 0
                red = 0
