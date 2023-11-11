This software is not affiliated with MCC DAQ in any way.
It just happens to be used for projects with MCC DAQ counter modules.


### windows setup:

#### 1. Install MCC DAQ Software

Can be found here: http://www.mccdaq.com/Software-Downloads.aspx

#### 2. Install Anaconda

Download and install from https://www.anaconda.com/download

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


#### 4. Enjoy!

Press `[Space]` in the graph-window to start a measurement. Press it again to stop and save it.

If you need to change any parameter, look in `config.py`


#### 5. Known Errors

If you're getting an error that some freetype library is missing you have to install it from e.g. https://github.com/ubawurinna/freetype-windows-binaries according to https://stackoverflow.com/questions/55291132/runtime-error-freetype-library-not-found .

Note that this also requires Microsoft Visual C++ Redistributable für Visual Studio 2019.
You can find this e.g. at https://visualstudio.microsoft.com/de/downloads/ (Under the "other" dropdown)


#### License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

---
<sup>Copyright © 2023 Philipp Klocke (@klockeph)</sup>
