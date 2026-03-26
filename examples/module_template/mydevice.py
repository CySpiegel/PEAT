"""
PEAT module for the Vendor DeviceName.

This is the main module file. It defines the device class, its attributes,
and orchestrates identification and pull operations by delegating to
protocol-specific helpers (HTTP, SSH, Telnet, etc.).

To use as an external module:

    peat scan -d MyDevice -I mydevice.py -i <target_ip>
    peat pull -d MyDevice -I mydevice.py -i <target_ip>
    peat parse -d MyDevice -I mydevice.py -- <input_file>

Authors

- Your Name
"""

from pathlib import Path

from peat import DeviceData, DeviceModule, IPMethod, datastore

from .mydevice_http import MyDeviceHTTP
from .mydevice_parse import parse_config

# Uncomment as needed:
# from .mydevice_ssh import MyDeviceSSH
# from .mydevice_telnet import MyDeviceTelnet
# from .mydevice_serial import MyDeviceSerial


class MyDevice(DeviceModule):
    """PEAT module for the Vendor DeviceName.

    Listening services

    - HTTP (TCP 80)

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

    # TODO: Module-specific configuration options
    default_options: dict = {
        "mydevice": {
            "pull_methods": ["http"],
        },
        "http": {
            "user": "",
            "pass": "",
        },
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
        except Exception as err:
            cls.log.warning(f"Failed to verify {dev.ip} via HTTP: {err}")

        return False

    # ------------------------------------------------------------------
    # Pull
    # ------------------------------------------------------------------

    @classmethod
    def _pull(cls, dev: DeviceData) -> bool:
        """Orchestrate pulling device data across configured protocols."""
        pull_methods = dev.options["mydevice"]["pull_methods"]
        success = False

        if "http" in pull_methods:
            if dev.service_status({"protocol": "http"}) == "closed":
                cls.log.warning(f"Failed to pull HTTP on {dev.ip}: port is closed")
            elif not dev._is_verified and not cls._verify_http(dev):
                cls.log.warning(f"Failed to pull HTTP on {dev.ip}: verification failed")
            elif cls._pull_http(dev):
                success = True

        # TODO: Uncomment and implement additional protocols as needed
        # if "ssh" in pull_methods:
        #     if cls._pull_ssh(dev):
        #         success = True

        # if "telnet" in pull_methods:
        #     if cls._pull_telnet(dev):
        #         success = True

        # if "serial" in pull_methods:
        #     if cls._pull_serial(dev):
        #         success = True

        return success

    @classmethod
    def _pull_http(cls, dev: DeviceData) -> bool:
        """Pull device data over HTTP using the MyDeviceHTTP helper."""
        cls.log.info(f"Pulling HTTP from {dev.ip}")

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
            cls.log.error(f"Failed to pull from {dev.ip}: HTTP login failed")
            return False

        dev.related.user.add(dev.options["http"]["user"])

        if not http.get_and_process_all(dev):
            return False

        cls.log.info(f"Finished pulling HTTP from {dev.ip}")
        return True

    # @classmethod
    # def _pull_ssh(cls, dev: DeviceData) -> bool:
    #     """Pull device data over SSH using the MyDeviceSSH helper."""
    #     cls.log.info(f"Pulling SSH from {dev.ip}")
    #     # TODO: Implement SSH pull logic
    #     return False

    # @classmethod
    # def _pull_telnet(cls, dev: DeviceData) -> bool:
    #     """Pull device data over Telnet using the MyDeviceTelnet helper."""
    #     cls.log.info(f"Pulling Telnet from {dev.ip}")
    #     # TODO: Implement Telnet pull logic
    #     return False

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
        raw_data = file.read_text(encoding="utf-8")

        if not dev:
            # TODO: Extract the device IP from the parsed data
            dev = datastore.get("0.0.0.0", "ip")

        # Delegate to the parse module
        parse_config(dev, raw_data)

        return dev


# ------------------------------------------------------------------
# Identification method registration
# ------------------------------------------------------------------

MyDevice.ip_methods = [
    IPMethod(
        # TODO: Set a descriptive name for this identification method
        name="mydevice_scrape_http",
        description=str(MyDevice._verify_http.__doc__).strip(),
        type="unicast_ip",
        identify_function=MyDevice._verify_http,
        # TODO: Set reliability (1-10, where 6+ is reliable)
        reliability=7,
        protocol="http",
        transport="tcp",
        # TODO: Set the default port for this protocol
        default_port=80,
    ),
]

# Uncomment if the device supports serial communication:
# MyDevice.serial_methods = []


__all__ = ["MyDevice"]
