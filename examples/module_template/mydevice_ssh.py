"""
SSH interface for the Vendor DeviceName.

Handles all SSH-based communication with the device, including
authentication, command execution, and file transfer via SFTP.

Authors

- Your Name
"""

from peat import DeviceData, log
from peat.protocols import SSH


class MyDeviceSSH:
    """SSH interface for the Vendor DeviceName.

    Wraps the base SSH protocol class with device-specific
    command sequences and response parsing.

    Example usage:

        >>> ssh = MyDeviceSSH("192.168.1.1", port=22, timeout=5.0)
        >>> ssh.connect(username="admin", password="secret")
        True
        >>> ssh.get_config()
        '...'
        >>> ssh.disconnect()
    """

    def __init__(self, ip: str, port: int = 22, timeout: float = 5.0) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.log = log.bind(classname=self.__class__.__name__)
        self._ssh: SSH | None = None

    @property
    def connected(self) -> bool:
        return self._ssh is not None and self._ssh.connected

    def connect(self, username: str, password: str) -> bool:
        """Establish an SSH connection to the device.

        Args:
            username: SSH username.
            password: SSH password.

        Returns:
            True if the connection was successful.
        """
        try:
            self._ssh = SSH(self.ip, self.port, self.timeout)
            self._ssh.connect(username=username, password=password)
            self.log.debug(f"SSH connected to {self.ip}")
            return True
        except Exception as err:
            self.log.warning(f"SSH connection to {self.ip} failed: {err}")
            self._ssh = None
            return False

    def disconnect(self) -> None:
        """Close the SSH connection."""
        if self._ssh:
            self._ssh.close()
            self._ssh = None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def run_command(self, command: str) -> str:
        """Execute a command on the device and return the output.

        Args:
            command: Shell command to execute.

        Returns:
            Command output as a string, or empty string on failure.
        """
        if not self.connected:
            self.log.warning("Cannot run command: not connected")
            return ""

        try:
            result = self._ssh.exec_command(command)
            return result.strip() if result else ""
        except Exception as err:
            self.log.warning(f"Command '{command}' failed on {self.ip}: {err}")
            return ""

    def get_config(self) -> str:
        """Retrieve the device configuration via SSH.

        TODO: Replace with the actual command(s) for your device.

        Returns:
            Configuration data as a string.
        """
        # TODO: Implement device-specific config retrieval
        # return self.run_command("show running-config")
        return ""

    def get_firmware_version(self) -> str:
        """Retrieve the firmware version via SSH.

        TODO: Replace with the actual command for your device.

        Returns:
            Firmware version string.
        """
        # TODO: Implement device-specific version retrieval
        # return self.run_command("show version")
        return ""

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the device via SFTP.

        Args:
            remote_path: Path to the file on the device.
            local_path: Local path to save the file to.

        Returns:
            True if the download was successful.
        """
        if not self.connected:
            self.log.warning("Cannot download file: not connected")
            return False

        try:
            self._ssh.get_file(remote_path, local_path)
            self.log.debug(f"Downloaded {remote_path} from {self.ip}")
            return True
        except Exception as err:
            self.log.warning(f"Failed to download {remote_path} from {self.ip}: {err}")
            return False

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def pull_and_process(self, dev: DeviceData) -> bool:
        """Pull all data over SSH and process into the data model.

        TODO: Implement the SSH pull workflow for your device.

        Returns:
            True if at least one operation was successful.
        """
        success = False

        # TODO: Implement device-specific SSH pull logic
        # Example:
        # config_output = self.get_config()
        # if config_output:
        #     dev.write_file(config_output, "running_config.txt")
        #     # Parse and populate dev fields
        #     success = True
        #
        # version_output = self.get_firmware_version()
        # if version_output:
        #     dev.firmware.version = version_output
        #     success = True

        return success


__all__ = ["MyDeviceSSH"]
