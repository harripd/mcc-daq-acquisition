# Laser Piezo Autofocus

import numpy
import serial
import serial.tools.list_ports

from auto_align.ag_uc8 import AGUC8Control

def auto_align(measure_fn, should_stop_fn):
    # plugging in and out the usb id changes, so we just pick any and fail if there's more than one
    [comport] = serial.tools.list_ports.comports()
    control = AGUC8Control(
        port=str(comport.device),
        baudrate=912600,
        bytesize=serial.EIGHTBITS,
        timeout=1,
        parity=serial.PARITY_NONE,
    )
    
    measurements = []

    step_size = 100
    step_sizes = [(20, 0.2), (5, 0.2), (1, 0.1)]
    # direction we currently walk in (up or down in piezo units)
    up1 = True
    up2 = True
    steps_to_reduce = 4
    measure_secs = 0.4

    new = measure_fn(measure_secs)
    if new == None:
        return
    measurements = [new]
    
    while not should_stop_fn():
        if True:
            last = new
            control.move_till_idle(1, 1, step_size if up1 else -step_size)
            new = measure_fn(measure_secs)
            if new == None:
               return
            measurements.append(new)
            if new < last:
                # reverse direction
                up1 = not up1
            print(f"1 {new:>6.2f} {new - last:>6.2f} {'forward' if up1 else 'backward'}")
            if new * 3 < last:
                print(f"return! {last:.2f} {new:.2f}")
                control.move_till_idle(1, 1, step_size if up1 else -step_size)
                new = measure_fn(measure_secs)
                if new == None:
                    return
                if step_sizes:
                    measurements = [new]
                    (step_size, measure_secs) = step_sizes.pop(0)

        if True:
            last = new
            control.move_till_idle(1, 2, step_size if up2 else -step_size)
            new = measure_fn(measure_secs)
            if new == None:
                return
            measurements.append(new)
            if new < last:
                # reverse direction
                up2 = not up2
            print(f"2 {new:>6.2f} {new - last:>6.2f} {'forward' if up2 else 'backward'}")

            if new * 3 < last:
                print(f"return! {last:.2f} {new:.2f}")
                control.move_till_idle(1, 2, step_size if up2 else -step_size)
                new = measure_fn(measure_secs)
                if new == None:
                    return
                if step_sizes:
                    measurements = [new]
                    (step_size, measure_secs) = step_sizes.pop(0)

        # keep only the latest two measurements
        measurements = measurements[-steps_to_reduce:]
        if len(measurements) == steps_to_reduce and measurements[0] > measurements[-1]:
            if not step_sizes:
                print(
                    f"No improvement for {steps_to_reduce} steps ({measurements[0]:.2f} to {measurements[-1]:.2f}), done, exiting"
                )
                # End Alignment
                return
            else:
                print(
                    f"No improvement for {steps_to_reduce} steps ({measurements[0]:.2f} to {measurements[-1]:.2f}), "
                    f"reducing step size from {step_size} to {step_sizes[0]}"
                )
                measurements = []
                (step_size, measure_secs) = step_sizes.pop(0)
