#!/usr/bin/env python3

import os

import visualize_vispy_lines as visualizer_backend

from config import *

if os.name == "posix":
    from counter_api_linux import CounterAPI
elif os.name == "nt":
    from counter_api_windows import CounterAPI
else:
    print("Operating System not supported!")
    exit(0)

try:
    counterAPI = CounterAPI()

    counterAPI.setup()
    buf = counterAPI.get_buf()
    get_idx_fn = counterAPI.get_idx_fn

    scanrate = counterAPI.start_scan()
except:
    # if we had an error we use mock data

    print("Exception while initializing Counter")
    print("Showing some sample data instead")

    import threading,time
    import numpy as np
    
    class MockCounter(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.buf = np.zeros(SAMPLES*CHANNELS)
            self.idx = 0

        def run(self):
            while(True):
                buf[self.idx] = np.random.rand() * 20 + 1000
                buf[self.idx+1] = np.random.rand() * 15 + 700
                self.idx = (self.idx + 2) % (SAMPLES*CHANNELS)
                time.sleep(1 / SAMPLES_PER_SECOND)
            pass
        
        def get_idx(self):
            return self.idx
        
        def get_buf(self):
            return self.buf

    mock = MockCounter()
    buf = mock.get_buf()
    get_idx_fn = mock.get_idx
    mock.start()

visualizer_backend.visualize(buf, get_idx_fn)

