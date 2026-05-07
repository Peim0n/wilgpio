# wilgpio

**Wiegand Protocol Library** for Orange Pi, Raspberry Pi and other single-board computers.

A clean, reliable and easy-to-use Python library for reading and writing Wiegand codes using the `lgpio` backend.

## Features

- Support for multiple Wiegand formats: **26, 34, 37, 32, 40** bits (and others)
- Simultaneous reading from multiple Wiegand readers
- Writing (emulating) Wiegand codes
- `active_low` signal inversion support
- Proper GPIO resource management and cleanup
- Thread-safe bit collection with timeout detection

## Installation

```bash
# Install system dependency
sudo apt update
sudo apt install python3-lgpio

# Install the library
pip install wilgpio
