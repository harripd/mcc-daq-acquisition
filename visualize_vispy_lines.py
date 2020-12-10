import numpy as np
import sys

from vispy import gloo, app, visuals, scene

from config import *

# vertex positions of data to draw
N = CANVAS_SIZE[0]

# Leaves some space for the axes
# TODO: refine this
GRID_COLS=10
GRID_ROWS=7

# green channel
pos_green = np.zeros((N, 2), dtype=np.float32)
pos_green[:, 0] = np.linspace(0, N, N)
pos_green[:,1] = None

# red channel
pos_red = np.zeros((N, 2), dtype=np.float32)
pos_red[:, 0] = np.linspace(0, N, N)
pos_red[:,1] = None


def transfer_data(buf, canv_idx, transfer_from, transfer_to) -> (int, int):
    """
    Transfers data to canvas buffer, starting from transfer_from to transfer_to
    Returns new transfer_idx, new idx (to canvas) and sets pos_green, pos_red.
    """

    # print("transferring from buf[", transfer_from, "to", transfer_to, "] to canvas[", idx, "]")

    if(transfer_from == transfer_to):
        # TODO: could we miss a whole cycle? Very low probability
        return (transfer_from, canv_idx)

    #print(f"{transfer_from}-{transfer_to}")

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
            red_bin += buf[buf_idx + 1]
            buf_idx = (buf_idx + CHANNELS) % PLAIN_BUFFER_SIZE
        #print(f"canv[{canv_idx}] = bin from {buf_idx-SAMPLES_PER_BIN*CHANNELS} to {buf_idx}")
        pos_green[canv_idx,1] = green_bin
        pos_red[canv_idx,1] = red_bin
        canv_idx = (canv_idx +1) % N

    return (buf_idx, canv_idx)


def visualize(buf, get_idx_fn, update_callback_fn):

    win = scene.SceneCanvas(size=CANVAS_SIZE, keys='interactive', show=True, fullscreen=False)
    grid = win.central_widget.add_grid()
    
    view = grid.add_view(
        row = 0,
        col=1,
        row_span=GRID_ROWS,
        col_span=GRID_COLS,
        camera='panzoom',
        border_color='grey'
    )

    view.camera.rect = (0, 0, CANVAS_SIZE[1], CANVAS_SIZE[0])

    progress_bar = scene.visuals.InfiniteLine(0, parent=view.scene)
    green_line = scene.visuals.Line(pos=pos_green,color='g',parent=view.scene)
    red_line = scene.visuals.Line(pos=pos_red,color='r',parent=view.scene)
    gridlines = scene.GridLines(color=(1, 1, 1, 1), parent=view.scene)

    yax = scene.AxisWidget(orientation='left', axis_label="Counts")
    grid.add_widget(yax, 0, 0, row_span=GRID_ROWS)
    yax.link_view(view)

    xax = scene.AxisWidget(orientation='bottom', axis_label=f"Time in (1/{BIN_SIZE})s",tick_label_margin=15)
    grid.add_widget(xax, GRID_ROWS, 1, col_span=GRID_COLS)
    xax.link_view(view)


    last_transfer_idx = 0
    last_update_idx = 0
    def update(ev):
        nonlocal last_update_idx, last_transfer_idx

        update_callback_fn(buf)

        transfer_idx = get_idx_fn()
        if transfer_idx % CHANNELS != 0:
            # transfer of 1 channel is ahead, reading that sample next time
            # this shouldn't happen but let's add it for sanity anyways
            transfer_idx -= 1 # TODO: what if more channels?

        last_transfer_idx, last_update_idx = transfer_data(buf, last_update_idx, last_transfer_idx, transfer_idx)

        green_line.set_data(pos_green)
        red_line.set_data(pos_red)
        progress_bar.set_data(last_update_idx)

        win.update()

    timer = app.Timer(interval='auto')
    timer.connect(update)
    timer.start()

    if sys.flags.interactive != 1:
        app.run()
