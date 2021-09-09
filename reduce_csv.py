#!/usr/bin/env python3

import sys
import csv

RESAMPLE_FACTOR = int(2e2)

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
            t = int(t)
            green += int(g)
            red += int(r)
            samples += 1
            if samples == RESAMPLE_FACTOR:
                writer.writerow([(t+1)//RESAMPLE_FACTOR, green, red])
                samples = 0
                green = 0
                red = 0
