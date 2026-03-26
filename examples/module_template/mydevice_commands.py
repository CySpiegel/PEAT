"""
Device command interface for the Vendor DeviceName.

Defines device-specific commands and response parsing in a
transport-agnostic way. Both SSH and Telnet helpers inherit
from this class, providing a unified command set regardless
of the underlying communication protocol.

This follows the same pattern as SELAscii in peat/modules/sel/,
where the command layer is shared between Telnet and Serial.

Authors

- Your Name
"""

import re
from abc import ABC, abstractmethod

from peat import DeviceData, log


class MyDeviceCommands(ABC):
    """Transport-agnostic command interface for the Vendor DeviceName.

    Subclasses (SSH, Telnet) must implement the transport methods:
    ``send_command``, ``connect``, and ``disconnect``. All device-specific
    commands and response parsing live here so they remain consistent
    across transports.

    Example usage (via a concrete subclass):

        >>> session = MyDeviceSSH("192.168.1.1")
        >>> session.connect(username="admin", password="secret")
        True
        >>> session.get_config()
        'hostname mydevice\\ninterface eth0 ...'
        >>> session.disconnect()
    """

    # TODO: Set device-specific constants
    ENCODING = "utf-8"
    LINE_TERMINATOR = "\r\n"
    PROMPT_PATTERN = re.compile(r"[\w\-]+[>#]\s*$")

    def __init__(self, ip: str, timeout: float = 5.0) -> None:
        self.ip = ip
        self.timeout = timeout
        self.log = log.bind(classname=self.__class__.__name__, target=self.ip)
        self.priv_level: int = 0

    # ------------------------------------------------------------------
    # Abstract transport methods (implemented by SSH/Telnet subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    def send_command(self, command: str) -> str:
        """Send a command and return the response.

        Args:
            command: Command string to send to the device.

        Returns:
            Command output as a string.
        """
        ...

    @abstractmethod
    def connect(self, username: str, password: str) -> bool:
        """Establish a connection to the device.

        Args:
            username: Login username.
            password: Login password.

        Returns:
            True if the connection was successful.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection."""
        ...

    @property
    @abstractmethod
    def connected(self) -> bool:
        """Whether the connection is currently active."""
        ...

    # ------------------------------------------------------------------
    # Device commands
    #
    # These are transport-agnostic. They call self.send_command()
    # which is implemented by the SSH or Telnet subclass.
    # ------------------------------------------------------------------

    def get_config(self) -> str:
        """Retrieve the running configuration.

        TODO: Replace with the actual command for your device.

        Returns:
            Configuration data as a string.
        """
        # TODO: Implement device-specific config command
        # return self.send_command("show running-config")
        return ""

    def get_version(self) -> str:
        """Retrieve firmware/software version information.

        TODO: Replace with the actual command for your device.

        Returns:
            Version information as a string.
        """
        # TODO: Implement device-specific version command
        # return self.send_command("show version")
        return ""

    def get_interfaces(self) -> str:
        """Retrieve network interface information.

        TODO: Replace with the actual command for your device.

        Returns:
            Interface data as a string.
        """
        # TODO: Implement device-specific interface command
        # return self.send_command("show interfaces")
        return ""

    def get_status(self) -> str:
        """Retrieve device status information.

        TODO: Replace with the actual command for your device.

        Returns:
            Status data as a string.
        """
        # TODO: Implement device-specific status command
        # return self.send_command("show status")
        return ""

    def elevate(self, password: str) -> bool:
        """Elevate to a higher privilege level.

        TODO: Replace with the actual privilege escalation
        command for your device.

        Args:
            password: Enable/privilege password.

        Returns:
            True if elevation was successful.
        """
        # TODO: Implement device-specific privilege escalation
        # response = self.send_command("enable")
        # if "Password:" in response:
        #     response = self.send_command(password)
        #     if self.PROMPT_PATTERN.search(response):
        #         self.priv_level = 1
        #         return True
        # return False
        return False

    # ------------------------------------------------------------------
    # Pull workflow
    # ------------------------------------------------------------------

    def pull_and_process(self, dev: DeviceData) -> bool:
        """Pull all data via CLI commands and process into the data model.

        This is the main entry point called by the module's ``_pull_ssh()``
        or ``_pull_telnet()`` methods.

        Returns:
            True if at least one operation was successful.
        """
        self.log.info(f"Starting CLI pull and process for {self.ip}")
        success = False

        # TODO: Implement the CLI pull workflow for your device.
        #
        # Example:
        # config_output = self.get_config()
        # if config_output:
        #     dev.write_file(config_output, "running_config.txt")
        #     parse_config(dev, config_output)  # from mydevice_parse
        #     success = True
        # else:
        #     self.log.warning(f"Failed to get config from {self.ip}")
        #
        # version_output = self.get_version()
        # if version_output:
        #     dev.write_file(version_output, "version.txt")
        #     parse_firmware_info(dev, version_output)
        #     success = True
        # else:
        #     self.log.warning(f"Failed to get version from {self.ip}")
        #
        # iface_output = self.get_interfaces()
        # if iface_output:
        #     dev.write_file(iface_output, "interfaces.txt")
        #     parse_interfaces(dev, iface_output)
        #     success = True
        # else:
        #     self.log.warning(f"Failed to get interfaces from {self.ip}")

        if not success:
            self.log.warning(f"CLI pull and process failed for {self.ip}")

        return success


__all__ = ["MyDeviceCommands"]
