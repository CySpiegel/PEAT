"""
Parsing logic for the Vendor DeviceName.

Contains functions for parsing device-specific file formats and
command outputs into the PEAT data model. Keep parsing logic here
rather than in the main module or protocol files.

Each function takes a DeviceData object and raw data, then populates
the appropriate fields in the data model. Functions are kept as
standalone module-level functions so they can be reused across
protocols (HTTP, SSH, Telnet) and tested independently.

Refer to the PEAT data model documentation for all available fields:
https://sandialabs.github.io/PEAT/data_model.html

Authors

- Your Name
"""

import json
import re

from peat import DeviceData, Event, Interface, Register, Service, utils
from peat.data.models import User


def parse_config(dev: DeviceData, raw_data: str) -> None:
    """Parse device configuration data into the data model.

    This is the main parse entry point. It reads a JSON configuration
    export and populates the DeviceData object with all available
    device information.

    Args:
        dev: DeviceData object to populate.
        raw_data: Raw configuration data as a JSON string.
    """
    data = json.loads(raw_data)

    # ------------------------------------------------------------------
    # Basic device identity
    # ------------------------------------------------------------------

    # dev.name: primary reference name for the device
    dev.name = data.get("hostname", "")

    # dev.hostname: resolved hostname (often same as name)
    dev.hostname = data.get("hostname", "")

    # dev.serial_number: manufacturer-assigned serial
    dev.serial_number = data.get("serialNumber", "")

    # dev.architecture: CPU architecture (x86, ARM, MIPS, etc.)
    dev.architecture = data.get("arch", "")

    # dev.status: device-specific operational status
    dev.status = data.get("status", "")

    # dev.run_mode: operational mode (e.g. "RUN", "PROG", "REMOTE")
    dev.run_mode = data.get("runMode", "")

    # dev.slot: position in a rack or chassis
    dev.slot = data.get("slot", "")

    # dev.label: user-assigned label or asset tag
    dev.label = data.get("assetTag", "")

    # dev.comment: arbitrary notes about the device
    dev.comment = data.get("notes", "")

    # ------------------------------------------------------------------
    # Description (vendor, brand, model identification)
    #
    # These fields identify what the device is. Most are auto-populated
    # by DeviceModule.update_dev(), but can also be set from parsed data.
    # ------------------------------------------------------------------

    # dev.description.vendor.id: short vendor name ("SEL", "Rockwell")
    dev.description.vendor.id = data.get("vendorId", "")

    # dev.description.vendor.name: full vendor name
    dev.description.vendor.name = data.get("vendorName", "")

    # dev.description.brand: product line brand
    dev.description.brand = data.get("brand", "")

    # dev.description.model: specific model number/name
    dev.description.model = data.get("model", "")

    # dev.description.description: free-form device description
    dev.description.description = data.get("description", "")

    # dev.description.contact_info: SNMP-style contact info
    dev.description.contact_info = data.get("contact", "")

    # ------------------------------------------------------------------
    # Firmware
    # ------------------------------------------------------------------

    # dev.firmware.version: primary firmware version string
    dev.firmware.version = data.get("firmwareVersion", "")

    # dev.firmware.revision: firmware revision or build number
    dev.firmware.revision = data.get("firmwareRevision", "")

    # dev.firmware.id: unique firmware identifier
    dev.firmware.id = data.get("firmwareId", "")

    # dev.firmware.hash: checksums for firmware integrity verification
    if data.get("firmwareMd5"):
        dev.firmware.hash.md5 = data["firmwareMd5"]
    if data.get("firmwareSha256"):
        dev.firmware.hash.sha256 = data["firmwareSha256"]

    # dev.firmware.release_date: when the firmware was released
    if data.get("firmwareReleaseDate"):
        dev.firmware.release_date = utils.parse_date(data["firmwareReleaseDate"])

    # dev.boot_firmware: separate boot/BIOS firmware (same fields as firmware)
    if data.get("bootVersion"):
        dev.boot_firmware.version = data["bootVersion"]

    # ------------------------------------------------------------------
    # Operating system
    # ------------------------------------------------------------------

    # dev.os.name: OS name (e.g. "Linux", "VxWorks", "Windows CE")
    dev.os.name = data.get("osName", "")

    # dev.os.version: OS version string
    dev.os.version = data.get("osVersion", "")

    # dev.os.family: OS family (e.g. "linux", "windows", "rtos")
    dev.os.family = data.get("osFamily", "")

    # dev.os.kernel: kernel version string
    dev.os.kernel = data.get("kernelVersion", "")

    # dev.os.full: complete OS description
    dev.os.full = data.get("osFullName", "")

    # dev.os.vendor: OS vendor (same Vendor model as device vendor)
    if data.get("osVendor"):
        dev.os.vendor.name = data["osVendor"]

    # ------------------------------------------------------------------
    # Hardware
    # ------------------------------------------------------------------

    # dev.hardware.id: hardware identifier or catalog number
    dev.hardware.id = data.get("hardwareId", "")

    # dev.hardware.revision: hardware revision
    dev.hardware.revision = data.get("hardwareRevision", "")

    # dev.hardware.memory_total: total RAM in bytes
    if data.get("totalMemory"):
        dev.hardware.memory_total = int(data["totalMemory"])

    # dev.hardware.memory_available: available RAM in bytes
    if data.get("availableMemory"):
        dev.hardware.memory_available = int(data["availableMemory"])

    # dev.hardware.storage_total: total storage in bytes
    if data.get("totalStorage"):
        dev.hardware.storage_total = int(data["totalStorage"])

    # dev.hardware.storage_available: free storage in bytes
    if data.get("storageAvailable"):
        dev.hardware.storage_available = int(data["storageAvailable"])

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    # dev.start_time: UTC timestamp of last power-on or boot
    if data.get("bootTime"):
        dev.start_time = utils.parse_date(data["bootTime"])

    # dev.uptime: how long the device has been running (seconds)
    if data.get("uptimeSeconds"):
        dev.uptime = int(data["uptimeSeconds"])

    # ------------------------------------------------------------------
    # Geolocation
    # ------------------------------------------------------------------

    # dev.geo.name: site or facility name
    dev.geo.name = data.get("siteName", "")

    # dev.geo.timezone: IANA timezone (e.g. "America/Denver")
    dev.geo.timezone = data.get("timezone", "")

    # dev.geo.city_name: city name
    dev.geo.city_name = data.get("city", "")

    # dev.geo.country_name: country name
    dev.geo.country_name = data.get("country", "")

    # dev.geo.location: lat/lon coordinates
    if data.get("latitude") and data.get("longitude"):
        dev.geo.location.lat = float(data["latitude"])
        dev.geo.location.lon = float(data["longitude"])

    # ------------------------------------------------------------------
    # Network interfaces
    # ------------------------------------------------------------------

    parse_interfaces(dev, data.get("interfaces", []))

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    parse_services(dev, data.get("services", []))

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    parse_users(dev, data.get("users", []))

    # ------------------------------------------------------------------
    # Related information
    #
    # The "related" object is a set-based collection of associated
    # identifiers. Use .add() to insert, and PEAT handles deduplication.
    # ------------------------------------------------------------------

    for ip in data.get("relatedIps", []):
        dev.related.ip.add(ip)

    for host in data.get("relatedHosts", []):
        dev.related.hosts.add(host)

    # ------------------------------------------------------------------
    # Extra / catch-all
    #
    # dev.extra is a dict for arbitrary data that doesn't fit the
    # standard model. It gets flattened on export to Elasticsearch.
    # ------------------------------------------------------------------

    if data.get("customFields"):
        dev.extra.update(data["customFields"])


def parse_interfaces(dev: DeviceData, interfaces: list[dict]) -> None:
    """Parse network interface data into the data model.

    Creates Interface objects and stores them using dev.store(), which
    handles deduplication via the lookup parameter. Services found on
    interfaces are associated using interface_lookup.

    Args:
        dev: DeviceData object to populate.
        interfaces: List of interface dicts from parsed data.
    """
    for iface_data in interfaces:
        # Create an Interface object with available fields
        iface = Interface(
            # name: interface identifier (eth0, GigabitEthernet0/1, etc.)
            name=iface_data.get("name", ""),
            # type: interface type (ethernet, wifi, serial, loopback, etc.)
            type=iface_data.get("type", "ethernet"),
            # ip: IPv4 address assigned to this interface
            ip=iface_data.get("ip", ""),
            # subnet_mask: network mask (255.255.255.0)
            subnet_mask=iface_data.get("subnetMask", ""),
            # gateway: default gateway for this interface
            gateway=iface_data.get("gateway", ""),
            # mac: MAC address (validated and normalized by PEAT)
            mac=iface_data.get("mac", ""),
            # enabled: whether the interface is administratively active
            enabled=iface_data.get("enabled", False),
            # connected: whether the link is up / cable is connected
            connected=iface_data.get("connected", False),
            # speed: link speed in bits per second
            speed=iface_data.get("speed"),
            # mtu: maximum transmission unit
            mtu=iface_data.get("mtu"),
            # duplex: "half", "full", or "auto"
            duplex=iface_data.get("duplex", ""),
        )

        # description: nested Description object on the interface
        if iface_data.get("description"):
            iface.description.description = iface_data["description"]

        # Serial interface fields (for RS-232/485 ports)
        if iface_data.get("type") == "serial":
            iface.serial_port = iface_data.get("serialPort", "")
            iface.baudrate = iface_data.get("baudrate")
            iface.data_bits = iface_data.get("dataBits")
            iface.parity = iface_data.get("parity", "")
            iface.stop_bits = iface_data.get("stopBits")
            iface.flow_control = iface_data.get("flowControl", "")

        # Store into the data model. The lookup parameter tells PEAT
        # which fields to use for deduplication -- if an interface with
        # matching name and ip already exists, it will be merged.
        dev.store("interface", iface, lookup=["name", "ip"])

        # Track MACs and IPs in related sets for cross-referencing
        if iface.mac:
            dev.related.mac.add(iface.mac)
        if iface.ip:
            dev.related.ip.add(iface.ip)


def parse_services(dev: DeviceData, services: list[dict]) -> None:
    """Parse network service data into the data model.

    Services represent listening network services on the device
    (HTTP, SSH, Modbus TCP, DNP3, etc.). They can optionally be
    associated with a specific interface using interface_lookup.

    Args:
        dev: DeviceData object to populate.
        services: List of service dicts from parsed data.
    """
    for svc_data in services:
        svc = Service(
            # protocol: application protocol name (http, ssh, modbus_tcp, dnp3)
            protocol=svc_data.get("protocol", ""),
            # port: listening port number (1-65535)
            port=int(svc_data["port"]) if svc_data.get("port") else None,
            # transport: transport protocol (tcp, udp, serial)
            transport=svc_data.get("transport", "tcp"),
            # enabled: whether the service is active
            enabled=svc_data.get("enabled", True),
            # status: "open", "closed", or "verified"
            status=svc_data.get("status", ""),
            # protocol_id: protocol-specific identifier (e.g. Modbus slave address)
            protocol_id=svc_data.get("protocolId", ""),
        )

        # Track in related sets
        if svc.port:
            dev.related.ports.add(svc.port)
        if svc.protocol:
            dev.related.protocols.add(svc.protocol)

        # Associate the service with a specific interface using
        # interface_lookup. This finds the matching interface and
        # nests the service under it.
        interface_ip = svc_data.get("listenAddress", dev.ip)
        dev.store("service", svc, interface_lookup={"ip": interface_ip})


def parse_users(dev: DeviceData, users: list[dict]) -> None:
    """Parse user account data into the data model.

    Args:
        dev: DeviceData object to populate.
        users: List of user dicts from parsed data.
    """
    for user_data in users:
        user = User(
            # name: login username
            name=user_data.get("username", ""),
            # full_name: display name
            full_name=user_data.get("fullName", ""),
            # id: user ID string
            id=user_data.get("id", ""),
            # description: account description or comment
            description=user_data.get("description", ""),
        )

        # roles: set of role names assigned to the user
        for role in user_data.get("roles", []):
            user.roles.add(role)
            dev.related.roles.add(role)

        # permissions: set of permission strings
        for perm in user_data.get("permissions", []):
            user.permissions.add(perm)

        # Track in related.user for cross-referencing
        dev.related.user.add(user.name)

        # Store with deduplication on username
        dev.store("users", user, lookup="name")


def parse_registers(dev: DeviceData, registers: list[dict]) -> None:
    """Parse protocol register/data point information.

    Registers represent addressable data points for industrial
    protocols like Modbus and DNP3.

    Args:
        dev: DeviceData object to populate.
        registers: List of register dicts from parsed data.
    """
    for reg_data in registers:
        reg = Register(
            # protocol: which protocol this register belongs to (modbus, dnp3)
            protocol=reg_data.get("protocol", ""),
            # address: register address (e.g. "40001" for Modbus)
            address=reg_data.get("address", ""),
            # tag: human-readable tag name
            tag=reg_data.get("tag", ""),
            # description: what this register represents
            description=reg_data.get("description", ""),
            # data_type: value type (int16, float32, boolean, etc.)
            data_type=reg_data.get("dataType", ""),
            # measurement_type: what's being measured (analog, digital, etc.)
            measurement_type=reg_data.get("measurementType", ""),
            # read_write: access mode ("read", "write", "read_write")
            read_write=reg_data.get("readWrite", ""),
            # enabled: whether the register is active
            enabled=reg_data.get("enabled", True),
        )

        # extra: catch-all for additional register metadata
        if reg_data.get("scaling"):
            reg.extra["scaling"] = float(reg_data["scaling"])
        if reg_data.get("offset"):
            reg.extra["offset"] = reg_data["offset"]
        if reg_data.get("units"):
            reg.extra["units"] = reg_data["units"]

        dev.store(
            "registers",
            reg,
            lookup={"protocol": reg.protocol, "address": reg.address},
        )


def parse_events(dev: DeviceData, events: list[dict]) -> None:
    """Parse device event/log data into the data model.

    Events represent log entries, alarms, or audit records
    collected from the device.

    Args:
        dev: DeviceData object to populate.
        events: List of event dicts from parsed data.
    """
    for evt_data in events:
        evt = Event(
            # id: unique event identifier
            id=evt_data.get("id", ""),
            # message: human-readable event message
            message=evt_data.get("message", ""),
            # action: what action was taken (e.g. "login", "config-change")
            action=evt_data.get("action", ""),
            # outcome: result of the action ("success", "failure")
            outcome=evt_data.get("outcome", ""),
            # severity: event severity level (info, warning, error, critical)
            severity=evt_data.get("severity", ""),
            # original: raw/original event text for forensic reference
            original=evt_data.get("raw", ""),
        )

        # created: when the event occurred (parsed to UTC datetime)
        if evt_data.get("timestamp"):
            evt.created = utils.parse_date(evt_data["timestamp"])

        # category: ECS event category list
        if evt_data.get("category"):
            evt.category = evt_data["category"] if isinstance(
                evt_data["category"], list
            ) else [evt_data["category"]]

        dev.store("event", evt, lookup="id")


def parse_firmware_info(dev: DeviceData, raw_data: str) -> None:
    """Parse firmware version from CLI output.

    Handles the common pattern of extracting version info from
    command-line output (e.g. "show version").

    Args:
        dev: DeviceData object to populate.
        raw_data: Raw CLI output as a string.
    """
    # Example patterns -- adjust for your device's output format:
    #   "Firmware Version: 1.2.3"
    #   "Software v4.5.6 Build 789"
    #   "Version  : 2.0.1-rc1"

    version_match = re.search(r"(?:Firmware|Software)\s+(?:Version:?\s*|v)(\S+)", raw_data, re.I)
    if version_match:
        dev.firmware.version = version_match.group(1)

    serial_match = re.search(r"Serial\s+(?:Number:?\s*)(\S+)", raw_data, re.I)
    if serial_match:
        dev.serial_number = serial_match.group(1)

    model_match = re.search(r"Model:?\s+(\S+)", raw_data, re.I)
    if model_match:
        dev.description.model = model_match.group(1)
