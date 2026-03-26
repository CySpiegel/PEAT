"""
PEAT module for the Vendor DeviceName.

This is the main module file. It defines the device class, its attributes,
and orchestrates identification and pull operations by delegating to
protocol-specific helpers (HTTP, SSH, Telnet, etc.).

SSH/Telnet sessions are cached in dev._cache during verification so that
the same authenticated connection is reused for pulling, avoiding a second
login round-trip. This follows the same pattern as the Sage module.

To use as an external module:

    peat scan -d MyDevice -I mydevice.py -i <target_ip>
    peat pull -d MyDevice -I mydevice.py -i <target_ip>
    peat parse -d MyDevice -I mydevice.py -- <input_file>

Authors

- Your Name
"""

from pathlib import Path
from typing import Literal

from peat import DeviceData, DeviceModule, IPMethod, datastore, exit_handler

from .mydevice_http import MyDeviceHTTP
from .mydevice_parse import parse_config
from .mydevice_ssh import MyDeviceSSH
from .mydevice_telnet import MyDeviceTelnet

# Uncomment as needed:
# from .mydevice_serial import MyDeviceSerial


class MyDevice(DeviceModule):
    """PEAT module for the Vendor DeviceName.

    Listening services

    - HTTP (TCP 80)
    - SSH (TCP 22)
    - Telnet (TCP 23)

    Data collected

    - Configuration
    - Firmware version
    - Network interfaces

    Authors

    - Your Name
    """

    # TODO: Set the type of device (e.g. "PLC", "Relay", "RTU", "Gateway", "DGA")
    device_type = ""

    # TODO: Set vendor identifiers
    vendor_id = ""  # Short form (e.g. "SEL", "Rockwell")
    vendor_name = ""  # Long form (e.g. "Schweitzer Engineering Laboratories")

    # TODO: Set brand and model (leave empty if not applicable)
    brand = ""
    model = ""

    # TODO: List models this module supports (optional)
    supported_models: list[str] = []

    # TODO: File patterns this module can parse (must start with *)
    # Examples: ["*.cfg", "*_config.xml", "*.rdb"]
    filename_patterns: list[str] = []

    # TODO: Alternative names for the -d flag (optional)
    module_aliases: list[str] = []

    # TODO: Fields to auto-populate on devices (optional)
    # Example: {"os.name": "Linux", "os.vendor.id": "Vendor"}
    annotate_fields: dict = {}

    # Module-specific configuration options.
    #
    # These get deep-merged with PEAT's global defaults (peat/data/default_options.py).
    # Protocol keys like "http", "ssh", "telnet" already have port and timeout
    # defined globally -- only specify fields you want to ADD or OVERRIDE.
    #
    # Note: "ssh" already includes user/pass/key_filename/passphrase/look_for_keys
    # in the global defaults, so you only need to redeclare them here if you want
    # to set non-empty default values (e.g. a known default password).
    #
    # Access at runtime via: dev.options["mydevice"]["pull_methods"]
    #                        dev.options["http"]["port"]  (from global defaults)
    #                        dev.options["ssh"]["user"]   (from global defaults)
    default_options: dict = {
        "mydevice": {
            "pull_methods": ["http", "ssh"],
        },
        # Add user/pass to http and telnet (not in global defaults for these)
        "http": {
            "user": "",
            "pass": "",
        },
        "telnet": {
            "user": "",
            "pass": "",
        },
        # ssh already has user/pass in global defaults -- only override if
        # your device has a known default credential:
        # "ssh": {
        #     "user": "admin",
        #     "pass": "default_password",
        # },
    }

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    @classmethod
    def _verify_http(cls, dev: DeviceData) -> bool:
        """Verify the device via HTTP by checking for device-specific markers."""
        cls.log.debug(f"Checking {dev.ip} via HTTP")

        try:
            with MyDeviceHTTP(
                ip=dev.ip,
                port=dev.options["http"]["port"],
                timeout=dev.options["http"]["timeout"],
                dev=dev,
            ) as http:
                response = http.get("/")

                if not response:
                    cls.log.debug(f"Failed to verify {dev.ip} via HTTP: no response")
                    return False

                page = response.text

                # TODO: Replace with a check specific to your device
                if "DEVICE_IDENTIFIER" in page:
                    cls.log.debug(f"Successfully verified {dev.ip} via HTTP")
                    return True

                cls.log.debug(f"Failed to verify {dev.ip} via HTTP: identifier not found")
        except Exception:
            cls.log.exception(f"Failed to verify {dev.ip} via HTTP")

        return False

    @classmethod
    def _verify_cli(
        cls, dev: DeviceData, protocol: Literal["ssh", "telnet"] = "ssh"
    ) -> bool:
        """Verify the device via SSH or Telnet and cache the session.

        The connection is intentionally NOT wrapped in a "with" statement
        so that the session persists in dev._cache for reuse during pull.
        The exit_handler ensures clean disconnection when PEAT exits.
        """
        cls.log.debug(f"Checking {dev.ip} via {protocol.upper()}")
        port = dev.options[protocol]["port"]
        timeout = dev.options[protocol]["timeout"]

        # Create the appropriate transport
        if protocol == "ssh":
            conn = MyDeviceSSH(dev.ip, port, timeout)
        else:
            conn = MyDeviceTelnet(dev.ip, port, timeout)

        try:
            username = dev.options[protocol]["user"]
            password = dev.options[protocol]["pass"]

            if not conn.connect(username, password):
                cls.log.debug(
                    f"Failed to verify {dev.ip} via {protocol.upper()}: login failed"
                )
                conn.disconnect()
                return False

            dev.related.user.add(username)

            # TODO: Run a command to fingerprint the device.
            # Check for a device-specific string in the output to
            # confirm this is actually your device type.
            #
            # version_output = conn.get_version()
            # if "MyDevice" not in version_output:
            #     cls.log.debug(f"Not a MyDevice: {dev.ip}")
            #     conn.disconnect()
            #     return False

            # Cache the session for reuse in _pull_cli() and register
            # the disconnect method with the exit handler so the
            # connection is cleaned up when PEAT exits.
            dev._cache[f"mydevice_{protocol}_session"] = conn
            exit_handler.register(conn.disconnect, "CONNECTION")
            dev._cache[f"mydevice_{protocol}_fingerprinted"] = True

            cls.log.debug(f"Successfully verified {dev.ip} via {protocol.upper()}")
            return True
        except Exception:
            cls.log.exception(
                f"Failed to verify {dev.ip} via {protocol.upper()}"
            )
            conn.disconnect()
            return False

    @classmethod
    def _verify_ssh(cls, dev: DeviceData) -> bool:
        """Verify the device via SSH."""
        return cls._verify_cli(dev, protocol="ssh")

    @classmethod
    def _verify_telnet(cls, dev: DeviceData) -> bool:
        """Verify the device via Telnet."""
        return cls._verify_cli(dev, protocol="telnet")

    # ------------------------------------------------------------------
    # Pull
    # ------------------------------------------------------------------

    @classmethod
    def _pull(cls, dev: DeviceData) -> bool:
        """Orchestrate pulling device data across configured protocols."""
        pull_methods = dev.options["mydevice"]["pull_methods"]
        cls.log.info(f"Pulling from {dev.ip} (methods: {', '.join(pull_methods)})")
        success = False

        if "http" in pull_methods:
            if dev.service_status({"protocol": "http"}) == "closed":
                cls.log.warning(f"Failed to pull HTTP on {dev.ip}: port is closed")
            elif not dev._is_verified and not cls._verify_http(dev):
                cls.log.warning(f"Failed to pull HTTP on {dev.ip}: verification failed")
            elif cls._pull_http(dev):
                success = True

        if "ssh" in pull_methods:
            if cls._pull_cli(dev, protocol="ssh"):
                success = True

        if "telnet" in pull_methods:
            if cls._pull_cli(dev, protocol="telnet"):
                success = True

        # if "serial" in pull_methods:
        #     if cls._pull_serial(dev):
        #         success = True

        return success

    @classmethod
    def _pull_http(cls, dev: DeviceData) -> bool:
        """Pull device data over HTTP using the MyDeviceHTTP helper."""
        cls.log.info(f"Pulling HTTP from {dev.ip}")

        try:
            if not dev._cache.get("mydevice_http_session"):
                dev._cache["mydevice_http_session"] = MyDeviceHTTP(
                    ip=dev.ip,
                    port=dev.options["http"]["port"],
                    timeout=dev.options["http"]["timeout"],
                    dev=dev,
                )
            http = dev._cache["mydevice_http_session"]

            if not http.login(
                username=dev.options["http"]["user"],
                password=dev.options["http"]["pass"],
            ):
                cls.log.error(
                    f"Failed to pull from {dev.ip}: HTTP login failed"
                )
                return False

            dev.related.user.add(dev.options["http"]["user"])

            if not http.get_and_process_all(dev):
                cls.log.error(
                    f"Failed to pull from {dev.ip}: all HTTP methods failed"
                )
                return False

            cls.log.info(f"Finished pulling HTTP from {dev.ip}")
            return True
        except Exception:
            cls.log.exception(f"Failed to pull from {dev.ip} via HTTP")
            return False

    @classmethod
    def _pull_cli(
        cls, dev: DeviceData, protocol: Literal["ssh", "telnet"] = "ssh"
    ) -> bool:
        """Pull device data via SSH or Telnet, reusing a cached session.

        This method reuses the connection established during verification
        (_verify_cli). If no cached session exists (e.g. pull was called
        without scan), a new session is created and cached.
        """
        proto_upper = protocol.upper()
        port = dev.options[protocol]["port"]
        timeout = dev.options[protocol]["timeout"]

        cls.log.info(f"Pulling from {dev.ip}:{port} via {proto_upper}")

        try:
            # Reuse the session cached during _verify_cli(), or create
            # a new one if pull is called without a prior scan.
            conn = dev._cache.get(f"mydevice_{protocol}_session")
            if not conn:
                cls.log.debug(
                    f"No cached {proto_upper} session for {dev.ip}, "
                    f"creating new connection"
                )
                if protocol == "ssh":
                    conn = MyDeviceSSH(dev.ip, port, timeout)
                else:
                    conn = MyDeviceTelnet(dev.ip, port, timeout)

                # Cache and register for cleanup
                dev._cache[f"mydevice_{protocol}_session"] = conn
                exit_handler.register(conn.disconnect, "CONNECTION")

            # Log in only if not already connected (session from verify
            # will already be authenticated)
            if not conn.connected:
                username = dev.options[protocol]["user"]
                password = dev.options[protocol]["pass"]

                if not conn.connect(username, password):
                    cls.log.error(
                        f"Failed to pull from {dev.ip} via "
                        f"{proto_upper}: login failed"
                    )
                    return False
                dev.related.user.add(username)

            # Delegate to the shared pull_and_process() method defined
            # in MyDeviceCommands (inherited by both SSH and Telnet)
            if not conn.pull_and_process(dev):
                cls.log.warning(f"{proto_upper} pull failed for {dev.ip}")
                return False

            cls.log.info(
                f"Finished pulling from {dev.ip} via {proto_upper}"
            )
            return True
        except Exception:
            cls.log.exception(
                f"Failed to pull from {dev.ip} via {proto_upper}"
            )
            return False

    # @classmethod
    # def _pull_serial(cls, dev: DeviceData) -> bool:
    #     """Pull device data over serial using the MyDeviceSerial helper."""
    #     cls.log.info(f"Pulling serial from {dev.serial_port}")
    #     # TODO: Implement serial pull logic
    #     return False

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    @classmethod
    def _parse(cls, file: Path, dev: DeviceData | None = None) -> DeviceData | None:
        """Parse device data from a collected file.

        Delegates the actual parsing logic to mydevice_parse.
        """
        try:
            raw_data = file.read_text(encoding="utf-8")
        except Exception:
            cls.log.exception(f"Failed to read file: {file}")
            return None

        if not dev:
            # TODO: Extract the device IP from the parsed data
            dev = datastore.get("0.0.0.0", "ip")

        try:
            parse_config(dev, raw_data)
        except Exception:
            cls.log.exception(f"Failed to parse file: {file}")
            return None

        return dev


# ------------------------------------------------------------------
# Identification method registration
# ------------------------------------------------------------------

MyDevice.ip_methods = [
    IPMethod(
        name="mydevice_scrape_http",
        description=str(MyDevice._verify_http.__doc__).strip(),
        type="unicast_ip",
        identify_function=MyDevice._verify_http,
        reliability=7,
        protocol="http",
        transport="tcp",
        default_port=80,
    ),
    IPMethod(
        name="mydevice_verify_ssh",
        description=str(MyDevice._verify_ssh.__doc__).strip(),
        type="unicast_ip",
        identify_function=MyDevice._verify_ssh,
        reliability=8,
        protocol="ssh",
        transport="tcp",
        default_port=22,
    ),
    IPMethod(
        name="mydevice_verify_telnet",
        description=str(MyDevice._verify_telnet.__doc__).strip(),
        type="unicast_ip",
        identify_function=MyDevice._verify_telnet,
        reliability=6,
        protocol="telnet",
        transport="tcp",
        default_port=23,
    ),
]

# Uncomment if the device supports serial communication:
# MyDevice.serial_methods = []


__all__ = ["MyDevice"]
