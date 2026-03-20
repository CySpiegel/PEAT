Testing Guide: Adding Tests with SSH Output Data
=================================================

This guide explains how to add unit tests to PEAT's testing framework,
with a focus on testing parsers and modules that consume SSH command output.

If you have SSH output files (e.g., command responses captured from devices),
this guide will walk you through integrating them as test data.


Overview of PEAT's Testing Framework
-------------------------------------

PEAT uses **pytest** with these key plugins:

- ``pytest-mock`` — mocking via the ``mocker`` fixture
- ``pytest-cov`` — code coverage
- ``pytest-xdist`` — parallel test execution (``-n 4``)
- ``pytest-randomly`` — randomized test ordering
- ``xdoctest`` — doctest support
- ``pytest-loguru`` — loguru integration

**Run tests:**

.. code-block:: bash

   pdm run test          # Fast: excludes @pytest.mark.slow tests
   pdm run test-full     # Comprehensive: includes slow tests

**Run a specific test file or test:**

.. code-block:: bash

   pdm run pytest tests/parsing/test_command_parsers.py
   pdm run pytest tests/parsing/test_command_parsers.py::test_parse_env -v


Directory Structure
-------------------

Tests mirror the ``peat/`` package structure. Each test directory can have
a ``data_files/`` subdirectory for test data::

   tests/
   ├── conftest.py                    # Global fixtures
   ├── __init__.py
   ├── data_files/                    # General test data
   │   ├── test-scan-results-localhost-clx.json
   │   └── ...
   ├── parsing/
   │   ├── __init__.py
   │   ├── test_command_parsers.py    # Parser tests
   │   └── data_files/               # Parser test data
   │       ├── env.txt               # Raw input (SSH output)
   │       ├── expected_env.json     # Expected parsed output
   │       ├── sshd_config           # Raw file content
   │       ├── expected_sshd_config.json
   │       └── ...
   ├── protocols/
   │   ├── test_http.py
   │   └── data_files/               # Protocol test data
   │       ├── sage_certificate.cert
   │       └── expected_parsed_sage_certificate.json
   └── modules/
       └── rockwell/
           ├── test_controllogix.py
           └── data_files/           # Module-specific test data


File Naming Conventions
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - File Type
     - Naming Pattern
     - Example
   * - Raw SSH command output
     - ``<command_or_description>.txt``
     - ``proc_cpuinfo.txt``, ``arp_a.txt``
   * - Raw file content (from ``cat``)
     - Use the original filename
     - ``sshd_config``, ``etc_passwd.txt``
   * - Expected parsed output
     - ``expected_<input_stem>.json``
     - ``expected_proc_cpuinfo.json``
   * - Expected device summary
     - ``<input>_expected_device-data-summary.json``
     - ``sceptre_expected_device-data-summary.json``
   * - Expected full device data
     - ``<input>_expected_device-data-full.json``
     - ``awesome_output_expected_device-data-full.json``


Key Fixtures (from conftest.py)
-------------------------------

These fixtures are defined in ``tests/conftest.py`` and are available
to all tests.

Data Loading Fixtures
~~~~~~~~~~~~~~~~~~~~~

All of these resolve paths relative to the ``data_files/`` directory
adjacent to the test file being run.

``text_data(filename) -> str``
   Read a text file from ``data_files/``, preserving original line endings.
   Use this for raw SSH output, command output, and config files.

   .. code-block:: python

      def test_my_parser(text_data):
          raw_output = text_data("my_command_output.txt")

``json_data(filename) -> dict | list``
   Load and parse a JSON file from ``data_files/``.
   Use this for expected output files.

   .. code-block:: python

      def test_my_parser(json_data):
          expected = json_data("expected_my_command_output.json")

``binary_data(filename) -> bytes``
   Read a binary file from ``data_files/``.

``datapath(filename) -> Path``
   Get the full ``Path`` to a file in ``data_files/``.
   Use when you need the path itself, not the contents.

``datadir -> Path``
   The ``data_files/`` directory path for the current test module.

Execution Fixtures
~~~~~~~~~~~~~~~~~~

``run_peat(args) -> (stdout, stderr)``
   Run the PEAT CLI as a subprocess, assert exit code 0,
   and return decoded stdout/stderr strings.

``exec_peat(args) -> CompletedProcess``
   Run the PEAT CLI as a subprocess, returning the raw
   ``CompletedProcess`` object (doesn't assert on exit code).

Assertion Fixtures
~~~~~~~~~~~~~~~~~~

``assert_no_errors()``
   Assert no ``ERROR`` or ``CRITICAL`` messages in captured log output.

``assert_no_warns()``
   Assert no ``WARNING``, ``ERROR``, or ``CRITICAL`` in log output.

``assert_no_criticals()``
   Assert no ``CRITICAL`` in log output.

``assert_meta_files(run_dir=None)``
   Assert that standard PEAT output files were created (logs, metadata).

``assert_glob_path(directory, pattern) -> Path``
   Assert exactly one file matches the glob, exists, is non-empty,
   and (if JSON) is valid. Returns the matched path.

Comparison Fixtures
~~~~~~~~~~~~~~~~~~~

``deep_compare(first, second, exclude_regexes=None)``
   Compare two dicts using ``DeepDiff``, with optional regex-based
   field exclusion. Prints a readable diff on failure.

``dev_data_compare(expected, actual, additional_regexes=None)``
   Like ``deep_compare`` but pre-excludes volatile device data fields
   (``directory``, ``path``, ``owner``, ``group``, ``created``, ``mtime``,
   ``local_path``).


Step-by-Step: Adding a Command Parser Test
-------------------------------------------

This is the most common pattern when you have SSH output files.
PEAT already includes parsers for many Linux commands (``/proc/*``,
``arp``, ``env``, ``hostname``, ``sshd_config``, etc.) in
``peat/parsing/command_parsers.py``. You can add tests for existing
parsers or write new ones.

Step 1: Add test data files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Place your SSH output in the appropriate ``data_files/`` directory.
If testing a command parser, use ``tests/parsing/data_files/``.

For example, if you captured the output of ``uname -a``:

.. code-block:: text

   # tests/parsing/data_files/uname_a.txt
   Linux mydevice 4.14.73 #1 SMP PREEMPT Wed Sep 12 13:02:00 UTC 2018 armv7l GNU/Linux

Step 2: Create the expected output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create the JSON file that represents the correctly parsed result:

.. code-block:: json

   // tests/parsing/data_files/expected_uname_a.json
   {
       "kernel": "Linux",
       "hostname": "mydevice",
       "kernel_version": "4.14.73",
       "architecture": "armv7l",
       "os": "GNU/Linux"
   }

.. tip::

   If you already have a working parser, you can generate the expected
   output by running the parser in a Python REPL or a throwaway script,
   then saving the result as JSON.

Step 3: Write the parser (if needed)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a parser doesn't already exist in ``peat/parsing/command_parsers.py``,
create one by subclassing ``NixParserBase``:

.. code-block:: python

   # In peat/parsing/command_parsers.py

   class UnameParser(NixParserBase):
       """Parse output of ``uname -a``."""

       command = "uname -a"

       @classmethod
       def parse(cls, to_parse: str) -> dict:
           if not to_parse.strip():
               return {}

           parts = to_parse.strip().split()
           return {
               "kernel": parts[0],
               "hostname": parts[1],
               "kernel_version": parts[2],
               "architecture": parts[-2],
               "os": parts[-1],
           }

       @classmethod
       def process(cls, to_process: dict, dev: DeviceData) -> None:
           if not to_process:
               return
           dev.os.name = to_process.get("kernel", "")
           dev.os.kernel = to_process.get("kernel_version", "")
           dev.hostname = to_process.get("hostname", "")

Key attributes:

- ``command = "uname -a"`` — for command output
- ``file = PurePosixPath("/etc/ssh/sshd_config")`` — for file content
- ``parse()`` — converts raw string to structured data (dict/list)
- ``process()`` — populates fields on a ``DeviceData`` instance

Step 4: Write the test
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # In tests/parsing/test_command_parsers.py

   def test_parse_uname(text_data, json_data, assert_no_errors):
       # Test empty input returns empty
       assert command_parsers.UnameParser.parse("") == {}

       # Test parsing
       results = command_parsers.UnameParser.parse(text_data("uname_a.txt"))
       assert results == json_data("expected_uname_a.json")
       assert_no_errors()


   def test_process_uname(json_data, mocker, tmp_path, assert_no_errors):
       mocker.patch.dict(config["CONFIG"], {"DEVICE_DIR": tmp_path})

       # Test empty input
       assert not command_parsers.UnameParser.process({}, DeviceData())

       # Test processing into DeviceData
       dev = DeviceData(id="test_process_uname")
       data = json_data("expected_uname_a.json")
       command_parsers.UnameParser.process(data, dev)
       assert dev.hostname == "mydevice"
       assert dev.os.kernel == "4.14.73"
       assert_no_errors()


   def test_uname_parse_and_process(text_data, json_data, mocker, tmp_path, assert_no_errors):
       """Integration test: parse raw input and process into device model."""
       mocker.patch.dict(config["CONFIG"], {"DEVICE_DIR": tmp_path})

       input_data = text_data("uname_a.txt")
       dev = DeviceData(id="test_uname_integration")
       assert command_parsers.UnameParser.parse_and_process(input_data, dev)
       assert dev.extra["uname -a"] == json_data("expected_uname_a.json")
       assert_no_errors()

The standard test pattern has three layers:

1. **Parse test** — ``parse()`` converts raw text to structured data
2. **Process test** — ``process()`` populates ``DeviceData`` fields
3. **Integration test** — ``parse_and_process()`` does both end-to-end


Step-by-Step: Adding a Module Parse Test
-----------------------------------------

If your SSH output comes from a specific device module (e.g., a new
module that connects via SSH and pulls configuration), use this pattern.

Step 1: Create the test directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

   tests/modules/<vendor>/
   ├── __init__.py
   ├── test_<module>.py
   └── data_files/
       ├── device_output.json          # Raw captured data
       ├── device_output_expected_device-data-summary.json
       └── device_output_expected_device-data-full.json

Step 2: Write the test
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import filecmp
   import json

   import pytest

   from peat import DeviceData, config, datastore
   from peat.modules.<vendor> import MyDevice

   data_files = [
       "device_output.json",
   ]


   @pytest.mark.parametrize("input_filename", data_files)
   def test_parse_my_device(
       json_data, tmp_path, mocker, datapath,
       dev_data_compare, assert_glob_path, input_filename, caplog,
   ):
       # Mock configuration paths
       mocker.patch.dict(
           config["CONFIG"],
           {
               "DEVICE_DIR": tmp_path / "devices",
               "SUMMARIES_DIR": tmp_path / "summaries",
               "TEMP_DIR": tmp_path / "temp",
           },
       )
       mocker.patch.object(datastore, "objects", [])

       # Run the parse
       source_path = datapath(input_filename)
       parsed_device = MyDevice.parse(source_path)

       # Verify the source file was copied to output
       assert filecmp.cmp(parsed_device._out_dir / source_path.name, source_path)

       # Compare exported summary to expected
       exported_summary = parsed_device.export_summary()
       expected_summary = json_data(
           f"{source_path.stem}_expected_device-data-summary.json"
       )
       dev_data_compare(expected_summary, exported_summary)

       # Verify output files were created
       assert_glob_path(parsed_device._out_dir, "device-data-summary.json")

       # No errors in logs
       assert "ERROR" not in caplog.text
       assert "CRITICAL" not in caplog.text

Step 3: Generate expected output files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can generate expected output by adding a generator to
``tests/generate_test_data_files.py``, or manually:

.. code-block:: bash

   # Parse a file and inspect the output
   pdm run peat parse -vVV -d mydevice -o /tmp/peat_test -- path/to/input_file

   # The device-data-summary.json and device-data-full.json in the output
   # become your expected files (after review and renaming)


Testing SSH Protocol Interactions
----------------------------------

When testing code that uses the SSH protocol class directly
(e.g., a module's ``pull()`` method), mock the SSH connection
rather than making real connections.

.. code-block:: python

   from unittest.mock import MagicMock

   from peat import DeviceData, config, datastore
   from peat.modules.idirect import Idirect
   from peat.protocols.ssh import SSH


   def test_pull_with_mocked_ssh(mocker, tmp_path):
       mocker.patch.dict(
           config["CONFIG"],
           {
               "RUN_DIR": tmp_path,
               "DEVICE_DIR": tmp_path / "devices",
               "TEMP_DIR": tmp_path / "temp",
           },
       )
       mocker.patch.object(datastore, "objects", [])

       # Create a mock SSH connection
       mock_ssh = MagicMock(spec=SSH)
       mock_ssh.connected = True
       mock_ssh.all_output = ["device banner text"]

       # Mock write_read to return captured SSH output
       mock_ssh.write_read.side_effect = [
           "command1 output here",
           "command2 output here",
       ]

       # Patch the SSH constructor to return the mock
       mocker.patch(
           "peat.modules.idirect.idirect.SSH",
           return_value=mock_ssh,
       )

       dev = datastore.get("192.0.2.1")
       dev._runtime_options["timeout"] = 0.01

       # Call the module method under test
       # ... your test logic here ...


Mocking Patterns Reference
---------------------------

Config Patching
~~~~~~~~~~~~~~~

Always mock config paths to use ``tmp_path``:

.. code-block:: python

   mocker.patch.dict(
       config["CONFIG"],
       {
           "RUN_DIR": tmp_path,
           "DEVICE_DIR": tmp_path / "devices",
           "SUMMARIES_DIR": tmp_path / "summaries",
           "TEMP_DIR": tmp_path / "temp",
           "LOG_DIR": tmp_path / "logs",
       },
   )

Datastore Isolation
~~~~~~~~~~~~~~~~~~~

Reset the global datastore so tests don't share state:

.. code-block:: python

   mocker.patch.object(datastore, "objects", [])

Module Manager Isolation
~~~~~~~~~~~~~~~~~~~~~~~~

For tests that import modules dynamically:

.. code-block:: python

   mocker.patch.object(module_api, "modules", {})
   mocker.patch.object(module_api, "module_aliases", {})
   mocker.patch.object(module_api, "runtime_imports", set())
   mocker.patch.object(module_api, "runtime_paths", set())


Test Markers
------------

``@pytest.mark.slow``
   Tests that take a long time (CLI subprocess tests). Skipped
   unless ``--run-slow`` is passed or ``RUN_SLOW`` env var is set.

``@pytest.mark.gitlab_ci_only``
   Integration tests requiring external services (e.g., Elasticsearch).
   Skipped unless ``--run-ci`` is passed.

``@pytest.mark.broadcast_ci``
   Live network broadcast tests. Skipped unless ``--run-broadcast-ci``
   is passed.


Working with Your SSH Output Files
------------------------------------

If you have a collection of SSH output files from devices, here is
a practical workflow to turn them into tests:

1. **Identify what each file contains.**
   Is it the output of a command (``cat /proc/cpuinfo``), the contents
   of a file (``/etc/ssh/sshd_config``), or the full session transcript?

2. **Check if a parser already exists.**
   Look in ``peat/parsing/command_parsers.py`` for parsers matching
   your data. Common parsers:

   .. list-table::
      :header-rows: 1
      :widths: 40 30 30

      * - Parser
        - Type
        - Source
      * - ``EnvParser``
        - command
        - ``env``
      * - ``ProcCpuinfoParser``
        - file
        - ``/proc/cpuinfo``
      * - ``ProcMeminfoParser``
        - file
        - ``/proc/meminfo``
      * - ``ProcModulesParser``
        - file
        - ``/proc/modules``
      * - ``ProcUptimeParser``
        - file
        - ``/proc/uptime``
      * - ``ProcNetDevParser``
        - file
        - ``/proc/net/dev``
      * - ``EtcPasswdParser``
        - file
        - ``/etc/passwd``
      * - ``SshdConfigParser``
        - file
        - ``/etc/ssh/sshd_config``
      * - ``VarLogMessagesParser``
        - file
        - ``/var/log/messages``
      * - ``DateParser``
        - command
        - ``date``
      * - ``HostnameParser``
        - command
        - ``hostname``
      * - ``ArpParser``
        - command
        - ``arp -a``
      * - ``IfconfigParser``
        - command
        - ``ifconfig -a``
      * - ``LsRecursiveParser``
        - command
        - ``ls -laR``

3. **If no parser exists, write one** following the ``NixParserBase``
   pattern shown above.

4. **Place raw output files** in ``tests/parsing/data_files/``
   (for parsers) or ``tests/modules/<vendor>/data_files/``
   (for module-specific tests).

5. **Create expected output JSON.** Run the parser manually or in
   a REPL to produce the expected output, review it for correctness,
   then save it as ``expected_<name>.json``.

6. **Write the test** following the patterns above.

7. **Run and verify:**

   .. code-block:: bash

      pdm run pytest tests/parsing/test_command_parsers.py::test_parse_uname -v


Step-by-Step: Adding a New Device Module's Output to Tests
-----------------------------------------------------------

This is the complete workflow for when you have a brand new device type
and want to add its output dump as a tested module — from raw data to
passing CI.

Step 1: Create the module (if it doesn't exist)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you haven't written the module yet, see ``docs/module_development_guide.rst``
for the full tutorial. If the module already exists, skip to Step 2.

Step 2: Capture raw device output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Capture the output from the device however it's produced — SSH session
transcripts, HTTP responses, config file exports, binary dumps, etc.
Save these as files. For example, for a fictional "Acme Router":

::

   acme_router_config.json
   acme_router_large_config.json

Step 3: Create the test directory structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

   tests/modules/<vendor>/
   ├── __init__.py
   ├── test_<module>.py
   └── data_files/
       ├── acme_router_config.json
       ├── acme_router_config_expected_device-data-summary.json
       ├── acme_router_config_expected_device-data-full.json
       ├── acme_router_large_config.json
       ├── acme_router_large_config_expected_device-data-summary.json
       └── acme_router_large_config_expected_device-data-full.json

Create the ``__init__.py`` files (they can be empty).

Step 4: Generate expected output files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Option A: Use the CLI to generate expected output manually**

.. code-block:: bash

   # Parse the input file and save output to a temporary directory
   pdm run peat parse -vVV -d AcmeRouter -o /tmp/peat_gen -- tests/modules/acme/data_files/acme_router_config.json

   # Find the output files in the run directory
   ls /tmp/peat_gen/parse_*/devices/*/

   # Copy and rename the output files to your data_files directory
   cp /tmp/peat_gen/parse_*/devices/*/device-data-summary.json \
      tests/modules/acme/data_files/acme_router_config_expected_device-data-summary.json
   cp /tmp/peat_gen/parse_*/devices/*/device-data-full.json \
      tests/modules/acme/data_files/acme_router_config_expected_device-data-full.json

**Review the generated files** for correctness before committing them.
They become the ground truth for your tests.

**Option B: Add a generator to** ``tests/generate_test_data_files.py``

This automates regeneration when the module's parsing logic changes:

.. code-block:: python

   class AcmeRouterGenerator(TestDataGenerator):
       input_paths = ["./tests/modules/acme/data_files/"]
       input_globs = ["*.json"]
       file_types = ["device-data-full.json", "device-data-summary.json"]

Then run:

.. code-block:: bash

   pdm run python tests/generate_test_data_files.py AcmeRouter

Step 5: Write the test
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/modules/acme/test_acme_router.py

   import filecmp

   import pytest

   from peat import DeviceData, config, datastore
   from peat.modules.acme import AcmeRouter

   # List all input files to test — each one is a separate test case
   data_files = [
       "acme_router_config.json",
       "acme_router_large_config.json",
   ]


   @pytest.mark.parametrize("input_filename", data_files)
   def test_parse_acme_router(
       json_data, tmp_path, mocker, datapath,
       dev_data_compare, assert_glob_path, input_filename, caplog,
   ):
       # Mock config paths to use temp directory
       mocker.patch.dict(
           config["CONFIG"],
           {
               "DEVICE_DIR": tmp_path / "devices",
               "SUMMARIES_DIR": tmp_path / "summaries",
               "TEMP_DIR": tmp_path / "temp",
           },
       )
       # Isolate the datastore so tests don't share state
       mocker.patch.object(datastore, "objects", [])

       # Run the parse
       source_path = datapath(input_filename)
       parsed_device = AcmeRouter.parse(source_path)

       # Verify the source file was copied to output
       assert filecmp.cmp(parsed_device._out_dir / source_path.name, source_path)

       # Compare exported summary to expected
       exported_summary = parsed_device.export_summary()
       expected_summary = json_data(
           f"{source_path.stem}_expected_device-data-summary.json"
       )
       dev_data_compare(expected_summary, exported_summary)

       # Compare exported full data to expected
       exported_full = parsed_device.export(include_original=True)
       expected_full = json_data(
           f"{source_path.stem}_expected_device-data-full.json"
       )
       dev_data_compare(expected_full, exported_full)

       # Verify output files were created
       assert_glob_path(parsed_device._out_dir, "device-data-summary.json")
       assert_glob_path(parsed_device._out_dir, "device-data-full.json")

       # No errors in logs
       assert "ERROR" not in caplog.text
       assert "CRITICAL" not in caplog.text

Step 6: Run and verify
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run just your new test
   pdm run pytest tests/modules/acme/test_acme_router.py -v

   # Run the full test suite to make sure nothing else broke
   pdm run test


Tips and Pitfalls
-----------------

- **Line endings matter.** Use the ``text_data`` fixture (which calls
  ``read_text`` with ``newline=""``) to preserve original line endings.
  If tests pass locally but fail in CI, check ``.gitattributes`` for
  ``eol`` settings on your test data files.

- **Use ``dev_data_compare``** instead of ``==`` when comparing device
  data exports. It excludes volatile fields like ``directory``, ``path``,
  ``mtime``, etc. that change between runs.

- **Always mock ``config["CONFIG"]``** with ``tmp_path``-based paths.
  Never let tests write to the real filesystem.

- **Always mock ``datastore.objects``** to ``[]``. The datastore is
  global and tests run in parallel — without isolation, tests will
  interfere with each other.

- **Test empty/edge cases first.** Every parser test should verify
  that empty string input returns an empty result (``{}``, ``[]``,
  ``None``, or ``False``).

- **Check logs.** Use ``assert_no_errors()`` or check ``caplog.text``
  to ensure no unexpected errors occurred during parsing.

- **Mark slow tests.** If your test spawns a subprocess
  (``run_peat`` / ``exec_peat``), mark it ``@pytest.mark.slow``.
  Pure unit tests (calling ``parse()`` directly) don't need this.
