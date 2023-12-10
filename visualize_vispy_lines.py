import numpy as np
import sys

from threading import Thread, Lock
from time import sleep

from vispy import app, scene

from PyQt5.QtWidgets import *

from config import *
from auto_align import autofocus

# vertex positions of data to draw
N = CANVAS_SIZE[0]

# Leaves some space for the axes
# TODO: refine this
GRID_COLS = 10
GRID_ROWS = 7

# green channel
pos_green = np.zeros((N, 2), dtype=np.float32)
pos_green[:, 0] = np.linspace(0, N, N)
pos_green[:, 1] = None

# red channel
pos_red = np.zeros((N, 2), dtype=np.float32)
pos_red[:, 0] = np.linspace(0, N, N)
pos_red[:, 1] = None


def transfer_data(buf, canv_idx, transfer_from, transfer_to) -> (int, int):
    """
    Transfers data to canvas buffer, starting from transfer_from to transfer_to
    Returns new transfer_idx, new idx (to canvas) and sets pos_green, pos_red.
    """

    # print("transferring from buf[", transfer_from, "to", transfer_to, "] to canvas[", idx, "]")

    if transfer_from == transfer_to:
        # TODO: could we miss a whole cycle? Very low probability
        return transfer_from, canv_idx

    # print(f"{transfer_from}-{transfer_to}")

    transferrable_samples = transfer_to - transfer_from
    if transferrable_samples < 0:
        # handle buffer overrun (restart from the left)
        transferrable_samples += PLAIN_BUFFER_SIZE

    transferrable_samples = transferrable_samples // CHANNELS

    transferrable_bins = transferrable_samples // SAMPLES_PER_BIN

    buf_idx = transfer_from
    for _ in range(transferrable_bins):
        green_bin = 0
        red_bin = 0
        for _ in range(0, SAMPLES_PER_BIN):
            green_bin += buf[buf_idx]
            if CHANNELS == 2:
                red_bin += buf[buf_idx + 1]
            buf_idx = (buf_idx + CHANNELS) % PLAIN_BUFFER_SIZE
        # print(f"canv[{canv_idx}] = bin from {buf_idx-SAMPLES_PER_BIN*CHANNELS} to {buf_idx}")
        pos_green[canv_idx, 1] = green_bin
        if CHANNELS == 2:
            pos_red[canv_idx, 1] = red_bin
        canv_idx = (canv_idx + 1) % N

    return buf_idx, canv_idx


def visualize(buf, get_idx_fn, update_callback_fn, acquisition_fun=None):

    if acquisition_fun is not None:
        keys = dict(space=acquisition_fun)
    else:
        keys = "interactive"

    scene_canvas = scene.SceneCanvas(size=CANVAS_SIZE, keys=keys, show=False, fullscreen=False)
    grid = scene_canvas.central_widget.add_grid()
    
    view = grid.add_view(
        row=0,
        col=1,
        row_span=GRID_ROWS,
        col_span=GRID_COLS,
        camera='panzoom',
        border_color='grey'
    )

    view.camera.rect = (0, 0, CANVAS_SIZE[1], CANVAS_SIZE[0])

    progress_bar = scene.visuals.InfiniteLine(0, parent=view.scene)
    green_line = scene.visuals.Line(pos=pos_green,color='g',parent=view.scene)
    if CHANNELS == 2:
        red_line = scene.visuals.Line(pos=pos_red,color='r',parent=view.scene)
    gridlines = scene.GridLines(color=(1, 1, 1, 1), parent=view.scene)

    yax = scene.AxisWidget(orientation='left', axis_label="Counts")
    grid.add_widget(yax, 0, 0, row_span=GRID_ROWS)
    yax.link_view(view)

    xax = scene.AxisWidget(orientation='bottom', axis_label=f"Time in (1/{BIN_SIZE})s", tick_label_margin=15)
    grid.add_widget(xax, GRID_ROWS, 1, col_span=GRID_COLS)
    xax.link_view(view)

    auto_align_mutex = Lock()
    auto_align_awaits = False
    auto_align_start_idx = 0
    auto_align_end_idx = 0

    last_transfer_idx = 0
    last_update_idx = 0

    def update(ev):
        nonlocal last_update_idx, last_transfer_idx
        nonlocal auto_align_mutex, auto_align_awaits, auto_align_start_idx, auto_align_end_idx

        transfer_idx = get_idx_fn()
        if transfer_idx % CHANNELS != 0:
            # transfer of 1 channel is ahead, reading that sample next time
            # this shouldn't happen but let's add it for sanity anyways
            transfer_idx -= 1  # TODO: what if more channels?

        update_callback_fn(buf, transfer_idx)
        
        if auto_align:
            if auto_align_thread is not None and not auto_align_thread.is_alive():
                reset_auto_align_fn()
            elif auto_align_awaits:
                # Communicate via a global variable because I can't find a better way
                with auto_align_mutex:
                    if auto_align_start_idx is None:
                        auto_align_start_idx = transfer_idx
                    auto_align_end_idx = transfer_idx
                    

        last_transfer_idx, last_update_idx = transfer_data(buf, last_update_idx, last_transfer_idx, transfer_idx)

        green_line.set_data(pos_green)
        if CHANNELS == 2:
            red_line.set_data(pos_red)
        progress_bar.set_data(last_update_idx)

        scene_canvas.update()
    

    def auto_align_measure_fn(secs):
        nonlocal auto_align_mutex, auto_align_awaits, auto_align_start_idx, auto_align_end_idx
        with auto_align_mutex:
            auto_align_awaits = True
            auto_align_start_idx = None
        sleep(secs)
        with auto_align_mutex:
            if not auto_align: # auto align was stopped in the meantime.
                return None
            if auto_align_end_idx < auto_align_start_idx:
                auto_align_end_idx = BUFFER_SIZE
            return np.mean(buf[auto_align_start_idx:auto_align_end_idx]) / CHANNELS * 1000

    timer = app.Timer(interval='auto')
    timer.connect(update)
    timer.start()

    w = QMainWindow()
    w.setWindowTitle("Noisy Lines Simulator v0.0.1")
    widget = QWidget()
    w.setCentralWidget(widget)
    widget.setLayout(QVBoxLayout())

    autoalign_frame = QFrame(widget)
    widget.layout().addWidget(autoalign_frame)
    autoalign_layout = QHBoxLayout(autoalign_frame)
    
    autoalign_toggle_button = QPushButton("Autoalign Axis")
    autoalign_toggle_button.setCheckable(True)
    autoalign_toggle_button.setChecked(False)
    autoalign_layout.addWidget(autoalign_toggle_button)
    
    autoalign_toggle_button.clicked.connect(lambda: toggle_auto_align(auto_align_measure_fn))

    measurement_frame = QFrame(widget)
    widget.layout().addWidget(measurement_frame)
    measurement_layout = QHBoxLayout(measurement_frame)
    
    # Toggle Button
    measurement_toggle_button = QPushButton("Toggle Measurement")
    measurement_toggle_button.setCheckable(True)
    measurement_toggle_button.setChecked(False)
    measurement_toggle_button.clicked.connect(acquisition_fun)

    measurement_layout.addWidget(measurement_toggle_button)

    # Type (HDF5 or CSV)
    measurement_type_group = QGroupBox("Storage Type", measurement_frame)
    measurement_layout.addWidget(measurement_type_group)

    measurement_type_group_layout = QVBoxLayout(measurement_type_group)

    measurement_type_select_hdf5 = QRadioButton("HDF5")
    measurement_type_select_hdf5.setChecked(True)
    measurement_type_group_layout.addWidget(measurement_type_select_hdf5)
    measurement_type_select_csv = QRadioButton("CSV")
    measurement_type_group_layout.addWidget(measurement_type_select_csv)

    measurement_type_select_hdf5.clicked.connect(
        lambda: set_measurement_type("HDF5")
    )
    measurement_type_select_csv.clicked.connect(
        lambda: set_measurement_type("CSV")
    )

    measurement_settings = QGroupBox("Measurement Settings", measurement_frame)
    measurement_layout.addWidget(measurement_settings)

    measurement_settings_layout = QFormLayout(measurement_settings)

    measurement_settings_seconds_label = QLabel("Seconds")
    measurement_settings_seconds_input = QSpinBox()
    measurement_settings_seconds_input.setRange(1, 300)
    measurement_settings_layout.addRow(measurement_settings_seconds_label, measurement_settings_seconds_input)

    measurement_settings_seconds_input.valueChanged.connect(set_measurement_seconds)

    # Type selection disabled when measurement is running
    measurement_toggle_button.clicked.connect(measurement_type_group.setDisabled)
    measurement_toggle_button.clicked.connect(measurement_settings.setDisabled)

    widget.layout().addWidget(measurement_frame)
    widget.layout().addWidget(autoalign_frame)
    widget.layout().addWidget(scene_canvas.native, stretch=1)
    w.show()

    global stop_measurement
    def stop_fn():
        print("Stop fn!")
        measurement_toggle_button.setChecked(False)
        measurement_type_group.setEnabled(True)
        measurement_settings.setEnabled(True)

    stop_measurement = stop_fn
    
    def reset_auto_align_fn():
        global auto_align
        global auto_align_thread
        autoalign_toggle_button.setChecked(False)
        auto_align = False
        auto_align_thread = None

    if sys.flags.interactive != 1:
        app.run()


# Global variables that will be read from main / acquisition parts
# TODO: change these to accessors

#Communicate via global variables coz I can't find a better way.

# TODO: Add real measure_fn...
auto_align = False
auto_align_thread = None
def toggle_auto_align(auto_align_measure_fn):
    global auto_align
    global auto_align_thread
    auto_align = not auto_align
    if auto_align:
        auto_align_thread = Thread(target = autofocus.auto_align, args = (auto_align_measure_fn, should_stop_autoalign_fn,))
        auto_align_thread.start()
    
def should_stop_autoalign_fn():
    return not auto_align

measurement_type = "HDF5"
measurement_time_seconds = 1


def set_measurement_type(t):
    global measurement_type
    measurement_type = t


def set_measurement_seconds(t):
    global measurement_time_seconds
    measurement_time_seconds = t


stop_measurement = lambda: None
