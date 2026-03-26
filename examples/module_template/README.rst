Module Template
===============

A template for creating new PEAT device modules with proper separation
of concerns. Each file has a single responsibility:

.. code-block:: text

   module_template/
   ├── __init__.py              # Package exports
   ├── mydevice.py              # Main module: attributes, identification, pull/parse orchestration
   ├── mydevice_http.py         # HTTP protocol: auth, endpoints, response processing
   ├── mydevice_ssh.py          # SSH protocol: connection, commands, file transfer
   ├── mydevice_telnet.py       # Telnet protocol: connection, commands, prompts
   ├── mydevice_parse.py        # Parsing logic: file format parsing, data extraction
   ├── test_template_module.py  # Test scaffolding for all components
   └── README.rst               # This file

Quick Start
-----------

1. **Copy the template** into your module directory:

   .. code-block:: bash

      cp -r examples/module_template/ peat/modules/myvendor/

2. **Rename the files** to match your device (e.g. ``mydevice.py`` to
   ``totus.py``, ``mydevice_http.py`` to ``totus_http.py``).

3. **Rename the classes** (e.g. ``MyDevice`` to ``Totus``,
   ``MyDeviceHTTP`` to ``TotusHTTP``).

4. **Fill in TODO placeholders** in each file:

   - ``mydevice.py`` -- device type, vendor info, model, options
   - ``mydevice_http.py`` -- endpoints, auth flow, response processing
   - ``mydevice_ssh.py`` -- commands, file paths (delete if unused)
   - ``mydevice_telnet.py`` -- prompts, commands (delete if unused)
   - ``mydevice_parse.py`` -- file format parsing, data extraction

5. **Delete unused protocol files.** If the device only uses HTTP,
   remove ``mydevice_ssh.py`` and ``mydevice_telnet.py``.

6. **Register the module** (built-in modules only):

   - Update ``peat/modules/<vendor>/__init__.py``
   - Update ``peat/modules/__init__.py``

7. **Copy and update tests** to ``tests/modules/<vendor>/``.

File Responsibilities
---------------------

``mydevice.py`` (main module)
   The entry point. Defines class attributes (vendor, model, device type),
   identification methods (``_verify_*``), and orchestrates pull/parse by
   delegating to protocol helpers. Should contain minimal logic itself.

``mydevice_http.py`` (HTTP protocol)
   Subclasses ``peat.protocols.HTTP`` with device-specific authentication,
   API endpoint definitions, and response processing methods. Each
   ``process_*`` method maps a JSON/HTML response to the ``DeviceData`` model.

``mydevice_ssh.py`` (SSH protocol)
   Wraps ``peat.protocols.SSH`` with device-specific command sequences,
   prompt handling, and SFTP file transfer operations.

``mydevice_telnet.py`` (Telnet protocol)
   Wraps ``peat.protocols.Telnet`` with device-specific login sequences,
   prompt patterns, and command/response handling.

``mydevice_parse.py`` (parsing)
   Standalone functions for parsing device-specific file formats (JSON,
   XML, CSV, binary, proprietary text). Functions here are protocol-agnostic
   so they can be reused by both pull (live) and parse (offline) workflows.

Usage
-----

As an external module (no installation required):

.. code-block:: bash

   peat scan -d MyDevice -I path/to/mydevice.py -i 192.168.1.0/24
   peat pull -d MyDevice -I path/to/mydevice.py -i 192.168.1.100
   peat parse -d MyDevice -I path/to/mydevice.py -- device_config.json

As a built-in module (after registration):

.. code-block:: bash

   peat scan -d MyDevice -i 192.168.1.0/24
   peat pull -d MyDevice -i 192.168.1.100
   peat parse -d MyDevice -- device_config.json

See Also
--------

- ``examples/example_peat_module/`` -- fully worked single-file example
- ``peat/modules/camlin/`` -- production example with HTTP separation
- ``peat/modules/sel/`` -- production example with HTTP, Telnet, serial, and parse separation
- ``docs/device_api.rst`` -- DeviceModule API reference
