"""
HTTP interface for the Vendor DeviceName.

Handles all HTTP-based communication with the device, including
authentication, data retrieval, and processing HTTP responses
into the PEAT data model.

Authors

- Your Name
"""

from collections.abc import Callable

from peat import DeviceData, config, log, utils
from peat.data import Interface, Service
from peat.protocols import HTTP


class MyDeviceHTTP(HTTP):
    """HTTP interface for the Vendor DeviceName.

    Extends the base HTTP protocol class with device-specific
    endpoints, authentication, and response processing.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # TODO: Define the HTTP endpoints and their processing methods.
        # Each entry maps a label to a page URL and a processing function.
        self.methods: dict[str, dict[str, str | Callable]] = {
            "device_info": {
                "page": "api/device/info",
                "process_method": self.process_device_info,
            },
            "network_config": {
                "page": "api/network/config",
                "process_method": self.process_network_config,
            },
            # TODO: Add more endpoints as needed
            # "firmware": {
            #     "page": "api/firmware/version",
            #     "process_method": self.process_firmware,
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

                method["process_method"](dev, parsed_data)
                at_least_one_success = True
            except Exception as err:
                self.log.exception(f"'{label}' method failed: {err}")
                failed_methods.append(label)

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
    # endpoint and populates the DeviceData model.
    # ------------------------------------------------------------------

    @staticmethod
    def process_device_info(dev: DeviceData, data: dict) -> None:
        """Process device information response.

        TODO: Map response fields to the DeviceData model.
        Example response:
            {"hostname": "mydevice", "model": "X100", "firmware": "1.2.3"}
        """
        # dev.name = data.get("hostname", "")
        # dev.description.model = data.get("model", "")
        # dev.firmware.version = data.get("firmware", "")
        # dev.serial_number = data.get("serial", "")
        pass

    @staticmethod
    def process_network_config(dev: DeviceData, data: dict) -> None:
        """Process network configuration response.

        TODO: Map response fields to Interface and Service objects.
        Example response:
            {"interfaces": [{"name": "eth0", "ip": "192.168.1.1", "mask": "255.255.255.0"}]}
        """
        # for iface_data in data.get("interfaces", []):
        #     iface = Interface(
        #         name=iface_data.get("name", ""),
        #         type="ethernet",
        #         ip=iface_data.get("ip", ""),
        #         subnet_mask=iface_data.get("mask", ""),
        #         gateway=iface_data.get("gateway", ""),
        #     )
        #     dev.store("interface", iface, lookup=["name", "ip"])
        pass


__all__ = ["MyDeviceHTTP"]
