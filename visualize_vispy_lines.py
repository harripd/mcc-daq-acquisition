import numpy as np
import sys

from vispy import gloo, app, visuals, scene

# size of canvas
# todo: how to set this, like really I dunno
canvas_size = (3000, 800) # width,height

# vertex positions of data to draw
N = canvas_size[0]

GRID_COLS=8
GRID_ROWS=5

DUALCHANNEL = True

pos_green = np.zeros((N, 2), dtype=np.float32)
pos_green[:, 0] = np.linspace(0, canvas_size[0], N)
pos_green[:,1] = None

if(DUALCHANNEL):
    pos_red = np.zeros((N, 2), dtype=np.float32)
    pos_red[:, 0] = np.linspace(0, canvas_size[0], N)
    pos_red[:,1] = None


def visualize(buf, ctrdev, SAMPLES_PER_SECOND, bufsize, num_channels):
    if (num_channels == 2 and not DUALCHANNEL) or DUALCHANNEL and num_channels != 2:
        print("wrong setup: If you use 2 channels you have to set DUALCHANNEL and vice versa!")
        exit(0)

    win = scene.SceneCanvas(size=canvas_size, keys='interactive', show=True, fullscreen=False)
    grid = win.central_widget.add_grid()
    
    view = grid.add_view(
        row = 0,
        col=1,
        row_span=GRID_ROWS,
        col_span=GRID_COLS,
        camera='panzoom',
        border_color='grey'
    )

    view.camera.rect = (0, 0, canvas_size[1], canvas_size[0])

    progress_bar = scene.visuals.InfiniteLine(0, parent=view.scene)

    green_line = scene.visuals.Line(pos=pos_green,color='g',parent=view.scene)

    if(DUALCHANNEL):
        red_line = scene.visuals.Line(pos=pos_red,color='r',parent=view.scene)

    gridlines = scene.GridLines(color=(1, 1, 1, 1), parent=view.scene)

    yax = scene.AxisWidget(orientation='left', axis_label="Counts")
    grid.add_widget(yax, 0, 0, row_span=GRID_ROWS)
    yax.link_view(view)

    # TODO: fix for canvas_size != N
    xax = scene.AxisWidget(orientation='bottom', axis_label=f"Time in (1/{SAMPLES_PER_SECOND})s",tick_label_margin=15)
    grid.add_widget(xax, GRID_ROWS, 1, col_span=GRID_COLS)
    xax.link_view(view)



    last_transfer_idx = 0
    last_update_idx = 0
    def update(ev):
        nonlocal last_update_idx, last_transfer_idx
        (_, transferstatus) = ctrdev.get_scan_status()
        transfer_idx = transferstatus.current_index - 1
        if transfer_idx % 2 != 0:
            #transfer of 1 channel is ahead, reading that sample next time
            transfer_idx -= 1

        if(last_transfer_idx == transfer_idx):
            # TODO: could we miss a whole cycle? Very low probability
            return

        # TODO: transfer data method
        if(transfer_idx < last_transfer_idx):
            for i in range(last_transfer_idx, bufsize, num_channels):
                pos_green[last_update_idx,1] = buf[i]
                if DUALCHANNEL:
                    pos_red[last_update_idx,1] = buf[i+1]
                last_update_idx = (last_update_idx + 1) % N
                #print("g:", buf[i],"\t", "r:", buf[i+1])
            last_transfer_idx = 0
        for i in range(last_transfer_idx, transfer_idx, num_channels):
            pos_green[last_update_idx,1] = buf[i]
            if DUALCHANNEL:
                pos_red[last_update_idx,1] = buf[i+1]
            last_update_idx = (last_update_idx + 1) % N
            #print("g:", buf[i],"\t", "r:", buf[i+1])
        last_transfer_idx = transfer_idx

        green_line.set_data(pos_green)

        if DUALCHANNEL:
            red_line.set_data(pos_red)

        # could be simplified when N = canvas_size[0]
        progress_bar.set_data(pos_green[last_update_idx,0])

        win.update()

    timer = app.Timer(interval='auto')
    timer.connect(update)
    timer.start()

    if sys.flags.interactive != 1:
        app.run()
