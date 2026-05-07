# wiegand_reader.py
import threading
from typing import Callable, Optional

from .gpio_listener import GpioListener

_WIEGAND_FORMATS = {8: 8, 24: 24, 26: 26, 32: 32, 34: 34, 35: 35, 37: 37, 40: 40}
_WIEGAND_TIMEOUT_MS = 50


class WiegandReader:
    """
    Wiegand protocol reader supporting multiple formats.
    """

    def __init__(
        self,
        chip_num: int,
        d0_pin: int,
        d1_pin: int,
        wiegand_format: int = 26,
        data_callback: Optional[Callable[[str, int], None]] = None,
        active_low: bool = False,
    ) -> None:
        """
        Args:
            wiegand_format (int): One of: 26, 34, 37, etc.
            data_callback: Called when valid code received → (code_str, format)
        """
        if wiegand_format not in _WIEGAND_FORMATS:
            raise ValueError(f"Unsupported format {wiegand_format}. "
                           f"Supported: {list(_WIEGAND_FORMATS.keys())}")
        if d0_pin == d1_pin:
            raise ValueError("D0 and D1 pins must be different")

        self.__chip_num = chip_num
        self.__d0_pin = d0_pin
        self.__d1_pin = d1_pin
        self.__expected_bits = _WIEGAND_FORMATS[wiegand_format]
        self.__data_callback = data_callback
        self.__active_low = active_low

        self.__bits: list[int] = []
        self.__lock = threading.Lock()
        self.__timer: Optional[threading.Timer] = None

        self.__d0_listener: Optional[GpioListener] = None
        self.__d1_listener: Optional[GpioListener] = None

        self._init_listeners()

    def _init_listeners(self) -> None:
        try:
            self.__d0_listener = GpioListener(
                self.__chip_num, self.__d0_pin, self.__d0_callback,
                active_low=self.__active_low, edge_type="falling"
            )
            self.__d1_listener = GpioListener(
                self.__chip_num, self.__d1_pin, self.__d1_callback,
                active_low=self.__active_low, edge_type="falling"
            )
            print(f"WiegandReader: Ready for {self.__expected_bits}-bit format "
                  f"on D0={self.__d0_pin}, D1={self.__d1_pin}")
        except Exception as e:
            self.stop()
            raise

    def __d0_callback(self, gpio: int, level: int, tick: int) -> None:
        if level == 0:
            self.__add_bit(0)

    def __d1_callback(self, gpio: int, level: int, tick: int) -> None:
        if level == 0:
            self.__add_bit(1)

    def __add_bit(self, bit: int) -> None:
        with self.__lock:
            self.__bits.append(bit)
            if self.__timer and self.__timer.is_alive():
                self.__timer.cancel()
            self.__timer = threading.Timer(
                _WIEGAND_TIMEOUT_MS / 1000.0, self.__process_wiegand_data
            )
            self.__timer.start()

    def __process_wiegand_data(self) -> None:
        with self.__lock:
            bits = self.__bits
            self.__bits = []

            if len(bits) == self.__expected_bits:
                code = "".join(map(str, bits))
                if self.__data_callback:
                    try:
                        self.__data_callback(code, self.__expected_bits)
                    except Exception as e:
                        print(f"Callback error: {e}")
            elif len(bits) > 0:
                print(f"Wiegand length error: got {len(bits)}, expected {self.__expected_bits}")

    def get_d0_level(self) -> int:
        return self.__d0_listener.read_level() if self.__d0_listener else -1

    def get_d1_level(self) -> int:
        return self.__d1_listener.read_level() if self.__d1_listener else -1

    def stop(self) -> None:
        if self.__d0_listener:
            self.__d0_listener.stop()
        if self.__d1_listener:
            self.__d1_listener.stop()
        if self.__timer and self.__timer.is_alive():
            self.__timer.cancel()

    def __del__(self) -> None:
        self.stop()
