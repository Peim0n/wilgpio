# gpio_listener.py
import lgpio
from typing import Callable, Optional, Literal

EdgeType = Literal["rising", "falling", "both"]


def _edge_to_lgpio(edge: EdgeType) -> int:
    mapping = {
        "rising": lgpio.RISING_EDGE,
        "falling": lgpio.FALLING_EDGE,
        "both": lgpio.BOTH_EDGES,
    }
    if edge not in mapping:
        raise ValueError(f"Invalid edge type: '{edge}'. Must be 'rising', 'falling' or 'both'.")
    return mapping[edge]


class GpioListener:
    """
    Universal GPIO pin state listener with interrupt support.
    """

    def __init__(
        self,
        chip_num: int,
        pin_num: int,
        callback_func: Optional[Callable[[int, int, int], None]] = None,
        active_low: bool = False,
        edge_type: EdgeType = "both",
    ) -> None:
        """
        Args:
            chip_num (int): GPIO chip number (usually 0).
            pin_num (int): BCM GPIO pin number.
            callback_func: Callback called on edge. Signature: (gpio, level, tick) -> None
            active_low (bool): Invert logical level.
            edge_type (str): 'rising', 'falling' or 'both'.
        """
        if chip_num < 0 or pin_num < 0:
            raise ValueError("chip_num and pin_num must be >= 0")

        self.__chip_num = chip_num
        self.__pin_num = pin_num
        self.__callback_func = callback_func
        self.__active_low = active_low
        self.__edge_type = _edge_to_lgpio(edge_type)

        self.__handle: int = -1
        self.__cb_id: int = -1

        self._init_gpio()

    def _init_gpio(self) -> None:
        try:
            self.__handle = lgpio.gpiochip_open(self.__chip_num)
            if self.__handle < 0:
                raise IOError(f"Failed to open gpiochip{self.__chip_num}")

            lgpio.gpio_claim_alert(self.__handle, self.__pin_num, self.__edge_type)
            self.__cb_id = lgpio.callback(
                self.__handle, self.__pin_num, self.__edge_type, self.__internal_callback
            )

            print(f"GpioListener: Pin {self.__pin_num} configured "
                  f"(edge={self.__edge_type}, active_low={self.__active_low})")
        except Exception as e:
            print(f"Error initializing GpioListener pin {self.__pin_num}: {e}")
            self.stop()
            raise

    def __internal_callback(self, chip: int, gpio: int, level: int, tick: int) -> None:
        processed_level = 1 - level if self.__active_low else level
        if self.__callback_func:
            try:
                self.__callback_func(gpio, processed_level, tick)
            except Exception as e:
                print(f"Callback error on pin {self.__pin_num}: {e}")

    def read_level(self) -> int:
        """Return current logical level (0/1) or -1 on error."""
        if self.__handle < 0:
            return -1
        try:
            raw = lgpio.gpio_read(self.__handle, self.__pin_num)
            return 1 - raw if self.__active_low else raw if raw >= 0 else -1
        except Exception as e:
            print(f"Read error pin {self.__pin_num}: {e}")
            return -1

    def stop(self) -> None:
        """Release GPIO resources."""
        if self.__cb_id >= 0:
            try:
                lgpio.callback_cancel(self.__cb_id)
            except Exception:
                pass
            self.__cb_id = -1

        if self.__handle >= 0:
            try:
                lgpio.gpio_free(self.__handle, self.__pin_num)
                lgpio.gpiochip_close(self.__handle)
            except Exception:
                pass
            self.__handle = -1

    def __del__(self) -> None:
        self.stop()
