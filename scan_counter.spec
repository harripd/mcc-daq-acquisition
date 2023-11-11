# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules

import vispy.glsl
import vispy.io
import freetype
import phconvert

data_files = [
    (os.path.dirname(vispy.glsl.__file__), os.path.join("vispy", "glsl")),
    (os.path.join(os.path.dirname(vispy.io.__file__), "_data"), os.path.join("vispy", "io", "_data")),
    (os.path.dirname(vispy.util.__file__), os.path.join("vispy", "util")),
    (os.path.dirname(freetype.__file__), os.path.join("freetype")),
    (os.path.join(os.path.dirname(phconvert.__file__), "specs"), os.path.join("phconvert", "specs")),
    (os.path.join(os.path.dirname(phconvert.__file__), "v04", "specs"), os.path.join("phconvert", "v04", "specs"))
]

hidden_imports = [
    "vispy.ext._bundled.six",
    "vispy.app.backends._pyqt5",
    "freetype",
    "phconvert",
]

a = Analysis(
    ['scan_counter.py'],
    # You will have to edit this line:
    # vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    pathex=['C:\\Users\\Philipp\\Anaconda3\\envs\\virometer\\Lib\\site-packages'],
    # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='scan_counter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
