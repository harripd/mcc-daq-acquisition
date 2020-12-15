"""
Global constants
"""


"""
General setup (Counters/Channels)
"""
# Changing this is not really supported
CHANNELS = 2

# probably don't need to touch this
# just use channel 0 and 1 on the counter pls.
# but you definitely need to use a continuous number of counters
START_CTR = 0
END_CTR = START_CTR + (CHANNELS-1)


"""
Acquisition
"""

ACQUISITION_RATE = int(1e5)
BUFFER_SIZE = int(2e5) # Buffer size for each channel

PLAIN_BUFFER_SIZE = BUFFER_SIZE * CHANNELS

"""
Visualisation
"""

# TODO canvas size, probably not good to have it as constant.
CANVAS_SIZE = (1000, 800) # (width, height)
BIN_SIZE = 10**3 # this is only for visualization! See ACQUISITION_RATE

SAMPLES_PER_BIN = ACQUISITION_RATE // BIN_SIZE


if(ACQUISITION_RATE < BIN_SIZE):
    print("")
    print("Error: Trying to show more samples than acquired")
    print("Please choose ACQUISITION_RATE >= SAMPLES_PER_SECOND")
    exit(0)
