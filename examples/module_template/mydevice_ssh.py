"""
SSH transport for the Vendor DeviceName.

Implements the transport layer for SSH communication. Device-specific
commands are inherited from MyDeviceCommands, keeping the command
interface consistent with the Telnet transport.

Authors

- Your Name
"""

from peat.protocols import SSH

from .mydevice_commands import MyDeviceCommands


class MyDeviceSSH(MyDeviceCommands):
    """SSH transport for the Vendor DeviceName.

    Inherits device commands from MyDeviceCommands and implements
    the SSH-specific transport (connect, send, disconnect, SFTP).

    Example usage:

        >>> ssh = MyDeviceSSH("192.168.1.1", port=22, timeout=5.0)
        >>> ssh.connect(username="admin", password="secret")
        True
        >>> ssh.get_config()  # inherited from MyDeviceCommands
        '...'
        >>> ssh.disconnect()
    """

    def __init__(self, ip: str, port: int = 22, timeout: float = 5.0) -> None:
        super().__init__(ip, timeout)
        self.port = port
        self._ssh: SSH | None = None

    @property
    def connected(self) -> bool:
        return self._ssh is not None and self._ssh.connected

    # ------------------------------------------------------------------
    # Transport implementation
    # ------------------------------------------------------------------

    def connect(self, username: str, password: str) -> bool:
        """Establish an SSH connection to the device."""
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

    def send_command(self, command: str) -> str:
        """Send a command over SSH and return the output."""
        if not self.connected:
            self.log.warning("Cannot send command: not connected")
            return ""

        try:
            result = self._ssh.exec_command(command)
            return result.strip() if result else ""
        except Exception as err:
            self.log.warning(f"Command '{command}' failed on {self.ip}: {err}")
            return ""

    # ------------------------------------------------------------------
    # SSH-specific operations (SFTP, etc.)
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


__all__ = ["MyDeviceSSH"]
