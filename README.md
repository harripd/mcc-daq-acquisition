windows setup:

Install Anaconda

In Anaconda prompt:
```
pip install mcculw
pip install vispy
```

(you can also try `conda install` instead of `pip install`)


Then you can run the script by entering

```
python scan_counter.py
```

If you need to change the binning, see `scan_counter.py`, and change the `SAMPLES_PER_SECOND` variable.

If you need to change the output image resolution see `vispy_visualize_lines.py` and set the `canvas_size` accordingly
