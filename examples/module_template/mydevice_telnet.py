"""
Telnet transport for the Vendor DeviceName.

Implements the transport layer for Telnet communication. Device-specific
commands are inherited from MyDeviceCommands, keeping the command
interface consistent with the SSH transport.

Authors

- Your Name
"""

from peat.protocols import Telnet

from .mydevice_commands import MyDeviceCommands


class MyDeviceTelnet(MyDeviceCommands):
    """Telnet transport for the Vendor DeviceName.

    Inherits device commands from MyDeviceCommands and implements
    the Telnet-specific transport (connect, send, disconnect).

    Example usage:

        >>> tn = MyDeviceTelnet("192.168.1.1", port=23, timeout=5.0)
        >>> tn.connect(username="admin", password="secret")
        True
        >>> tn.get_config()  # inherited from MyDeviceCommands
        '...'
        >>> tn.disconnect()
    """

    def __init__(self, ip: str, port: int = 23, timeout: float = 5.0) -> None:
        super().__init__(ip, timeout)
        self.port = port
        self._telnet: Telnet | None = None

    @property
    def connected(self) -> bool:
        return self._telnet is not None

    # ------------------------------------------------------------------
    # Transport implementation
    # ------------------------------------------------------------------

    def connect(self, username: str, password: str) -> bool:
        """Establish a Telnet connection and authenticate."""
        try:
            self._telnet = Telnet(self.ip, self.port, self.timeout)

            # TODO: Implement device-specific login sequence.
            # Typical pattern:
            #   self._telnet.read_until(b"login: ")
            #   self._telnet.write(username.encode() + b"\n")
            #   self._telnet.read_until(b"Password: ")
            #   self._telnet.write(password.encode() + b"\n")

            self.log.debug(f"Telnet connected to {self.ip}")
            return True
        except Exception as err:
            self.log.warning(f"Telnet connection to {self.ip} failed: {err}")
            self._telnet = None
            return False

    def disconnect(self) -> None:
        """Close the Telnet connection."""
        if self._telnet:
            self._telnet.close()
            self._telnet = None

    def send_command(self, command: str) -> str:
        """Send a command over Telnet and return the output."""
        if not self.connected:
            self.log.warning("Cannot send command: not connected")
            return ""

        try:
            # TODO: Implement command send and response capture.
            # self._telnet.write(command.encode() + b"\n")
            # response = self._telnet.read_until(
            #     self.PROMPT_PATTERN.encode(), timeout=self.timeout
            # )
            # return response.decode(self.ENCODING).strip()
            return ""
        except Exception as err:
            self.log.warning(f"Command '{command}' failed on {self.ip}: {err}")
            return ""


__all__ = ["MyDeviceTelnet"]
