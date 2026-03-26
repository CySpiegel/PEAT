"""
Telnet interface for the Vendor DeviceName.

Handles all Telnet-based communication with the device, including
authentication, command execution, and response processing.

Authors

- Your Name
"""

from peat import DeviceData, log
from peat.protocols import Telnet


class MyDeviceTelnet:
    """Telnet interface for the Vendor DeviceName.

    Wraps the base Telnet protocol class with device-specific
    command sequences and prompt handling.

    Example usage:

        >>> tn = MyDeviceTelnet("192.168.1.1", port=23, timeout=5.0)
        >>> tn.connect(username="admin", password="secret")
        True
        >>> tn.get_config()
        '...'
        >>> tn.disconnect()
    """

    def __init__(self, ip: str, port: int = 23, timeout: float = 5.0) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.log = log.bind(classname=self.__class__.__name__)
        self._telnet: Telnet | None = None

    @property
    def connected(self) -> bool:
        return self._telnet is not None

    def connect(self, username: str, password: str) -> bool:
        """Establish a Telnet connection and authenticate.

        Args:
            username: Telnet username.
            password: Telnet password.

        Returns:
            True if connection and authentication were successful.
        """
        try:
            self._telnet = Telnet(self.ip, self.port, self.timeout)

            # TODO: Implement device-specific login sequence.
            # Typical pattern:
            #   1. Wait for "Username:" or "login:" prompt
            #   2. Send username
            #   3. Wait for "Password:" prompt
            #   4. Send password
            #   5. Verify successful login (check for command prompt)
            #
            # self._telnet.read_until(b"login: ")
            # self._telnet.write(username.encode() + b"\n")
            # self._telnet.read_until(b"Password: ")
            # self._telnet.write(password.encode() + b"\n")

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

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def run_command(self, command: str) -> str:
        """Execute a command on the device and return the output.

        Args:
            command: Command string to send.

        Returns:
            Command output as a string, or empty string on failure.
        """
        if not self.connected:
            self.log.warning("Cannot run command: not connected")
            return ""

        try:
            # TODO: Implement command execution and response capture.
            # self._telnet.write(command.encode() + b"\n")
            # response = self._telnet.read_until(b"prompt>", timeout=self.timeout)
            # return response.decode().strip()
            return ""
        except Exception as err:
            self.log.warning(f"Command '{command}' failed on {self.ip}: {err}")
            return ""

    def get_config(self) -> str:
        """Retrieve the device configuration via Telnet.

        TODO: Replace with the actual command(s) for your device.

        Returns:
            Configuration data as a string.
        """
        # TODO: Implement device-specific config retrieval
        # return self.run_command("show config")
        return ""

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def pull_and_process(self, dev: DeviceData) -> bool:
        """Pull all data over Telnet and process into the data model.

        TODO: Implement the Telnet pull workflow for your device.

        Returns:
            True if at least one operation was successful.
        """
        success = False

        # TODO: Implement device-specific Telnet pull logic
        # Example:
        # config_output = self.get_config()
        # if config_output:
        #     dev.write_file(config_output, "telnet_config.txt")
        #     success = True

        return success


__all__ = ["MyDeviceTelnet"]
