#!/usr/bin/env python3

import os
import time

import visualize_vispy_lines as visualizer_backend

from config import *

if os.name == "posix":
    from counter_api_linux import CounterAPI
elif os.name == "nt":
    from counter_api_windows import CounterAPI
else:
    print("Operating System not supported!")
    exit(0)

counterAPI = CounterAPI()

counterAPI.setup()
buf = counterAPI.get_buf()
get_idx_fn = counterAPI.get_idx_fn

scanrate = counterAPI.start_scan()

visualizer_backend.visualize(buf, get_idx_fn)

