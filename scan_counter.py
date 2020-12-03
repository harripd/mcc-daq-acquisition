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
    print("Press any key to continue with mock data...")
    input()

    import threading,time
    import numpy as np
    
    class MockCounter(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.buf = np.zeros(PLAIN_BUFFER_SIZE)
            self.idx = 0

        def run(self):
            while(True):
                sinargs = np.arange(self.idx, self.idx+SAMPLES_PER_BIN) * 2*np.pi / BUFFER_SIZE
                sin = np.sin(sinargs) * 200
                sin += (np.random.rand(SAMPLES_PER_BIN) - 0.5) * 20
                buf[self.idx:self.idx+SAMPLES_PER_BIN*2:2] = (sin + 1000) / SAMPLES_PER_BIN

                noise = (np.random.rand(SAMPLES_PER_BIN) * 15 + 200)

                buf[self.idx+1:self.idx+SAMPLES_PER_BIN*2+1:2] = (noise + 200) / SAMPLES_PER_BIN

                self.idx = (self.idx + SAMPLES_PER_BIN*CHANNELS) % (PLAIN_BUFFER_SIZE)
                time.sleep(1 / BIN_SIZE)
            pass
        
        def get_idx(self):
            return self.idx
        
        def get_buf(self):
            return self.buf

    mock = MockCounter()
    buf = mock.get_buf()
    get_idx_fn = mock.get_idx
    mock.start()


def update_callback_fn(buf, ):
    pass

visualizer_backend.visualize(buf, get_idx_fn, update_callback_fn)

