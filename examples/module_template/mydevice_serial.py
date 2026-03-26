"""
Serial transport for the Vendor DeviceName.

Implements the transport layer for RS-232 serial communication.
Device-specific commands are inherited from MyDeviceCommands,
keeping the command interface consistent with SSH and Telnet.

Authors

- Your Name
"""

import serial  # PySerial

from peat import DeviceData, log

from .mydevice_commands import MyDeviceCommands


class MyDeviceSerial(MyDeviceCommands):
    """Serial transport for the Vendor DeviceName.

    Inherits device commands from MyDeviceCommands and implements
    the serial-specific transport (connect, send, disconnect).

    Example usage:

        >>> ser = MyDeviceSerial("/dev/ttyUSB0", baudrate=9600, timeout=5.0)
        >>> ser.connect(username="", password="")
        True
        >>> ser.get_config()  # inherited from MyDeviceCommands
        '...'
        >>> ser.disconnect()
    """

    # TODO: Adjust serial parameters for your device
    DEFAULT_BAUDRATE = 9600
    BYTESIZE = serial.EIGHTBITS
    PARITY = serial.PARITY_NONE
    STOPBITS = serial.STOPBITS_ONE

    def __init__(
        self,
        serial_port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = 5.0,
    ) -> None:
        super().__init__(ip=serial_port, timeout=timeout)
        self.serial_port = serial_port
        self.baudrate = baudrate
        self._serial: serial.Serial | None = None

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"{self.serial_port}, {self.baudrate}, {self.timeout})"
        )

    @property
    def connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Transport implementation
    # ------------------------------------------------------------------

    def connect(self, username: str = "", password: str = "") -> bool:
        """Open the serial port and optionally authenticate.

        Args:
            username: Login username (if device requires authentication).
            password: Login password (if device requires authentication).

        Returns:
            True if the connection was successful.
        """
        try:
            self._serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                bytesize=self.BYTESIZE,
                parity=self.PARITY,
                stopbits=self.STOPBITS,
                timeout=self.timeout,
            )

            # TODO: Implement device-specific login sequence if needed.
            # Some devices require sending credentials over serial:
            #   self._serial.write(b"\r\n")
            #   self._serial.read_until(b"login: ")
            #   self._serial.write(username.encode() + b"\r\n")
            #   self._serial.read_until(b"Password: ")
            #   self._serial.write(password.encode() + b"\r\n")

            self.log.debug(f"Serial connected to {self.serial_port}")
            return True
        except Exception as err:
            self.log.warning(f"Serial connection to {self.serial_port} failed: {err}")
            self._serial = None
            return False

    def disconnect(self) -> None:
        """Close the serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def send_command(self, command: str) -> str:
        """Send a command over serial and return the output."""
        if not self.connected:
            self.log.warning("Cannot send command: not connected")
            return ""

        try:
            # Clear any pending input
            self._serial.reset_input_buffer()

            # Send command
            self._serial.write(
                command.encode(self.ENCODING) + self.LINE_TERMINATOR.encode(self.ENCODING)
            )

            # TODO: Read until prompt or timeout.
            # The read strategy depends on your device's behavior:
            #   - Fixed-length responses: self._serial.read(n)
            #   - Prompt-terminated: read_until(prompt_bytes)
            #   - Time-based: read all available after a delay
            #
            # response = self._serial.read_until(b"prompt>")
            # return response.decode(self.ENCODING).strip()
            return ""
        except Exception as err:
            self.log.warning(f"Command '{command}' failed on {self.serial_port}: {err}")
            return ""


__all__ = ["MyDeviceSerial"]
