### windows setup:

#### 1. Install MCC DAQ Software

Can be found here: http://www.mccdaq.com/Software-Downloads.aspx

#### 2. Install Anaconda

Open Anaconda Prompt (windows menu, search for anaconda)

In Anaconda prompt enter:
```
pip install mcculw vispy phconvert
```

(you can also try `conda install` instead of `pip install` but probably it won't work for all packages)

Navigate to wherever you stored this software. E.g.:

```
cd Documents\virometer_code\
```

Then you can run the script by entering

```
python scan_counter.py
```

If you need to change any parameter, look in `config.py`
