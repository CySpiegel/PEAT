*************
Testing guide
*************

.. seealso::

   :doc:`module_developer_guide`

   :doc:`contributing`


Introduction
============
This guide explains how to write unit tests for PEAT modules using the PEAT testing framework. The framework is built on `pytest <https://docs.pytest.org/>`_ and provides a rich set of custom fixtures, data management patterns, and assertion helpers that simplify testing device modules, protocols, parsers, and APIs.

All test infrastructure is centralized in a single ``tests/conftest.py`` file — there are no nested ``conftest.py`` files in subdirectories. This means every fixture described in this guide is available to all tests in the ``tests/`` directory tree.


Quick start
===========
Here's a minimal test for a PEAT module that parses a device output file:

.. code-block:: python

   from peat import config, datastore
   from peat.modules.myvendor.my_device import MyDevice


   def test_parse_my_device(mocker, tmp_path, datapath, json_data, dev_data_compare):
       mocker.patch.dict(
           config["CONFIG"],
           {"DEVICE_DIR": tmp_path / "devices", "TEMP_DIR": tmp_path / "temp"},
       )
       mocker.patch.object(datastore, "objects", [])

       source_path = datapath("sample_output.bin")
       parsed_device = MyDevice.parse(source_path)

       expected = json_data("sample_output_expected_device-data-full.json")
       dev_data_compare(expected, parsed_device.export(include_original=True))

This test:

1. Isolates config to use a temporary directory (avoids writing to real output dirs)
2. Clears the datastore so prior tests don't interfere
3. Loads an input file from the test's ``data_files/`` directory
4. Parses it with the device module
5. Compares the output against a golden expected JSON file, ignoring fields that vary between runs (timestamps, paths, etc.)


Test directory structure
========================
Tests are organized to mirror the source code structure:

.. code-block:: text

   tests/
   ├── conftest.py              # All shared fixtures (read this file!)
   ├── data_files/              # Shared test data (configs, certs, etc.)
   ├── generate_test_data_files.py  # Script to regenerate expected output
   ├── api/                     # Tests for peat.api.*
   │   ├── test_scan_api.py
   │   ├── test_parse_api.py
   │   ├── test_pull_api.py
   │   └── test_push_api.py
   ├── data/                    # Tests for peat.data.*
   │   ├── data_files/
   │   ├── test_models.py
   │   └── test_store.py
   ├── modules/                 # Tests for device modules
   │   ├── rockwell/
   │   │   ├── data_files/      # Module-specific test data
   │   │   ├── test_controllogix.py
   │   │   └── test_clx_cip.py
   │   └── sandia/
   │       ├── data_files/
   │       └── test_sceptre_fcd.py
   ├── parsing/                 # Tests for parsers
   │   ├── data_files/
   │   └── test_command_parsers.py
   ├── protocols/               # Tests for protocol classes
   │   ├── data_files/
   │   ├── test_http.py
   │   ├── test_ssh.py
   │   └── test_telnet.py
   └── test_*.py                # Top-level tests (CLI, config, etc.)


Where to put your tests
-----------------------
- **Device module tests**: ``tests/modules/<vendor>/test_<module>.py``
- **Protocol tests**: ``tests/protocols/test_<protocol>.py``
- **Parser tests**: ``tests/parsing/test_<parser>.py``
- **API tests**: ``tests/api/test_<api>.py``

Each test directory that needs test data should have a ``data_files/`` subdirectory alongside the test files.


Running tests
=============
PEAT uses pytest with configuration in ``pyproject.toml``:

.. code-block:: bash

   # Run all tests (from project root)
   pdm run pytest

   # Run a specific test file
   pdm run pytest tests/modules/sandia/test_sceptre_fcd.py

   # Run a specific test function
   pdm run pytest tests/protocols/test_http.py::test_http_class

   # Run with verbose output
   pdm run pytest -v

   # Run including slow tests
   pdm run pytest --run-slow

   # Run tests matching a keyword
   pdm run pytest -k "ssh"


Test markers
------------
PEAT defines several custom markers for controlling which tests run:

``@pytest.mark.slow``
   Tests that take a long time. Skipped by default; use ``--run-slow`` or set the ``RUN_SLOW`` environment variable to include them.

``@pytest.mark.gitlab_ci_only``
   Tests intended for the GitLab CI environment only (e.g. tests that need specific hardware or network resources). Run with ``--run-ci``.

``@pytest.mark.broadcast_ci``
   Live broadcast tests on the PEAT rack. Run with ``--run-broadcast-ci``.


Fixtures reference
==================
This section documents the fixtures available in ``tests/conftest.py``. All fixtures are available to every test in the ``tests/`` directory tree.


Data access fixtures
--------------------
These fixtures load test data from ``data_files/`` directories. The ``datadir``, ``datapath``, ``json_data``, ``text_data``, ``binary_data``, and ``read_text`` fixtures are **module-scoped** for performance — meaning the data directory is resolved once per test file, not per test function.

``datadir``
   Returns the ``Path`` to the ``data_files/`` directory relative to the current test module.

   .. code-block:: python

      def test_example(datadir):
          assert datadir.is_dir()
          # e.g. tests/modules/myvendor/data_files/

``datapath(filename)``
   Constructs a ``Path`` to a file in the test module's ``data_files/`` directory.

   .. code-block:: python

      def test_example(datapath):
          cert_path = datapath("device_certificate.cert")
          assert cert_path.is_file()

``json_data(filename)``
   Loads and returns parsed JSON from a file in ``data_files/``.

   .. code-block:: python

      def test_example(json_data):
          expected = json_data("expected_output.json")
          assert isinstance(expected, dict)

``text_data(filename)``
   Reads and returns text from a file in ``data_files/``, preserving original line endings (no universal newline translation).

   .. code-block:: python

      def test_example(text_data):
          raw_output = text_data("device_output.txt")
          results = MyParser.parse(raw_output)

``binary_data(filename)``
   Reads and returns raw bytes from a file in ``data_files/``.

   .. code-block:: python

      def test_example(binary_data):
          firmware = binary_data("firmware.bin")
          assert len(firmware) > 0

``read_text(filepath)``
   Generic text reader that preserves line endings. Unlike ``text_data``, this takes a full ``Path`` argument rather than a filename relative to ``data_files/``.

``top_datadir`` / ``top_datapath(filename)``
   Access the shared ``tests/data_files/`` directory (as opposed to per-module ``data_files/``).

``examples_dir`` / ``examples_path(filename)``
   Access the ``examples/`` directory at the project root.

``example_module_file(filename)``
   Access files in ``examples/example_peat_module/``.


Comparison and assertion fixtures
---------------------------------

``deep_compare(first, second, exclude_regexes=None)``
   Compares two dicts using `DeepDiff <https://zepworks.com/deepdiff/>`_ and fails with a detailed diff on mismatch. Supports regex-based exclusion of paths.

   .. code-block:: python

      def test_example(deep_compare):
          actual = {"a": 1, "b": {"c": 3}}
          expected = {"a": 1, "b": {"c": 3}}
          deep_compare(expected, actual)

          # Exclude specific fields from comparison
          deep_compare(
              expected, actual,
              exclude_regexes=r"\['(timestamp|hash)'\]"
          )

``dev_data_compare(expected, actual, additional_regexes=None)``
   Specialized comparison for device data. Automatically excludes fields that vary between runs: ``directory``, ``path``, ``owner``, ``group``, ``created``, ``mtime``, and ``local_path``. You can pass additional regex patterns to exclude more fields.

   .. code-block:: python

      def test_parse_device(dev_data_compare, json_data):
          expected = json_data("expected_device-data-full.json")
          parsed = MyDevice.parse(source_file)
          dev_data_compare(expected, parsed.export(include_original=True))

          # Exclude additional fields
          dev_data_compare(
              expected, actual,
              additional_regexes=r"\['(serial_number|uptime)'\]"
          )

``assert_glob_path(out_dir, glob_str)``
   Verifies that exactly **one** file matches the glob pattern in the given directory, that the file exists, has non-zero size, and (for JSON files) is valid JSON. Returns the path to the matched file.

   .. code-block:: python

      def test_output_files(assert_glob_path, tmp_path):
          # ... run parsing that produces output ...
          path = assert_glob_path(tmp_path / "devices" / "mydevice", "device-data-full.json")
          assert path.is_file()

``assert_no_warns(caplog)`` / ``assert_no_errors(caplog)`` / ``assert_no_criticals(caplog)``
   Log-level assertion helpers. Call them at the end of a test to verify no unexpected log messages were emitted.

   - ``assert_no_warns()``: Fails if WARNING, ERROR, or CRITICAL appear in logs
   - ``assert_no_errors()``: Fails if ERROR or CRITICAL appear in logs
   - ``assert_no_criticals()``: Fails if CRITICAL appears in logs

   .. code-block:: python

      def test_example(mocker, tmp_path, assert_no_errors):
          # ... test logic ...
          assert_no_errors()

``assert_meta_files(run_dir=None)``
   Verifies that standard PEAT metadata files were created during a run: ``peat.log``, ``json-log.jsonl``, ``debug-info.txt``, ``peat_configuration.yaml``, and ``peat_state.yaml``.


CLI execution fixtures
----------------------

``run_peat(args, shell=False)``
   Executes PEAT via the CLI and returns a tuple of ``(stdout, stderr)`` as decoded strings. **Asserts** that the return code is 0 (will fail if PEAT exits with an error).

   .. code-block:: python

      @pytest.mark.slow
      def test_cli_parse(run_peat, tmp_path):
          stdout, stderr = run_peat([
              "parse", "-q", "--print-results",
              "-o", tmp_path.as_posix(),
              "-d", "mydevice",
              "--", "/path/to/input/file",
          ])
          results = json.loads(stdout)

``exec_peat(args, shell=False, pre_cmd=None)``
   Executes PEAT via the CLI and returns a ``subprocess.CompletedProcess`` object. Does **not** assert the return code, so you can test error conditions.

   .. code-block:: python

      @pytest.mark.slow
      def test_cli_error(exec_peat):
          result = exec_peat(["parse", "--", "nonexistent_file"])
          assert result.returncode != 0


Utility fixtures
----------------

``tmp_path``
   Built-in pytest fixture providing a temporary directory unique to each test. Use this for output directories to keep tests isolated.

``mocker``
   Provided by `pytest-mock <https://pytest-mock.readthedocs.io/>`_. Used extensively for patching config and isolating tests. See :ref:`mocking-patterns`.

``caplog``
   Built-in pytest fixture for capturing log output. Used with the ``assert_no_*`` fixtures.

``win_or_wsl``
   Boolean; ``True`` if running on Windows or WSL.


.. _mocking-patterns:

Mocking patterns
================
Proper mocking is critical to writing isolated, reliable tests. Here are the common patterns used throughout the PEAT test suite.


Patching configuration
----------------------
PEAT's global configuration is stored in a dict-like ``config`` object. Always patch it so your test doesn't affect other tests or write to real output directories:

.. code-block:: python

   from peat import config

   def test_with_config(mocker, tmp_path):
       mocker.patch.dict(
           config["CONFIG"],
           {
               "DEVICE_DIR": tmp_path / "devices",
               "TEMP_DIR": tmp_path / "temp",
               "RUN_DIR": tmp_path,
               "SUMMARIES_DIR": tmp_path / "summaries",
           },
       )

The most commonly patched config values are:

- ``DEVICE_DIR`` — where device output goes (almost always needs patching)
- ``TEMP_DIR`` — temporary file storage
- ``RUN_DIR`` — base run directory
- ``SUMMARIES_DIR`` — summary output
- ``ELASTIC_DIR`` — Elasticsearch output
- ``DEBUG`` — debug level (0-3)
- ``VERBOSE`` — verbose output toggle


Isolating the datastore
-----------------------
The datastore holds discovered device objects and is shared globally. Always isolate it:

.. code-block:: python

   from peat import datastore

   def test_isolated(mocker):
       mocker.patch.object(datastore, "objects", [])


Patching state
--------------
Some tests need to check or manipulate PEAT's runtime state:

.. code-block:: python

   from peat import state

   def test_with_state(mocker):
       mocker.patch.dict(state["CONFIG"], {"error": False})


Mocking external dependencies
------------------------------
When testing protocol classes (SSH, HTTP, Telnet, etc.), mock the underlying libraries so tests don't make real network connections:

.. code-block:: python

   def test_ssh_connection(mocker):
       mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
       mock_client = mocker.MagicMock()
       mock_client_cls.return_value = mock_client

       ssh = SSH("192.0.2.1")
       # Test behavior without making real connections


Mocking module management
--------------------------
When testing module import and loading:

.. code-block:: python

   from peat import module_api

   def test_module_loading(mocker):
       mocker.patch.object(module_api, "modules", {})
       mocker.patch.object(module_api, "module_aliases", {})
       mocker.patch.object(module_api, "runtime_imports", set())
       mocker.patch.object(module_api, "runtime_paths", set())


Writing device module tests
===========================
Device module tests follow a consistent pattern: load input data, run the module's parser, and compare the output against expected (golden) data.


Setting up test data
--------------------
1. Create a ``data_files/`` directory next to your test file:

   .. code-block:: text

      tests/modules/myvendor/
      ├── data_files/
      │   ├── sample_device_output.bin       # Input to the parser
      │   ├── sample_device_output_expected_device-data-full.json
      │   └── sample_device_output_expected_device-data-summary.json
      └── test_my_device.py

2. The expected output JSON files can be generated using the ``generate_test_data_files.py`` script (see :ref:`regenerating-test-data`).


Complete device module test
---------------------------

.. code-block:: python

   import filecmp

   import pytest

   from peat import config, datastore
   from peat.modules.myvendor.my_device import MyDevice


   @pytest.mark.parametrize("input_filename", [
       "device_output_v1.bin",
       "device_output_v2.bin",
       "device_output_edge_case.bin",
   ])
   def test_parse_my_device(
       json_data,
       tmp_path,
       mocker,
       datapath,
       dev_data_compare,
       assert_glob_path,
       input_filename,
       caplog,
   ):
       mocker.patch.dict(
           config["CONFIG"],
           {
               "DEVICE_DIR": tmp_path / "devices",
               "TEMP_DIR": tmp_path / "temp",
           },
       )
       mocker.patch.object(datastore, "objects", [])

       source_path = datapath(input_filename)
       parsed_device = MyDevice.parse(source_path)

       # Compare summary output
       exported_summary = parsed_device.export_summary()
       dev_data_compare(
           json_data(f"{source_path.stem}_expected_device-data-summary.json"),
           exported_summary,
       )

       # Compare full output
       exported_full = parsed_device.export(include_original=True)
       dev_data_compare(
           json_data(f"{source_path.stem}_expected_device-data-full.json"),
           exported_full,
       )

       # Verify source file was copied to output
       assert filecmp.cmp(parsed_device._out_dir / source_path.name, source_path)

       # Verify output files were generated
       assert_glob_path(parsed_device._out_dir, "device-data-summary.json")
       assert_glob_path(parsed_device._out_dir, "device-data-full.json")

       # Verify no errors in logs
       assert "ERROR" not in caplog.text
       assert "CRITICAL" not in caplog.text


Key points:

- Use ``@pytest.mark.parametrize`` to test multiple input files with the same test logic
- Always patch ``DEVICE_DIR`` and ``TEMP_DIR`` to ``tmp_path``
- Always clear ``datastore.objects`` to prevent cross-test interference
- Use ``dev_data_compare`` instead of ``==`` for device data (it ignores timestamps, paths, etc.)
- Check log output for unexpected errors at the end


Writing parser tests
====================
Parser tests validate that raw text or binary data is correctly parsed into structured output.

.. code-block:: python

   from peat import DeviceData, config
   from peat.parsing import command_parsers


   def test_parse_my_command(text_data, json_data, mocker, tmp_path, assert_no_errors):
       mocker.patch.dict(config["CONFIG"], {"DEVICE_DIR": tmp_path})

       # Test empty input returns empty result
       assert command_parsers.MyParser.parse("") == {}

       # Test parsing produces expected output
       input_data = text_data("my_command_output.txt")
       results = command_parsers.MyParser.parse(input_data)
       expected = json_data("expected_my_command_output.json")
       assert results == expected

       # Test that process() populates DeviceData correctly
       dev = DeviceData(id="test_my_parser")
       assert command_parsers.MyParser.parse_and_process(input_data, dev)
       assert dev.extra["my_command"] == expected

       assert_no_errors()

The pattern is:

1. Test empty/edge-case inputs first
2. Parse real input and compare against expected JSON
3. Test that ``process()`` correctly populates ``DeviceData`` fields
4. Assert no errors in logs


Writing protocol tests
======================
Protocol tests validate the behavior of protocol wrapper classes (SSH, HTTP, Telnet, etc.). These tests should mock the underlying network libraries.

.. code-block:: python

   import pytest

   from peat.protocols.ssh import SSH


   class TestSSHInit:
       def test_defaults(self, mocker):
           mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
           ssh = SSH("192.0.2.1")
           assert ssh.ip == "192.0.2.1"
           assert ssh.port == 22
           assert ssh.timeout == 5.0
           assert ssh.connected is False

       def test_custom_port(self, mocker):
           mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
           ssh = SSH("192.0.2.1", port=2222, timeout=10.0)
           assert ssh.port == 2222
           assert ssh.timeout == 10.0


   class TestSSHContextManager:
       def test_enter_exit(self, mocker):
           mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
           ssh = SSH("192.0.2.1")
           assert ssh.__enter__() is ssh
           ssh.__exit__(None, None, None)


Key points:

- Always mock the underlying library (``paramiko``, ``requests``, etc.)
- Group related tests in classes for organization
- Test both success paths and error handling


Writing CLI tests
=================
CLI tests invoke PEAT as a subprocess and verify the output. These are integration tests and should be marked as slow:

.. code-block:: python

   import json

   import pytest


   @pytest.mark.slow
   def test_cli_parse_my_device(run_peat, tmp_path, example_module_file):
       args = [
           "parse",
           "-q",
           "--print-results",
           "-o", tmp_path.as_posix(),
           "-d", "MyDevice",
           "--",
           example_module_file("sample_output.json").as_posix(),
       ]

       stdout, stderr = run_peat(args)
       results = json.loads(stdout)["parse_results"][0]["results"]
       assert results["name"] == "expected_name"


.. _regenerating-test-data:

Regenerating expected test data
===============================
When a module's output format changes (e.g. new fields added, parsing improvements), the expected output files need to be regenerated. PEAT provides a script for this:

.. code-block:: bash

   # Regenerate expected files for a specific module
   pdm run python tests/generate_test_data_files.py SELRelay

   # Regenerate all expected files
   pdm run python tests/generate_test_data_files.py all

To add your module to the generator, create a subclass of ``TestDataGenerator`` in ``tests/generate_test_data_files.py``:

.. code-block:: python

   class MyDeviceGenerator(TestDataGenerator):
       input_paths = ["./tests/modules/myvendor/data_files/"]
       input_globs = ["*.bin"]  # Glob patterns for input files
       file_types = [           # Output files to capture
           "device-data-full.json",
           "device-data-summary.json",
       ]

The generator runs ``peat parse`` on each input file and captures the specified output file types as the new expected output.


.. _deep-diff-output:

Understanding test failures
===========================
When a ``deep_compare`` or ``dev_data_compare`` assertion fails, pytest will display a detailed diff showing:

- **Items CHANGED**: Fields where the expected and actual values differ
- **Items REMOVED**: Fields present in expected but missing in actual
- **Items ADDED**: Fields present in actual but not in expected

This is powered by a custom ``pytest_assertrepr_compare`` hook in ``conftest.py`` that pretty-prints ``DeepDiff`` results.

If a test fails in CI but passes locally, common causes include:

- **Line endings**: Ensure input files have their line endings set in ``.gitattributes`` (``eol=lf`` or ``eol=crlf``). Without this, line endings vary by platform and affect file hashes.
- **Stale expected data**: The module's output may have changed. Regenerate expected files (see :ref:`regenerating-test-data`).
- **Timestamp or path differences**: Use ``dev_data_compare`` which automatically excludes these fields.


Best practices
==============

1. **Always isolate config and datastore.** Patch ``config["CONFIG"]`` and ``datastore.objects`` in every test that touches device data or file I/O.

2. **Use ``tmp_path`` for all output.** Never write to real output directories during tests.

3. **Test edge cases first.** Start tests by verifying behavior with empty input, missing data, or malformed input before testing the "happy path".

4. **Use parametrize for multiple inputs.** When testing the same logic against multiple input files, use ``@pytest.mark.parametrize`` rather than duplicating the test body.

5. **Check logs at the end.** Use ``assert_no_errors()`` or check ``caplog.text`` directly to catch unexpected errors.

6. **Mark slow tests.** Integration tests and CLI tests should use ``@pytest.mark.slow`` so they can be skipped during rapid development.

7. **Name expected files consistently.** Follow the convention ``<input_stem>_expected_<output_type>.json`` so the data fixtures and generators work correctly.

8. **Don't mock what you're testing.** Mock external dependencies (network, filesystem, config) but let the code under test run for real.

9. **Keep test data minimal.** Include only enough data in ``data_files/`` to exercise the code paths you're testing. Large files slow down the test suite and increase repo size.

10. **Update expected data when output changes.** If you change a module's output format, regenerate the expected test data and commit it alongside your code changes.


Environment variables
=====================
The test framework automatically sets these environment variables to ensure consistent test behavior:

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Variable
     - Value
     - Purpose
   * - ``PEAT_NO_LOGO``
     - ``true``
     - Suppress ASCII art logo in output
   * - ``PEAT_NO_COLOR``
     - ``true``
     - Disable colored output
   * - ``PEAT_RESOLVE_MAC``
     - ``false``
     - Don't resolve MAC addresses
   * - ``PEAT_RESOLVE_IP``
     - ``false``
     - Don't resolve IP addresses
   * - ``PEAT_RESOLVE_HOSTNAME``
     - ``false``
     - Don't resolve hostnames

These are set at import time in ``conftest.py`` so tests don't depend on network resources or host-specific state.


Checklist for adding tests to a new module
==========================================
Use this checklist when creating tests for a new PEAT device module:

.. code-block:: text

   [ ] Create test file: tests/modules/<vendor>/test_<module>.py
   [ ] Create data directory: tests/modules/<vendor>/data_files/
   [ ] Add sample input files to data_files/
   [ ] Generate expected output files (generate_test_data_files.py or manually)
   [ ] Write parse test(s) with dev_data_compare
   [ ] Verify output files are generated (assert_glob_path)
   [ ] Check for errors in logs (assert_no_errors or caplog)
   [ ] Add test data generator class to generate_test_data_files.py
   [ ] Mark integration/CLI tests with @pytest.mark.slow
   [ ] Run full test suite to confirm no regressions
