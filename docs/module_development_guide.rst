Module Development Guide: Building a PEAT Module from Scratch
==============================================================

This guide walks through creating a new PEAT device module end-to-end —
from an empty file to a tested, working module that can scan, pull,
and parse device data.

If you just want to add tests for an existing module, see
``docs/testing_guide.rst`` instead.


Prerequisites
-------------

- PEAT development environment set up (``pdm install``)
- Familiarity with the device you're building a module for
- Sample data from the device (config exports, SSH output, HTTP
  responses, etc.)


How PEAT Modules Work
---------------------

A PEAT module is a Python class that extends ``DeviceModule`` and tells
PEAT how to interact with a specific type of device. The module lifecycle
has three phases:

1. **Scan** — discover and fingerprint devices on a network
   (``peat scan``)
2. **Pull** — connect to a device and retrieve its data
   (``peat pull``)
3. **Parse** — take raw data (files, exports) and extract structured
   information (``peat parse``)

Not every module needs all three. A parse-only module is the simplest
starting point and is the most common type.

.. tip::

   Start with ``_parse()`` only. You can add ``_pull()`` and scanning
   later. Most of the development time is spent figuring out how to
   extract useful information from raw device data.


Quick Start: The Minimum Viable Module
---------------------------------------

The smallest possible module needs just a class with metadata and a
``_parse()`` method. Here is a complete, working example:

.. code-block:: python

   # peat/modules/acme/acme_router.py

   import json
   from pathlib import Path

   from peat import DeviceData, DeviceModule, datastore


   class AcmeRouter(DeviceModule):
       """PEAT module for ACME Router devices."""

       device_type = "Router"
       vendor_id = "ACME"
       vendor_name = "ACME Corporation"
       filename_patterns = ["acme_*.json"]

       @classmethod
       def _parse(cls, file: Path, dev: DeviceData | None = None) -> DeviceData | None:
           data = json.loads(file.read_text(encoding="utf-8"))

           if not dev:
               dev = datastore.get(data["ip"], "ip")

           dev.name = data.get("hostname", "")
           dev.os.name = data.get("os", "")
           dev.description.model = data.get("model", "")

           return dev

   __all__ = ["AcmeRouter"]

Test it immediately:

.. code-block:: bash

   # Create a sample input file
   echo '{"ip": "192.168.1.1", "hostname": "core-rtr", "os": "AcmeOS", "model": "AR-5000"}' > /tmp/acme_config.json

   # Parse it
   pdm run peat parse -d AcmeRouter -I peat/modules/acme/acme_router.py -- /tmp/acme_config.json


Step-by-Step: Building a Complete Module
-----------------------------------------

Step 1: Plan your module
~~~~~~~~~~~~~~~~~~~~~~~~~

Before writing code, answer these questions:

- **What data do you have?** Config exports, SSH command output, HTTP
  pages, SNMP responses, binary files?
- **What format is it in?** JSON, XML, plain text, binary, archive
  (tar.gz, zip)?
- **What information can you extract?** IP addresses, hostnames, OS
  versions, firmware, network interfaces, services, users, config?
- **How do you access the device?** HTTP, SSH, Telnet, serial, SNMP?
  (Only needed if implementing ``_pull()``)

Step 2: Create the module files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

   peat/modules/<vendor>/
   ├── __init__.py          # Exports the module class
   └── <vendor>_<device>.py # Module implementation

**__init__.py:**

.. code-block:: python

   from peat.modules.acme.acme_router import AcmeRouter

   __all__ = ["AcmeRouter"]

**acme_router.py** — start with the minimum viable module shown above,
then build it up as described in the following steps.

Step 3: Define module metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These class attributes tell PEAT what your module is and how to use it:

.. code-block:: python

   class AcmeRouter(DeviceModule):
       # What type of device this module handles
       # Common values: "PLC", "RTU", "HMI", "Switch", "Router", "Relay",
       #                "Firewall", "Server", "Gateway"
       device_type = "Router"

       # Vendor identification
       vendor_id = "ACME"           # Short form, e.g. "SEL", "GE", "ABB"
       vendor_name = "ACME Corp."   # Full name

       # File patterns this module can parse.
       # Supports globs: "*.rdb", "*.json", "*config*.xml"
       # Also supports literal names: "device_export.json"
       filename_patterns = ["acme_*.json", "*.acme"]

       # Optional: aliases let users refer to this module by other names
       # e.g. "peat parse -d acme" instead of "-d AcmeRouter"
       module_aliases = ["acme", "acmerouter"]

       # Optional: default configuration options for this module
       # Users can override these in the PEAT config YAML file
       default_options = {
           "acmerouter": {
               "pull_methods": ["http", "ssh"],
               "parse_firmware": True,
           }
       }

Step 4: Implement _parse()
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``_parse()`` method is the core of most modules. It receives a
``pathlib.Path`` to the input file and returns a populated
``DeviceData`` object.

.. code-block:: python

   from peat import (
       DeviceData,
       DeviceModule,
       Interface,
       Service,
       datastore,
   )

   @classmethod
   def _parse(cls, file: Path, dev: DeviceData | None = None) -> DeviceData | None:
       # 1. Read and parse the input file
       raw = file.read_text(encoding="utf-8")
       data = json.loads(raw)

       # 2. Get or create a DeviceData object
       #    The datastore prevents duplicates — if a device with this IP
       #    already exists, you get the existing object back.
       if not dev:
           dev = datastore.get(data["management_ip"], "ip")

       # 3. Populate basic fields
       dev.name = data.get("hostname", "")
       dev.os.name = data.get("os_name", "")
       dev.os.version = data.get("os_version", "")
       dev.os.full = f"{dev.os.name} {dev.os.version}"
       dev.description.model = data.get("model", "")
       dev.description.serial_number = data.get("serial", "")
       dev.firmware.version = data.get("firmware_version", "")

       # 4. Add network interfaces
       for iface_data in data.get("interfaces", []):
           iface = Interface(
               name=iface_data.get("name", ""),
               type="ethernet",
               ip=iface_data.get("ip", ""),
               subnet_mask=iface_data.get("mask", ""),
               mac=iface_data.get("mac", ""),
           )
           dev.store("interface", iface)

       # 5. Add services
       for svc_data in data.get("services", []):
           service = Service(
               protocol=svc_data.get("protocol", ""),
               port=svc_data.get("port", 0),
               transport=svc_data.get("transport", "tcp"),
               enabled=svc_data.get("enabled", True),
           )
           # Associate with an interface if applicable
           if svc_data.get("interface_ip"):
               dev.store(
                   key="service",
                   value=service,
                   interface_lookup={"ip": svc_data["interface_ip"]},
               )
           else:
               dev.store("service", service)

       # 6. Store any remaining data in "extra" for reference
       dev.extra["raw_config"] = data

       # 7. Write intermediate files if needed (optional)
       # dev.write_file(some_data, "parsed-config.json")

       # 8. MUST return the DeviceData object
       return dev

**Key rules for _parse():**

- Always return a ``DeviceData`` object (or ``None`` on failure)
- Use ``datastore.get()`` to create/retrieve objects — never construct
  ``DeviceData()`` directly in a module
- Use ``dev.store()`` to add complex objects (interfaces, services) —
  it handles deduplication
- Use ``file.read_text(encoding="utf-8")`` for text, or
  ``file.read_bytes()`` for binary data
- Handle the case where ``dev`` is passed in (from a pull operation)

Step 5: Implement _pull() (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your module can connect to devices and retrieve data, implement
``_pull()``. It returns ``True`` if all data was successfully retrieved.

.. code-block:: python

   from peat.protocols import HTTP, SSH

   @classmethod
   def _pull(cls, dev: DeviceData) -> bool:
       success = True

       # Check which pull methods are enabled in config
       pull_methods = dev.options.get("acmerouter", {}).get("pull_methods", [])

       if "http" in pull_methods:
           if not cls._pull_http(dev):
               success = False

       if "ssh" in pull_methods:
           if not cls._pull_ssh(dev):
               success = False

       return success

   @classmethod
   def _pull_http(cls, dev: DeviceData) -> bool:
       """Pull configuration via HTTP."""
       port = dev.options["http"]["port"]
       timeout = dev.options["http"]["timeout"]

       try:
           with HTTP(dev.ip, port, timeout) as http:
               response = http.get("/api/config")
               if not response:
                   cls.log.warning(f"HTTP pull failed for {dev.ip}: no response")
                   return False

               data = response.json()
               path = dev.write_file(data, "acme_config.json")

               # Parse the pulled data immediately
               cls.parse(path, dev)
               return True
       except Exception as err:
           cls.log.warning(f"HTTP pull failed for {dev.ip}: {err}")
           return False

   @classmethod
   def _pull_ssh(cls, dev: DeviceData) -> bool:
       """Pull configuration via SSH."""
       port = dev.options["ssh"]["port"]
       timeout = dev.options["ssh"]["timeout"]

       try:
           with SSH(dev.ip, port=port, timeout=timeout) as ssh:
               if not ssh.connected:
                   cls.log.warning(f"SSH connection failed for {dev.ip}")
                   return False

               # Run commands and collect output
               output = ssh.write_read("show running-config")
               dev.write_file(output, "running_config.txt")

               version_output = ssh.write_read("show version")
               dev.write_file(version_output, "version.txt")

               return True
       except Exception as err:
           cls.log.warning(f"SSH pull failed for {dev.ip}: {err}")
           return False

Step 6: Add device identification (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Identification methods let ``peat scan`` discover and fingerprint your
device on a network. They are added after the class definition using
``IPMethod`` objects:

.. code-block:: python

   from peat import IPMethod

   class AcmeRouter(DeviceModule):
       # ... class definition ...

       @classmethod
       def _verify_http(cls, dev: DeviceData) -> bool:
           """Check if the device is an ACME Router via HTTP."""
           port = dev.options["http"]["port"]
           timeout = dev.options["http"]["timeout"]

           try:
               with HTTP(dev.ip, port, timeout) as http:
                   response = http.get("/api/info")
                   if not response:
                       return False

                   data = response.json()
                   if "ACME" not in data.get("vendor", ""):
                       return False

                   # Extract what we can during verification
                   dev.name = data.get("hostname", "")
                   dev.description.model = data.get("model", "")
                   return True
           except Exception:
               return False

   # Add identification methods AFTER the class definition
   AcmeRouter.ip_methods = [
       IPMethod(
           name="acme_http_check",
           description="Verify ACME Router via HTTP API",
           type="unicast_ip",
           identify_function=AcmeRouter._verify_http,
           reliability=8,        # 1-10 scale
           protocol="http",
           transport="tcp",
           default_port=80,
       ),
   ]

   AcmeRouter.serial_methods = []  # Add serial methods here if needed


Step 7: Register the module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the module's exports to ``peat/modules/__init__.py``:

.. code-block:: python

   from peat.modules.acme import AcmeRouter

And to ``peat/__init__.py`` if the class should be importable as
``from peat import AcmeRouter``.


Step 8: Add tests
~~~~~~~~~~~~~~~~~~

See the "Step-by-Step: Adding a New Device Module's Output to Tests"
section in ``docs/testing_guide.rst`` for the complete testing workflow.

The short version:

1. Create ``tests/modules/acme/`` with ``__init__.py``,
   ``test_acme_router.py``, and ``data_files/``
2. Place raw input files in ``data_files/``
3. Generate expected output using ``peat parse`` and save as
   ``<input_stem>_expected_device-data-summary.json`` and
   ``<input_stem>_expected_device-data-full.json``
4. Write parametrized tests using ``dev_data_compare`` fixture
5. Run: ``pdm run pytest tests/modules/acme/ -v``


Step 9: Add a test data generator (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you expect the module's parsing logic to evolve, add a generator
to ``tests/generate_test_data_files.py`` to automate regeneration of
expected output:

.. code-block:: python

   class AcmeRouterGenerator(TestDataGenerator):
       input_paths = ["./tests/modules/acme/data_files/"]
       input_globs = ["acme_*.json"]
       file_types = ["device-data-full.json", "device-data-summary.json"]

Usage:

.. code-block:: bash

   pdm run python tests/generate_test_data_files.py AcmeRouter


The DeviceData Model
---------------------

``DeviceData`` is the central data structure that stores everything
PEAT knows about a device. Here are the most commonly used fields:

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Field
     - Type
     - Description
   * - ``dev.name``
     - ``str``
     - Device hostname
   * - ``dev.ip``
     - ``str``
     - Management IP address
   * - ``dev.type``
     - ``str``
     - Device type (auto-set from ``cls.device_type``)
   * - ``dev.os.name``
     - ``str``
     - Operating system name
   * - ``dev.os.version``
     - ``str``
     - OS version
   * - ``dev.os.full``
     - ``str``
     - Full OS string
   * - ``dev.os.kernel``
     - ``str``
     - Kernel version
   * - ``dev.firmware.version``
     - ``str``
     - Firmware version
   * - ``dev.description.model``
     - ``str``
     - Device model
   * - ``dev.description.serial_number``
     - ``str``
     - Serial number
   * - ``dev.description.vendor.id``
     - ``str``
     - Vendor short ID (auto-set from ``cls.vendor_id``)
   * - ``dev.description.vendor.name``
     - ``str``
     - Vendor name (auto-set from ``cls.vendor_name``)
   * - ``dev.interface``
     - ``list[Interface]``
     - Network interfaces
   * - ``dev.service``
     - ``list[Service]``
     - Network services
   * - ``dev.extra``
     - ``dict``
     - Freeform storage for anything else
   * - ``dev.hostname``
     - ``str``
     - Alternative to ``dev.name``

**Storing data:**

- ``dev.store("interface", iface_obj)`` — adds with deduplication
- ``dev.store("service", svc_obj)`` — adds with deduplication
- ``dev.write_file(content, filename)`` — writes a file to the output dir
- ``dev.export_summary()`` — exports summary dict
- ``dev.export(include_original=True)`` — exports full dict


Available Protocols
--------------------

PEAT provides protocol classes you can use in ``_pull()`` and
identification methods:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Class
     - Import
     - Use case
   * - ``HTTP``
     - ``from peat.protocols import HTTP``
     - REST APIs, web pages, firmware downloads
   * - ``SSH``
     - ``from peat.protocols import SSH``
     - Command-line access, file retrieval
   * - ``Telnet``
     - ``from peat.protocols import Telnet``
     - Legacy device access
   * - ``SNMP``
     - ``from peat.protocols import SNMP``
     - SNMP queries (GET, WALK)
   * - ``Serial``
     - ``from peat.protocols import Serial``
     - Serial/RS-232 connections

All protocol classes support ``with`` statements for automatic cleanup:

.. code-block:: python

   with HTTP(ip, port, timeout) as http:
       response = http.get("/api/status")

   with SSH(ip, port=22, timeout=10) as ssh:
       output = ssh.write_read("show version")


External Module Loading
------------------------

During development, you can load your module from any path using the
``-I`` flag without installing it into the ``peat/modules/`` directory:

.. code-block:: bash

   # Load from a standalone file
   peat parse -d AcmeRouter -I ./my_module.py -- input_file.json

   # Load from a directory containing the module
   peat parse -d AcmeRouter -I ./my_modules/ -- input_file.json

   # Scan using an external module
   peat scan -d AcmeRouter -I ./my_module.py -i 192.168.1.0/24

This is useful for:

- Developing modules before adding them to the main codebase
- Proprietary modules that can't be open-sourced
- Quick prototyping and testing


Module Development Workflow Summary
-------------------------------------

1. **Start with data** — get sample output from the device
2. **Write _parse()** — extract structured information from the data
3. **Test with the CLI** — ``peat parse -d MyModule -I ./module.py -- input``
4. **Add to the codebase** — move to ``peat/modules/<vendor>/``
5. **Write tests** — see ``docs/testing_guide.rst``
6. **Add _pull() if needed** — connect to devices and retrieve data
7. **Add identification** — let ``peat scan`` discover the device
8. **Add test data generator** — automate expected output regeneration

The example module at ``examples/example_peat_module/awesome_module.py``
is a complete, well-commented reference implementation that demonstrates
all of these concepts.
