import functools
from dataclasses import dataclass, field

from colorama import Fore as Clr
from pylink import JLink, JLinkException, JLinkInterfaces

CHIP_NAME_DEFAULT = 'STM32F407VE'

class JLinkDongleException(Exception):

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

@dataclass(slots=True)
class JLinkDongle:
    interface:JLinkInterfaces = JLinkInterfaces.SWD  # type: ignore
    speed:str|int = 'auto'
    chip_name:str = CHIP_NAME_DEFAULT
    jlink:JLink = field(init=False)

    @staticmethod
    def check_exception(func):
        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except JLinkException as e:
                if func.__name__ in {self.read_rtt.__name__, self.write_rtt.__name__}:
                    raise JLinkDongleException(f"Do not read/write from RTT Terminal")
                raise JLinkDongleException(
                    f"{Clr.RED}ERROR:{Clr.RESET} method name: {Clr.YELLOW}{func.__name__}{Clr.RESET} : {e}")
        return wrap

    @check_exception
    def connect(self):
        self.jlink = JLink()
        self.jlink.disable_dialog_boxes()
        self.jlink.open()
        self.jlink.rtt_stop()
        self.jlink.set_tif(JLinkInterfaces.SWD)
        self.jlink.connect(chip_name=self.chip_name, speed=self.speed, verbose=True) # type: ignore
        self.jlink.rtt_start()
        endian = int.from_bytes(self.jlink._device.EndianMode, 'big') # type: ignore
        endian = {0: "Little", 1: "Big"}.get(endian, f"Unknown ({endian})")
        print()
        print(f"Connected to: {self.chip_name}")
        print(f"RTT RX buffers at {self.jlink.speed} kHz")
        print(f"connected to {endian}-Endian {self.jlink.core_name()}")
        print(f"running at {self.jlink.cpu_speed() / 1e6:.3f} MHz")

    @check_exception
    def read_rtt(self, terminal_number:int = 0) -> list:
        return self.jlink.rtt_read(terminal_number, self.jlink.MAX_BUF_SIZE)

    @check_exception
    def write_rtt(self, data:bytes, terminal_number:int = 0) -> None:
        self.jlink.rtt_write(terminal_number, data)

    def read_rtt_string(self, terminal_number:int = 0) -> str:
        data = self.read_rtt(terminal_number=terminal_number)
        if data:
            return bytes(data).decode('utf-8')
        return ""

    def write_rtt_sring(self, data:str, terminal_number:int = 0) -> None:
        self.write_rtt(str.encode(data, 'utf-8'), terminal_number)

    @check_exception
    def reconnect(self):
        self.jlink.close()
        # self.jlink.rtt_stop()
        self.connect()