"""
Parsing logic for the Vendor DeviceName.

Contains functions for parsing device-specific file formats and
command outputs into the PEAT data model. Keep parsing logic here
rather than in the main module or protocol files.

Authors

- Your Name
"""

from typing import Any

from peat import DeviceData, Interface, Service, log, utils


def parse_config(dev: DeviceData, raw_data: str) -> None:
    """Parse device configuration data into the data model.

    TODO: Implement parsing for your device's configuration format.
    This could be JSON, XML, CSV, proprietary text, or binary.

    Args:
        dev: DeviceData object to populate.
        raw_data: Raw configuration data as a string.
    """
    # TODO: Parse the raw data and populate the data model.
    #
    # Example for JSON:
    #   import json
    #   data = json.loads(raw_data)
    #   dev.name = data.get("hostname", "")
    #   dev.firmware.version = data.get("firmware", "")
    #
    # Example for key-value text:
    #   for line in raw_data.splitlines():
    #       key, _, value = line.partition("=")
    #       if key.strip() == "hostname":
    #           dev.name = value.strip()
    pass


def parse_interfaces(dev: DeviceData, raw_data: str) -> None:
    """Parse network interface data into the data model.

    TODO: Implement parsing for your device's network output.

    Args:
        dev: DeviceData object to populate.
        raw_data: Raw interface data as a string.
    """
    # TODO: Parse interface data
    #
    # Example:
    #   for entry in parse_interface_table(raw_data):
    #       iface = Interface(
    #           name=entry["name"],
    #           type="ethernet",
    #           ip=entry["ip"],
    #           subnet_mask=entry["mask"],
    #           gateway=entry.get("gateway", ""),
    #       )
    #       dev.store("interface", iface, lookup=["name", "ip"])
    pass


def parse_services(dev: DeviceData, raw_data: str) -> None:
    """Parse network service data into the data model.

    TODO: Implement parsing for your device's service/port information.

    Args:
        dev: DeviceData object to populate.
        raw_data: Raw service data as a string.
    """
    # TODO: Parse service data
    #
    # Example:
    #   for entry in parse_service_list(raw_data):
    #       svc = Service(
    #           protocol=entry["protocol"],
    #           port=int(entry["port"]),
    #           enabled=entry["status"] == "active",
    #           transport="tcp",
    #       )
    #       dev.store("service", svc, interface_lookup={"ip": dev.ip})
    pass


def parse_firmware_info(dev: DeviceData, raw_data: str) -> None:
    """Parse firmware and version data into the data model.

    TODO: Implement parsing for your device's version output.

    Args:
        dev: DeviceData object to populate.
        raw_data: Raw firmware/version data as a string.
    """
    # TODO: Parse firmware data
    #
    # Example:
    #   match = re.search(r"Version:\s+(\S+)", raw_data)
    #   if match:
    #       dev.firmware.version = match.group(1)
    pass


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

# TODO: Add helper functions for parsing device-specific formats.
#
# Keep parsing utilities as module-level functions rather than
# class methods. This makes them easy to test independently and
# reuse across protocols (e.g. both HTTP and SSH may return the
# same data format).
#
# Example:
#
# def split_config_sections(raw: str) -> dict[str, str]:
#     """Split a raw config into named sections."""
#     sections = {}
#     current = ""
#     for line in raw.splitlines():
#         if line.startswith("[") and line.endswith("]"):
#             current = line[1:-1]
#             sections[current] = ""
#         elif current:
#             sections[current] += line + "\n"
#     return sections
