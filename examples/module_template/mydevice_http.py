"""
HTTP interface for the Vendor DeviceName.

Handles all HTTP-based communication with the device, including
authentication, data retrieval, and processing HTTP responses
into the PEAT data model.

Authors

- Your Name
"""

from collections.abc import Callable

from peat import DeviceData, config
from peat.protocols import HTTP

from .mydevice_parse import parse_interfaces, parse_services, parse_users


class MyDeviceHTTP(HTTP):
    """HTTP interface for the Vendor DeviceName.

    Extends the base HTTP protocol class with device-specific
    endpoints, authentication, and response processing.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Define the HTTP endpoints and their processing methods.
        # Each entry maps a label to a page URL and a processing function.
        # get_and_process_all() iterates through these, fetches each page,
        # and calls the process method to populate the DeviceData model.
        self.methods: dict[str, dict[str, str | Callable]] = {
            "device_info": {
                "page": "api/device/info",
                "process_method": self.process_device_info,
            },
            "network_config": {
                "page": "api/network/config",
                "process_method": self.process_network_config,
            },
            "services": {
                "page": "api/services",
                "process_method": self.process_services,
            },
            "users": {
                "page": "api/users",
                "process_method": self.process_users,
            },
            # TODO: Add more endpoints as needed
            # "firmware": {
            #     "page": "api/firmware/version",
            #     "process_method": self.process_firmware,
            # },
            # "registers": {
            #     "page": "api/registers",
            #     "process_method": self.process_registers,
            # },
        }

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, username: str, password: str) -> bool:
        """Authenticate with the device via HTTP.

        Args:
            username: Login username.
            password: Login password.

        Returns:
            True if authentication was successful.
        """
        if not username:
            self.log.debug("Skipping login: no username configured")
            return True

        self.log.debug(f"Logging in with username '{username}'")

        try:
            # TODO: Implement device-specific authentication.
            # Common patterns include:
            #   - POST to a login endpoint with credentials
            #   - Basic auth via self.session.auth = (username, password)
            #   - Token-based auth via cookies or headers
            #
            # response = self.post(
            #     f"http://{self.ip}:{self.port}/api/login",
            #     data={"username": username, "password": password},
            # )
            #
            # if not response or response.status_code != 200:
            #     self.log.error("Login failed: bad response")
            #     return False
            #
            # token = response.json().get("token")
            # self.session.headers["Authorization"] = f"Bearer {token}"
            return True
        except Exception as err:
            self.log.error(f"Login failed: {err}")
            return False

    # ------------------------------------------------------------------
    # Data retrieval
    # ------------------------------------------------------------------

    def get_and_process_all(self, dev: DeviceData) -> bool:
        """Retrieve all configured endpoints and process responses into the data model.

        Returns:
            True if at least one method was successful.
        """
        at_least_one_success = False
        failed_methods = []

        for label, method in self.methods.items():
            self.log.info(f"Getting '{label}' data from {method['page']}")

            try:
                response = self.get(page=method["page"])

                if not response or not response.text:
                    self.log.warning(f"Failed to get {label} from {method['page']}: no data")
                    failed_methods.append(label)
                    continue

                parsed_data = response.json()

                if config.DEVICE_DIR:
                    dev.write_file(
                        data=parsed_data,
                        filename=f"{label}.json",
                        out_dir=dev.get_sub_dir("http_json_data"),
                    )

                self.log.debug(f"Processing parsed {label} data into the data model...")
                method["process_method"](dev, parsed_data)
                at_least_one_success = True
            except Exception as err:
                self.log.exception(f"'{label}' method failed: {err}")
                failed_methods.append(label)

        self.log.info(
            f"Finished getting and processing data from {dev.ip} "
            f"using {len(self.methods)} methods"
        )

        if failed_methods:
            self.log.warning(
                f"{len(failed_methods)}/{len(self.methods)} methods failed for {dev.ip}: "
                f"{', '.join(failed_methods)}"
            )

        return at_least_one_success

    # ------------------------------------------------------------------
    # Response processing
    #
    # Each method below processes a JSON response from a specific
    # endpoint and populates the DeviceData model. These demonstrate
    # how to map API responses to the PEAT data model fields.
    # ------------------------------------------------------------------

    @staticmethod
    def process_device_info(dev: DeviceData, data: dict) -> None:
        """Process device information response.

        Example response::

            {
                "hostname": "plc-west-01",
                "model": "X100",
                "serialNumber": "SN-2024-001",
                "firmwareVersion": "3.2.1",
                "hardwareRevision": "B",
                "osName": "VxWorks",
                "osVersion": "7.0",
                "uptimeSeconds": 86400,
                "timezone": "America/Denver"
            }
        """
        # Basic identity
        dev.name = data.get("hostname", "")
        dev.hostname = data.get("hostname", "")
        dev.serial_number = data.get("serialNumber", "")

        # Description (what the device is)
        dev.description.model = data.get("model", "")

        # Firmware
        dev.firmware.version = data.get("firmwareVersion", "")

        # Hardware
        dev.hardware.revision = data.get("hardwareRevision", "")
        if data.get("totalMemory"):
            dev.hardware.memory_total = int(data["totalMemory"])

        # Operating system
        dev.os.name = data.get("osName", "")
        dev.os.version = data.get("osVersion", "")
        dev.os.kernel = data.get("kernelVersion", "")

        # Timing
        if data.get("uptimeSeconds"):
            dev.uptime = int(data["uptimeSeconds"])

        # Geolocation
        dev.geo.timezone = data.get("timezone", "")

        # Anything that doesn't fit the standard model goes in extra
        for key in ["customField1", "customField2"]:
            if data.get(key):
                dev.extra[key] = data[key]

    @staticmethod
    def process_network_config(dev: DeviceData, data: dict) -> None:
        """Process network configuration response.

        Delegates to the shared parse_interfaces function to
        populate Interface objects in the data model.

        Example response::

            {
                "interfaces": [
                    {
                        "name": "eth0",
                        "type": "ethernet",
                        "ip": "192.168.1.100",
                        "subnetMask": "255.255.255.0",
                        "gateway": "192.168.1.1",
                        "mac": "00:1A:2B:3C:4D:5E",
                        "enabled": true,
                        "connected": true,
                        "speed": 100000000
                    }
                ]
            }
        """
        parse_interfaces(dev, data.get("interfaces", []))

    @staticmethod
    def process_services(dev: DeviceData, data: dict) -> None:
        """Process running services response.

        Delegates to the shared parse_services function.

        Example response::

            {
                "services": [
                    {
                        "protocol": "modbus_tcp",
                        "port": 502,
                        "transport": "tcp",
                        "enabled": true,
                        "protocolId": "1"
                    }
                ]
            }
        """
        parse_services(dev, data.get("services", []))

    @staticmethod
    def process_users(dev: DeviceData, data: dict) -> None:
        """Process user accounts response.

        Delegates to the shared parse_users function.

        Example response::

            {
                "users": [
                    {
                        "username": "admin",
                        "fullName": "Administrator",
                        "roles": ["admin"],
                        "permissions": ["read", "write", "execute"]
                    }
                ]
            }
        """
        parse_users(dev, data.get("users", []))


__all__ = ["MyDeviceHTTP"]
