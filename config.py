"""
Global constants
"""

# Changing this is not really supported
CHANNELS = 2
SAMPLES_PER_SECOND = 10**3
SAMPLES = 1000 # actually this is only buffer size

# probably don't need to touch this
# just use channel 0 and 1 on the counter pls.
# but you definitely need to use a continuous number of counters
START_CTR = 0
END_CTR = START_CTR + (CHANNELS-1)

# TODO canvas size, probably not good to have it as constant.
CANVAS_SIZE = (1000, 800) # (width, height)
