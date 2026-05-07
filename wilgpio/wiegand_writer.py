# wiegand_writer.py
import time
import lgpio
from typing import Optional


class WiegandWriter:
    """
    Wiegand protocol transmitter (D0 + D1 lines).
    """

    def __init__(
        self,
        chip_num: int,
        d0_pin: int,
        d1_pin: int,
        active_low: bool = False,
    ) -> None:
        """
        Initialize Wiegand writer.

        Args:
            chip_num (int): GPIO chip number.
            d0_pin (int): GPIO pin for D0 line.
            d1_pin (int): GPIO pin for D1 line.
            active_low (bool): If True, output signals will be inverted.

        Raises:
            ValueError: If D0 and D1 pins are the same.
            IOError: If GPIO initialization fails.
        """
        if d0_pin == d1_pin:
            raise ValueError("D0 and D1 pins must be different")

        self.__chip_num = chip_num
        self.__d0_pin = d0_pin
        self.__d1_pin = d1_pin
        self.__active_low = active_low
        self.__handle: int = -1

        self._init_gpio()

    def _init_gpio(self) -> None:
        """Initialize GPIO outputs."""
        try:
            self.__handle = lgpio.gpiochip_open(self.__chip_num)
            if self.__handle < 0:
                raise IOError(f"Failed to open gpiochip{self.__chip_num}")

            lgpio.gpio_claim_output(self.__handle, self.__d0_pin)
            lgpio.gpio_claim_output(self.__handle, self.__d1_pin)

            # Set idle state
            self.__write_physical_level(self.__d0_pin, 0)
            self.__write_physical_level(self.__d1_pin, 0)

            print(f"WiegandWriter: Initialized on D0={self.__d0_pin}, D1={self.__d1_pin} "
                  f"(active_low={self.__active_low})")
        except Exception as e:
            print(f"Error initializing WiegandWriter: {e}")
            self.stop()
            raise

    def __write_physical_level(self, pin: int, logical_value: int) -> None:
        """Write physical level considering active_low setting."""
        physical = 1 - logical_value if self.__active_low else logical_value
        lgpio.gpio_write(self.__handle, pin, physical)

    def send(
        self,
        data: str,
        pulse_us: int = 50,
        gap_us: int = 2000,
    ) -> None:
        """
        Transmit a Wiegand code.

        Args:
            data (str): String of '0' and '1' characters.
            pulse_us (int): Pulse width in microseconds (default 50).
            gap_us (int): Gap between bits in microseconds (default 2000).

        Raises:
            RuntimeError: If writer is not initialized.
            ValueError: If data is invalid or timings are non-positive.
        """
        if self.__handle < 0:
            raise RuntimeError("WiegandWriter is not initialized")

        if not data or not all(c in "01" for c in data):
            raise ValueError("data must be a non-empty string containing only '0' and '1'")

        if pulse_us <= 0 or gap_us <= 0:
            raise ValueError("pulse_us and gap_us must be positive integers")

        try:
            # Ensure idle state before transmission
            self.__write_physical_level(self.__d0_pin, 0)
            self.__write_physical_level(self.__d1_pin, 0)
            time.sleep(pulse_us / 1_000_000)

            for bit in data:
                target_pin = self.__d0_pin if bit == '0' else self.__d1_pin

                self.__write_physical_level(target_pin, 1)   # Active pulse
                time.sleep(pulse_us / 1_000_000)

                self.__write_physical_level(target_pin, 0)   # Back to idle
                time.sleep(gap_us / 1_000_000)

            print(f"WiegandWriter: Successfully sent {len(data)}-bit sequence")
        except Exception as e:
            print(f"Error during Wiegand transmission: {e}")
            raise

    def stop(self) -> None:
        """Stop writer and release GPIO resources."""
        if self.__handle >= 0:
            try:
                self.__write_physical_level(self.__d0_pin, 0)
                self.__write_physical_level(self.__d1_pin, 0)
                lgpio.gpio_free(self.__handle, self.__d0_pin)
                lgpio.gpio_free(self.__handle, self.__d1_pin)
                lgpio.gpiochip_close(self.__handle)
            except Exception:
                pass
            self.__handle = -1

    def __del__(self) -> None:
        self.stop()
