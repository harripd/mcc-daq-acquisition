import numpy as np
import sys
from itertools import combinations

from threading import Thread, Lock
import time

from vispy import app, scene

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout
from PyQt5.QtWidgets import QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton
from PyQt5.QtWidgets import QFrame, QGroupBox, QLabel, QPushButton, QLineEdit

from config import CHANNELS, ACQUISITION_RATE, BUFFER_SIZE, CANVAS_SIZE, BIN_SIZE, PLAIN_BUFFER_SIZE, SAMPLES_PER_BIN

has_align = True
try:
    from auto_align import autofocus
except:
    has_align = False

from correlate import pcorrelate, process_buffers

acquisition = False

# vertex positions of data to draw
N = CANVAS_SIZE[0]

# Leaves some space for the axes
# TODO: refine this
GRID_COLS = 10
GRID_ROWS = 7


# Make bins
pos_ph = np.zeros((CHANNELS, N, 2), dtype=np.float32)
pos_ph[:,:,0] = np.linspace(0, N, N)[np.newaxis,:]

current_filename = ''

def zip_color(val, color, fill):
    citer = iter(color)
    has_colors = True
    for v in val:
        if has_colors:
            try:
                c = next(citer)
            except StopIteration:
                has_colors = False
                c = fill
        yield v, c


def transfer_data(buf, canv_idx, transfer_from, transfer_to) -> (int, int):
    """
    Transfers data to canvas buffer, starting from transfer_from to transfer_to
    Returns new transfer_idx, new idx (to canvas) and sets pos_ph.
    """

    # # print("transferring from buf[", transfer_from, "to", transfer_to, "] to canvas[", idx, "]")

    if transfer_from == transfer_to:
        # TODO: could we miss a whole cycle? Very low probability
        return transfer_from, canv_idx

    # # print(f"{transfer_from}-{transfer_to}")
    

    transferrable_samples = transfer_to - transfer_from
    if transferrable_samples < 0:
        # handle buffer overrun (restart from the left)
        transferrable_samples += PLAIN_BUFFER_SIZE

    transferrable_samples = transferrable_samples // CHANNELS

    transferrable_bins = transferrable_samples // SAMPLES_PER_BIN

    buf_idx = transfer_from
    for _ in range(transferrable_bins):
        pos_ph[:, canv_idx, 1] = 0
        for i in range(CHANNELS):
            pos_ph[i, canv_idx, 1] = sum(buf[buf_idx+i:buf_idx+SAMPLES_PER_BIN*CHANNELS+i:CHANNELS])
        buf_idx = (buf_idx+CHANNELS*SAMPLES_PER_BIN) % PLAIN_BUFFER_SIZE
        canv_idx = (canv_idx + 1) % N
    return buf_idx, canv_idx


def gen_corr_bins(nbin, tmin, tmax, no_zero=True):
    if tmin <= 0.0:
        tmin = 1 / ACQUISITION_RATE
    if tmax <= tmin:
        tmax = tmin + 1
    corr_bins = np.logspace(np.log(tmin)/np.log(10), np.log(tmax)/np.log(10), nbin+1)
    corr_bins_scale = (corr_bins*ACQUISITION_RATE).astype(np.int64)
    if no_zero:
        corr_bins_scale[0==corr_bins_scale] = 1
    keep = np.concatenate([[True], np.diff(corr_bins_scale) != 0])
    corr_bins = corr_bins[keep]
    corr_bins_scale = corr_bins_scale[keep]
    corr_bins = (corr_bins[:-1]+corr_bins[1:])/2
    return corr_bins, corr_bins_scale


def visualize(buf, get_idx_fn, update_callback_fn, acquisition_fun=None, 
              correlate=False, cross=True, auto=True, mock=False):
    colors = ('g', 'r', 'c')
    cross_colors = ('orange', 'm', 'yellow')
    if acquisition_fun is not None:
        def acquisit_fun():
            global current_filename
            current_filename = measurement_type_filename.text()
            acquisition_fun()
        keys = dict(space=acquisit_fun)
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
    ph_lines = tuple(scene.visuals.Line(pos=pos_l, color=c, parent=view.scene) for pos_l, c in zip_color(pos_ph, colors, 'w'))

    # reen_line = scene.visuals.Line(pos=pos_green,color='g',parent=view.scene)
    # if CHANNELS == 2:
    #     red_line = scene.visuals.Line(pos=pos_red,color='r',parent=view.scene)
    gridlines = scene.GridLines(color=(1, 1, 1, 1), parent=view.scene)

    yax = scene.AxisWidget(orientation='left', axis_label="Counts")
    grid.add_widget(yax, 0, 0, row_span=GRID_ROWS)
    yax.link_view(view)

    xax = scene.AxisWidget(orientation='bottom', axis_label=f"Time in (1/{BIN_SIZE})s", tick_label_margin=15)
    grid.add_widget(xax, GRID_ROWS, 1, col_span=GRID_COLS)
    xax.link_view(view)
    
    corr_view = grid.add_view(row=GRID_ROWS, col=1, row_span=GRID_ROWS, col_span=GRID_COLS,
                              camera='panzoom', border_color='grey')
    corr_node = scene.Node(parent=corr_view.scene)
    corr_node.transform = scene.transforms.LogTransform(base=(10,0,0))
    
    # build correlation lines
    corr_bins, corr_bins_scale = gen_corr_bins(10, 1/ACQUISITION_RATE, 1, no_zero=True)
    corr_pos_all = np.vstack([corr_bins, np.zeros(corr_bins.size)]).T
    corr_line_all = scene.visuals.Line(pos=corr_pos_all, parent=corr_node, color='w')
    corr_pos_auto = {i:np.vstack([corr_bins, np.zeros(corr_bins.size)]).T for i in range(CHANNELS)}
    corr_line_auto = {i:scene.visuals.Line(pos=cp, parent=corr_node, color=c) for (i, cp), c in zip_color(corr_pos_auto.items(), colors, 'w')}
    corr_pos_cross = {i:np.vstack([corr_bins, np.zeros(corr_bins.size)]).T for i in combinations(range(CHANNELS), 2)}
    corr_line_cross = {i:scene.visuals.Line(pos=cp, parent=corr_node, color=c) for (i, cp), c in zip_color(corr_pos_cross.items(), cross_colors, 'w')}

    corr_gridlines = scene.GridLines(color=(1, 1, 1, 1), parent=corr_node)

    corr_yax = scene.AxisWidget(orientation='left', axis_label="G(tau)")
    grid.add_widget(corr_yax, GRID_ROWS, 0, row_span=GRID_ROWS)
    corr_yax.link_view(corr_view)

    corr_xax = scene.AxisWidget(orientation='bottom', axis_label="log(tau) (s)", tick_label_margin=15)
    grid.add_widget(corr_xax, 2*GRID_ROWS, 1, row_span=2, col_span=GRID_COLS)
    corr_xax.link_view(corr_view)
    

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
            transfer_idx -= transfer_idx % CHANNELS

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
        
        for ph_line, pos_l in zip(ph_lines, pos_ph):
            ph_line.set_data(pos_l)

        progress_bar.set_data(last_update_idx)
        
        scene_canvas.update()
    
    def update_corr(ev):
        nonlocal last_update_idx, last_transfer_idx
        nonlocal auto_align_mutex, auto_align_awaits, auto_align_start_idx, auto_align_end_idx
        cor_all = measurement_correlate_allbutton.isChecked()
        cor_auto = tuple(i for i, button in measurement_correlate_autobuttons.items() if button.checkState())
        cor_cross = tuple(i for i, button in measurement_correlate_crossbuttons.items() if button.checkState())
        
        transfer_idx = get_idx_fn()
        times_all, times = process_buffers(buf, transfer_idx, CHANNELS, tuple(range(CHANNELS)), cor_all)
        if cor_all and (times_all[-1] - times_all[0]) > corr_bins_scale[-1]:
            corr_pos_all[:,1] = pcorrelate(times_all, times_all, corr_bins_scale)
            corr_line_all.set_data(corr_pos_all)
        for i in cor_auto:
            if (times[i][-1] - times[i][0]) > corr_bins_scale[-1]:
                corr_pos_auto[i][:,1] = pcorrelate(times[i], times[i], corr_bins_scale)
                corr_line_auto[i].set_data(corr_pos_auto[i])
        for i, j in cor_cross:
            if (times[i][-1] - times[j][0]) > corr_bins_scale[-1]:
                corr_pos_cross[i,j][:,1] = pcorrelate(times[i], times[i], corr_bins_scale)
                corr_line_cross[i,j].set_data(corr_pos_cross[i,j])
        scene_canvas.update()
    
    timer = app.Timer(interval='auto')
    timer.connect(update)
    timer.start()

    
    def auto_align_measure_fn(secs):
        nonlocal auto_align_mutex, auto_align_awaits, auto_align_start_idx, auto_align_end_idx
        with auto_align_mutex:
            auto_align_awaits = True
            auto_align_start_idx = None
        time.sleep(secs)
        with auto_align_mutex:
            if not auto_align: # auto align was stopped in the meantime.
                return None
            if auto_align_end_idx < auto_align_start_idx:
                auto_align_end_idx = BUFFER_SIZE
            return np.mean(buf[auto_align_start_idx:auto_align_end_idx]) / CHANNELS * 1000

    def remove_correlation():
        corr_timer.stop()
        grid.remove_widget(corr_view)
        grid.remove_widget(corr_yax)
        grid.remove_widget(corr_xax)
        corr_view.parent = None
        corr_yax.parent = None
        corr_xax.parent = None
        measurement_correlate_allbutton.setEnabled(False)
        for button in measurement_correlate_autobuttons.values():
            button.setEnabled(False)
        for button in measurement_correlate_crossbuttons.values():
            button.setEnabled(False)
        measurement_correlate_bins_group.setEnabled(False)
    
    def insert_correlation():
        grid.add_widget(corr_view, row=GRID_ROWS, col=1, row_span=GRID_ROWS, col_span=GRID_COLS)
        grid.add_widget(corr_yax, GRID_ROWS, 0, row_span=GRID_ROWS)
        grid.add_widget(corr_xax, 2*GRID_ROWS, 1, row_span=2, col_span=GRID_COLS)
            
        measurement_correlate_allbutton.setEnabled(True)
        for button in measurement_correlate_autobuttons.values():
            button.setEnabled(True)
        for button in measurement_correlate_crossbuttons.values():
            button.setEnabled(True)
        measurement_correlate_bins_group.setEnabled(True)
    
    corr_timer = app.Timer(interval=10)
    corr_timer.connect(update_corr)
        
    def toggle_correlation():
        nonlocal correlate
        if correlate:
            remove_correlation()
        else:
            insert_correlation()
        correlate = not correlate
    
    def update_corr_timer(t):
        corr_timer.stop()
        corr_timer.start(interval=t)
                
    def update_corr_bins(t):
        nonlocal corr_bins, corr_bins_scale
        nonlocal corr_pos_all, corr_line_all, corr_pos_auto, corr_line_auto, corr_pos_cross, corr_line_cross
        tmin = measurement_correlate_mintime.value()
        tmax = measurement_correlate_maxtime.value()
        nbins = measurement_correlate_nbins.value()
        corr_bins, corr_bins_scale = gen_corr_bins(nbins, tmin, tmax, no_zero=tmin>=1/ACQUISITION_RATE)
        if measurement_correlate_allbutton.checkState():
            corr_pos_all = np.vstack([corr_bins, np.zeros((corr_bins.size))]).T
            corr_line_all.set_data(corr_pos_all)
        for i, button in measurement_correlate_autobuttons.items():
            if button.checkState():
                corr_pos_auto[i] = np.vstack([corr_bins, np.zeros((corr_bins.size))]).T
                corr_line_auto[i].set_data(corr_pos_auto[i])
        for i, button in measurement_correlate_crossbuttons.items():
            if button.checkState():
                corr_pos_cross[i] = np.vstack([corr_bins, np.zeros((corr_bins.size))]).T
                corr_line_cross[i].set_data(corr_pos_cross[i])
        
    
    def update_corr_checked():
        nonlocal corr_pos_all, corr_line_all, corr_pos_auto, corr_line_auto, corr_pos_cross, corr_line_cross
        if measurement_correlate_allbutton.checkState():
            if np.all(corr_pos_all == 0):
                corr_pos_all[:,0] = corr_bins
        else:
            corr_pos_all[:,:] = 0
            corr_line_all.set_data(corr_pos_all)
        for i, button in measurement_correlate_autobuttons.items():
            if button.checkState():
                corr_pos_auto[i][:,0] = corr_bins
            else:
                corr_pos_auto[i][:,:] = 0
                corr_line_auto[i].set_data(corr_pos_auto[i])
                
        for i, button in measurement_correlate_crossbuttons.items():
            if button.checkState():
                corr_pos_auto[i] = np.vstack([corr_bins, np.zeros((corr_bins.size))]).T
            else:
                if corr_pos_cross[i].shape[0] > 2:
                    corr_pos_cross[i][:,:] = 0
                    corr_line_cross[i].set_data(corr_pos_cross[i])
        scene_canvas.update()
    

    w = QMainWindow()
    w.setWindowTitle("Noisy Lines Simulator v0.1.2")
    widget = QWidget()
    w.setCentralWidget(widget)
    widget.setLayout(QVBoxLayout())

    autoalign_frame = QFrame(widget)
    widget.layout().addWidget(autoalign_frame)
    autoalign_layout = QHBoxLayout(autoalign_frame)
    
    autoalign_toggle_button = QPushButton("Autoalign Axis")
    autoalign_toggle_button.setCheckable(True)
    autoalign_toggle_button.setChecked(False)
    autoalign_toggle_button.setEnabled(has_align and not mock)
    autoalign_layout.addWidget(autoalign_toggle_button)
    
    autoalign_toggle_button.clicked.connect(lambda: toggle_auto_align(auto_align_measure_fn))

    measurement_frame = QFrame(widget)
    measurement_layout = QHBoxLayout(measurement_frame)
    

    # Measurement type/filename box
    measurement_type_group = QGroupBox("Storage Type", measurement_frame)
    measurement_layout.addWidget(measurement_type_group)

    measurement_type_group_layout = QFormLayout(measurement_type_group)
    
    # Toggle Measuring button
    measurement_toggle_button = QPushButton("Toggle Measurement")
    measurement_toggle_button.setCheckable(True)
    measurement_toggle_button.setChecked(False)
    measurement_toggle_button.clicked.connect(acquisit_fun)

    measurement_type_group_layout.addRow(measurement_toggle_button)

    # Radio buttons HDF5 or CSV
    measurement_type_select_hdf5 = QRadioButton("HDF5")
    measurement_type_select_hdf5.setChecked(True)
    # measurement_type_group_layout.addRow(measurement_type_select_hdf5)
    measurement_type_select_csv = QRadioButton("CSV")
    measurement_type_group_layout.addRow(measurement_type_select_hdf5, measurement_type_select_csv)

    measurement_type_select_hdf5.clicked.connect(
        lambda: set_measurement_type("HDF5")
    )
    measurement_type_select_csv.clicked.connect(
        lambda: set_measurement_type("CSV")
    )
    
    measurement_type_seconds_label = QLabel("Measurement duration (s)")
    measurement_type_seconds_input = QSpinBox()
    measurement_type_seconds_input.setRange(1, 301)
    measurement_type_group_layout.addRow(measurement_type_seconds_label, measurement_type_seconds_input)

    measurement_type_seconds_input.valueChanged.connect(set_measurement_seconds)
    
    
    measurement_type_filenamelabel = QLabel("Filename:")
    measurement_type_filename = QLineEdit()
    measurement_type_group_layout.addRow(measurement_type_filenamelabel, measurement_type_filename)

    # measurement_settings = QGroupBox("Measurement Settings", measurement_frame)
    # measurement_layout.addWidget(measurement_settings)

    # Measurement type/filename box
    measurement_correlate_bins_group = QGroupBox("Correlation Bins", measurement_frame)
    measurement_layout.addWidget(measurement_correlate_bins_group)

    measurement_correlate_bins_group_layout = QFormLayout(measurement_correlate_bins_group)
    
    
    # Correlation min/max
    measurement_correlate_mintime_label = QLabel("Min (s)")
    measurement_correlate_mintime = QDoubleSpinBox(decimals=6)
    measurement_correlate_mintime.setRange(0.5/ACQUISITION_RATE, 10.0)
    measurement_correlate_mintime.setValue(1/ACQUISITION_RATE)
    measurement_correlate_mintime.valueChanged.connect(update_corr_bins)
    
    measurement_correlate_maxtime_label = QLabel("Max (s)")
    measurement_correlate_maxtime = QDoubleSpinBox(decimals=5)
    measurement_correlate_maxtime.setRange(1/ACQUISITION_RATE, 10.0)
    measurement_correlate_maxtime.setValue(1.0)
    measurement_correlate_maxtime.valueChanged.connect(update_corr_bins)
    
    measurement_correlate_nbins_label = QLabel("# of bins")
    measurement_correlate_nbins = QSpinBox()
    measurement_correlate_nbins.setRange(2, 50)
    measurement_correlate_nbins.setValue(10)
    measurement_correlate_nbins.valueChanged.connect(update_corr_bins)
    
    measurement_correlate_bins_group_layout.addRow(measurement_correlate_mintime_label, measurement_correlate_mintime, )
    measurement_correlate_bins_group_layout.addRow(measurement_correlate_maxtime_label, measurement_correlate_maxtime, )
    measurement_correlate_bins_group_layout.addRow(measurement_correlate_nbins_label, measurement_correlate_nbins, )
    
    measurement_correlate_freq_label = QLabel("Update frequency (seconds)")
    measurment_correlate_freq = QSpinBox()
    measurment_correlate_freq.setRange(0, 300)
    measurment_correlate_freq.setValue(10)
    measurment_correlate_freq.valueChanged.connect(update_corr_timer)
    
    measurement_correlate_bins_group_layout.addRow(measurement_correlate_freq_label, measurment_correlate_freq)
    
    # Correlation setings
    measurement_correlate_group = QGroupBox("Correlation Types", measurement_frame)
    measurement_layout.addWidget(measurement_correlate_group)
    
    measurement_correlate_layout = QFormLayout(measurement_correlate_group)
    
    
    # Toggle button for coorelation
    measurement_correlation_toggle_button = QPushButton("Toggle Correlation")
    measurement_correlate_layout.addRow(measurement_correlation_toggle_button)
    measurement_correlation_toggle_button.clicked.connect(toggle_correlation)
    
    
    # Check boxes for correlate
    measurement_correlate_allbutton = QCheckBox("all auto")
    measurement_correlate_autobuttons = {i:QCheckBox(f"auto: {i}") for i in range(CHANNELS)}
    measurement_correlate_crossbuttons = {(i,j):QCheckBox(f"cross: {i}, {j}") 
                                          for i, j in combinations(range(CHANNELS), 2)}
    
            
        
    measurement_correlate_allbutton.setChecked(auto)
    measurement_correlate_allbutton.stateChanged.connect(update_corr_checked)
    for autobutton in measurement_correlate_autobuttons.values():
        autobutton.setChecked(auto)
        autobutton.stateChanged.connect(update_corr_checked)
    for crossbutton in measurement_correlate_crossbuttons.values():
        crossbutton.setChecked(cross)
        crossbutton.stateChanged.connect(update_corr_checked)
    
    
    measurement_correlate_layout.addRow(measurement_correlate_allbutton)
    measurement_correlate_autobuttons_list = list(measurement_correlate_autobuttons.values())
    for n in range(int(np.ceil(len(measurement_correlate_autobuttons)/2))):
        measurement_correlate_layout.addRow(*measurement_correlate_autobuttons_list[2*n:2*n+2])
    measurement_correlate_crossbuttons_list = list(measurement_correlate_crossbuttons.values())
    for n in range(int(np.ceil(len(measurement_correlate_crossbuttons)/2))):
        measurement_correlate_layout.addRow(*measurement_correlate_crossbuttons_list[2*n:2*n+2])
    
    
    

    # Type selection disabled when measurement is running
    measurement_toggle_button.clicked.connect(measurement_type_group.setDisabled)
    # measurement_toggle_button.clicked.connect(measurement_settings.setDisabled)

    widget.layout().addWidget(measurement_frame)
    widget.layout().addWidget(autoalign_frame)
    widget.layout().addWidget(scene_canvas.native, stretch=1)
    w.show()
    
    if correlate:
        update_corr_bins(0)
        corr_timer.start()
    else:
        remove_correlation()
    

    global stop_measurement
    def stop_fn():
        print("Stop fn!")
        measurement_toggle_button.setChecked(False)
        measurement_type_group.setEnabled(True)
        # measurement_settings.setEnabled(True)

    stop_measurement = stop_fn
    
    def reset_auto_align_fn():
        global auto_align
        global auto_align_thread
        autoalign_toggle_button.setChecked(False)
        auto_align = False
        auto_align_thread = None

    if sys.flags.interactive != 1:
        app.run()

def get_filename():
    global current_filename
    if current_filename:
        filename = current_filename
    else:
        filename = f'measurement_{int(time.time())}'
    current_filename = ''
    return filename
        

# Global variables that will be read from main / acquisition parts
# TODO: change these to accessors

# Communicate via global variables coz I can't find a better way.

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
