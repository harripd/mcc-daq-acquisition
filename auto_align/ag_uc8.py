"""
Parts taken from https://github.com/QCoDeS/Qcodes_contrib_drivers/blob/master/qcodes_contrib_drivers/drivers/Newport/AG_UC8.py
"""

from time import sleep

from serial import Serial

from auto_align.qcodes_delayed_keyboard_interrupt import DelayedKeyboardInterrupt


class AGUC8Control(Serial):
    """serial.Serial wrapper that encodes strings, add the CRLF, waits for the controller and handles
    channel state

    https://www.newport.com/mam/celum/celum_assets/np/resources/Agilis_Piezo_Motor_Driven_Components_User_Manual.pdf?0
    """

    command_delay = 0.002
    reset_delay = 0.05
    current_channel = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()
        version = self.ask("VE")
        print(version)
        if version.contains("UC2"):
            self.multichannel = False
        else:
            self.multichannel = True

    def write(self, cmd: str) -> None:
        with DelayedKeyboardInterrupt():
            super().write((cmd + "\r\n").encode())
            sleep(self.command_delay)
        self.check_error()

    def ask(self, cmd: str) -> str:
        with DelayedKeyboardInterrupt():
            super().write((cmd + "\r\n").encode())
            return super().readline().decode().strip()

    def select_channel(self, channel_number: int) -> None:
        if not self.multichannel: return
        """Make sure the specified channel is selected."""
        if self.current_channel != channel_number:
            self.write(f"CC{channel_number}")
            sleep(self.command_delay)
            _current_channel = channel_number

    def write_channel(self, channel_number: int, cmd: str) -> None:
        """Select specified channel, then apply specified command."""
        self.select_channel(channel_number)
        self.write(cmd)

    def ask_channel(self, channel_number: int, cmd: str) -> str:
        """Select specified channel, then apply specified query
        and return response."""
        self.select_channel(channel_number)
        return self.ask(cmd)

    def move(self, channel: int, axis: int, ticks: int):
        """PR: Move (channel, axis) by ticks"""
        self.write_channel(channel, f"{axis}PR{ticks}")

    def wait_till_idle(self, axis: int):
        while True:
            status = self.ask(f"{axis}TS")
            if status == f"{axis}TS0":
                break
            elif status == f"{axis}TS1":
                sleep(0.01)
            else:
                raise RuntimeError(f"Unknown axis status: '{status}'")

    def move_till_idle(self, channel: int, axis: int, ticks: int):
        self.move(channel, axis, ticks)
        self.wait_till_idle(axis)

    def reset(self) -> None:
        """Reset the motor controller."""
        # clear connection
        super().readall()
        # Send reset command.
        super().write(b"RS\r\n")
        sleep(self.reset_delay)
        # Switch controller to remote mode (many commands require remote mode).
        super().write(b"MR\r\n")
        sleep(self.command_delay)
        self.check_error()

    def check_error(self):
        with DelayedKeyboardInterrupt():
            super().write("TE\r\n".encode())
            resp = super().readline().decode()
        if resp.startswith("TE"):
            try:
                code = int(resp.strip()[2:])
                if code != 0:
                    print(f"Command error: {code}")
                else:
                    return
            except ValueError:
                # Parsing error code failed.
                # Ignore the error here, we will report it below.
                pass
        raise RuntimeError(f"Unexpected response to TE command: '{resp}'")
