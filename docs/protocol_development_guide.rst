Protocol Development Guide: Adding New Protocol Support to PEAT
=================================================================

This guide walks through adding a new communication protocol to PEAT —
from understanding the existing patterns to a fully tested, integrated
protocol class.


Overview
--------

PEAT protocols live in ``peat/protocols/`` and provide reusable
communication classes that device modules use to talk to devices.
Each protocol class wraps a lower-level library and adds:

- Consistent constructor interface (``ip``, ``port``, ``timeout``)
- Context manager support (``with`` statements)
- Logging via loguru
- Error handling with ``CommError``
- Connection state tracking
- Output recording for debugging

Existing protocols:

.. list-table::
   :header-rows: 1
   :widths: 15 15 20 50

   * - Class
     - File
     - Wraps
     - Purpose
   * - ``HTTP``
     - ``http.py``
     - ``requests.Session``
     - REST APIs, web pages, file downloads
   * - ``SSH``
     - ``ssh.py``
     - ``paramiko``
     - Secure shell command execution
   * - ``Telnet``
     - ``telnet.py``
     - ``telnetlib``
     - Legacy device CLI access
   * - ``FTP``
     - ``ftp.py``
     - ``ftplib``
     - File transfer
   * - ``SNMP``
     - ``snmp.py``
     - ``pysnmp``
     - SNMP GET/WALK queries
   * - ``Serial``
     - ``serial.py``
     - ``pyserial``
     - RS-232/serial connections


Step-by-Step: Adding a New Protocol
-------------------------------------

This example adds a fictional "MQTT" protocol.

Step 1: Create the protocol file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``peat/protocols/mqtt.py``:

.. code-block:: python

   """
   MQTT protocol support for PEAT.

   Provides publish/subscribe functionality for device modules
   that communicate via MQTT brokers.
   """

   import traceback
   from typing import Any

   import paho.mqtt.client as mqtt_client  # The underlying library

   import peat  # Avoid circular imports
   from peat import CommError, log


   class MQTT:
       """
       MQTT client for interacting with devices via MQTT brokers.

       Usage:

       .. code-block:: python

          with MQTT("192.168.1.100", port=1883) as client:
              client.subscribe("device/status")
              messages = client.read(timeout=5.0)

       Args:
           ip: IP address of the MQTT broker
           port: TCP port (default 1883, or 8883 for TLS)
           timeout: Connection timeout in seconds
       """

       def __init__(
           self,
           ip: str,
           port: int = 1883,
           timeout: float = 5.0,
       ) -> None:
           self.ip: str = ip
           self.port: int = port
           self.timeout: float = timeout

           # Create a bound logger for this protocol instance.
           # All protocol classes should do this for consistent logging.
           self.log = log.bind(
               classname=self.__class__.__name__,
               target=f"{self.ip}:{self.port}",
           )

           # Connection state tracking
           self.connected: bool = False

           # Store all received messages for debugging/recording
           self.all_output: list[dict[str, Any]] = []

           # Internal client handle (lazy-initialized)
           self._client: mqtt_client.Client | None = None

           self.log.trace(f"Initialized {repr(self)}")

       # --- Context Manager ---
       # All protocol classes MUST support "with" statements.
       # This ensures connections are always cleaned up properly,
       # even if exceptions occur.

       def __enter__(self) -> "MQTT":
           return self

       def __exit__(self, exc_type, exc_val, exc_tb) -> None:
           self.disconnect()
           if exc_type:
               self.log.debug(
                   f"Unhandled exception while exiting - "
                   f"{exc_type.__name__}: {exc_val}"
               )
               self.log.trace(
                   f"Exception traceback\n"
                   f"{''.join(traceback.format_tb(exc_tb))}"
                   f"{exc_type.__name__}: {exc_val}"
               )

       # --- String representations ---

       def __str__(self) -> str:
           return self.ip

       def __repr__(self) -> str:
           return (
               f"{self.__class__.__name__}"
               f"({self.ip}, {self.port}, {self.timeout})"
           )

       # --- Connection Management ---

       def connect(self) -> bool:
           """
           Connect to the MQTT broker.

           Returns:
               True if connection was successful

           Raises:
               CommError: If connection fails
           """
           try:
               self._client = mqtt_client.Client()
               self._client.connect(self.ip, self.port, int(self.timeout))
               self.connected = True
               self.log.info(f"Connected to {self.ip}:{self.port}")
               return True
           except Exception as ex:
               self._client = None
               self.connected = False
               raise CommError(
                   f"Failed to connect to MQTT broker at "
                   f"{self.ip}:{self.port}: {ex}"
               ) from ex

       def disconnect(self) -> None:
           """Disconnect from the MQTT broker."""
           if self._client and self.connected:
               try:
                   self._client.disconnect()
                   self.log.debug(f"Disconnected from {self.ip}:{self.port}")
               except Exception as ex:
                   self.log.debug(f"Error during disconnect: {ex}")
               finally:
                   self._client = None
                   self.connected = False

       # --- Protocol Operations ---

       def subscribe(self, topic: str) -> bool:
           """
           Subscribe to an MQTT topic.

           Args:
               topic: MQTT topic string (e.g. "device/status/#")

           Returns:
               True if subscription was successful
           """
           if not self.connected:
               self.connect()

           try:
               result, mid = self._client.subscribe(topic)
               self.log.debug(f"Subscribed to '{topic}' (mid={mid})")
               return result == mqtt_client.MQTT_ERR_SUCCESS
           except Exception as ex:
               self.log.warning(f"Failed to subscribe to '{topic}': {ex}")
               return False

       def publish(self, topic: str, payload: str | bytes) -> bool:
           """
           Publish a message to an MQTT topic.

           Args:
               topic: MQTT topic string
               payload: Message content

           Returns:
               True if publish was successful
           """
           if not self.connected:
               self.connect()

           try:
               result = self._client.publish(topic, payload)
               self.log.debug(f"Published to '{topic}' ({len(payload)} bytes)")

               # Record the output for debugging
               self.all_output.append({
                   "direction": "publish",
                   "topic": topic,
                   "payload": payload if isinstance(payload, str)
                              else payload.decode("utf-8", errors="replace"),
               })

               return result.rc == mqtt_client.MQTT_ERR_SUCCESS
           except Exception as ex:
               self.log.warning(f"Failed to publish to '{topic}': {ex}")
               return False

The key patterns to follow (visible in all existing protocols):

1. **Constructor:** ``(ip, port, timeout)`` — consistent interface
2. **Bound logger:** ``self.log = log.bind(classname=..., target=...)``
3. **Connection tracking:** ``self.connected`` boolean
4. **Output recording:** ``self.all_output`` list
5. **Context manager:** ``__enter__`` / ``__exit__`` with cleanup
6. **CommError:** raise ``CommError`` (from ``peat``) on connection failures
7. **Lazy connection:** connect on first use, not in ``__init__``

Step 2: Add the dependency (if needed)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your protocol requires an external library, add it to
``pyproject.toml``:

.. code-block:: toml

   [project]
   dependencies = [
       # ... existing dependencies ...
       "paho-mqtt>=1.6.1",
   ]

Then run:

.. code-block:: bash

   pdm lock
   pdm install

Step 3: Register the protocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Export the class from ``peat/protocols/__init__.py``:

.. code-block:: python

   from .mqtt import MQTT

This allows modules to import it as:

.. code-block:: python

   from peat.protocols import MQTT

Step 4: Add default options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your protocol needs configurable options (port, timeout, etc.),
add defaults to the global config. Check
``peat/settings.py`` or ``peat/consts.py`` for how existing protocols
define their defaults:

.. code-block:: python

   # In peat/consts.py or peat/settings.py (follow existing pattern)
   DEFAULT_OPTIONS = {
       # ... existing protocols ...
       "mqtt": {
           "port": 1883,
           "timeout": 10.0,
           "tls": False,
       },
   }

This allows module developers to access settings via
``dev.options["mqtt"]["port"]`` and users to override them in the
PEAT config YAML.

Step 5: Write tests
~~~~~~~~~~~~~~~~~~~~~

Create ``tests/protocols/test_mqtt.py`` (or add to an existing protocol
test file). Protocol tests should cover:

1. **Construction** — verify default values
2. **Connection** — test connect/disconnect lifecycle
3. **Operations** — test the protocol-specific methods
4. **Error handling** — verify CommError is raised appropriately
5. **Context manager** — verify cleanup on exit

.. code-block:: python

   # tests/protocols/test_mqtt.py

   import pytest
   from unittest.mock import MagicMock, patch

   from peat import CommError
   from peat.protocols.mqtt import MQTT


   class TestMQTTConstruction:
       """Test MQTT client initialization."""

       def test_default_port(self):
           client = MQTT("192.168.1.100")
           assert client.ip == "192.168.1.100"
           assert client.port == 1883
           assert client.timeout == 5.0
           assert client.connected is False

       def test_custom_port(self):
           client = MQTT("10.0.0.1", port=8883, timeout=15.0)
           assert client.port == 8883
           assert client.timeout == 15.0

       def test_repr(self):
           client = MQTT("192.168.1.1", 1883, 5.0)
           assert repr(client) == "MQTT(192.168.1.1, 1883, 5.0)"

       def test_str(self):
           client = MQTT("192.168.1.1")
           assert str(client) == "192.168.1.1"


   class TestMQTTConnection:
       """Test MQTT connect/disconnect."""

       @patch("peat.protocols.mqtt.mqtt_client.Client")
       def test_connect_success(self, mock_client_cls):
           client = MQTT("192.168.1.100")
           assert client.connect() is True
           assert client.connected is True

       @patch("peat.protocols.mqtt.mqtt_client.Client")
       def test_connect_failure_raises_commerror(self, mock_client_cls):
           mock_instance = mock_client_cls.return_value
           mock_instance.connect.side_effect = ConnectionRefusedError("refused")

           client = MQTT("192.168.1.100")
           with pytest.raises(CommError):
               client.connect()
           assert client.connected is False

       @patch("peat.protocols.mqtt.mqtt_client.Client")
       def test_disconnect(self, mock_client_cls):
           client = MQTT("192.168.1.100")
           client.connect()
           client.disconnect()
           assert client.connected is False

       @patch("peat.protocols.mqtt.mqtt_client.Client")
       def test_context_manager_cleanup(self, mock_client_cls):
           with MQTT("192.168.1.100") as client:
               client.connect()
               assert client.connected is True
           # After exiting "with", should be disconnected
           assert client.connected is False


   class TestMQTTOperations:
       """Test MQTT publish/subscribe."""

       @patch("peat.protocols.mqtt.mqtt_client.Client")
       def test_publish(self, mock_client_cls):
           mock_instance = mock_client_cls.return_value
           mock_result = MagicMock()
           mock_result.rc = 0  # MQTT_ERR_SUCCESS
           mock_instance.publish.return_value = mock_result

           with MQTT("192.168.1.100") as client:
               client.connect()
               assert client.publish("test/topic", "hello") is True
               assert len(client.all_output) == 1

Step 6: Use the protocol in a module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now modules can use your protocol:

.. code-block:: python

   from peat.protocols import MQTT

   class AcmeIoTSensor(DeviceModule):
       device_type = "Sensor"
       vendor_id = "ACME"
       vendor_name = "ACME Corporation"

       @classmethod
       def _pull(cls, dev: DeviceData) -> bool:
           port = dev.options["mqtt"]["port"]
           timeout = dev.options["mqtt"]["timeout"]

           try:
               with MQTT(dev.ip, port, timeout) as client:
                   client.subscribe("device/config")
                   messages = client.read(timeout=10.0)

                   if not messages:
                       cls.log.warning(f"No MQTT messages from {dev.ip}")
                       return False

                   path = dev.write_file(messages, "mqtt_config.json")
                   cls.parse(path, dev)
                   return True
           except Exception as err:
               cls.log.warning(f"MQTT pull failed for {dev.ip}: {err}")
               return False


Protocol Design Patterns
--------------------------

Lazy Connection
~~~~~~~~~~~~~~~~

Don't connect in ``__init__``. Connect when the first operation is
called. This is the pattern used by ``FTP`` and ``Telnet``:

.. code-block:: python

   @property
   def client(self):
       if not self.connected:
           self.connect()
       return self._client

This allows creating protocol objects without immediately opening
connections, which is important for configuration and testing.

Error Handling
~~~~~~~~~~~~~~~

Use ``CommError`` for connection-level failures. Let application-level
errors propagate as their original exception types:

.. code-block:: python

   from peat import CommError

   def connect(self):
       try:
           self._client.connect(self.ip, self.port)
       except ConnectionRefusedError as ex:
           raise CommError(f"Connection refused: {ex}") from ex

Logging Levels
~~~~~~~~~~~~~~~

Follow the existing logging conventions:

- ``self.log.info()`` — connection established/closed
- ``self.log.debug()`` — individual operations (commands sent, responses)
- ``self.log.warning()`` — recoverable errors
- ``self.log.trace()`` — initialization, detailed debugging

Output Recording
~~~~~~~~~~~~~~~~~

Record all protocol interactions in ``self.all_output``. This is used
for debugging and can be saved to files for analysis:

.. code-block:: python

   # After each operation, record what happened
   self.all_output.append(response_text)

Credential Tracking
~~~~~~~~~~~~~~~~~~~~

If your protocol supports authentication, track successful credentials:

.. code-block:: python

   self.successful_creds: tuple[str, str] | None = None

   def login(self, username: str, password: str) -> bool:
       # ... attempt login ...
       if success:
           self.successful_creds = (username, password)
       return success


Checklist
----------

Before submitting your protocol, verify:

.. code-block:: text

   [ ] Class follows constructor pattern: (ip, port, timeout)
   [ ] Context manager (__enter__ / __exit__) implemented
   [ ] __exit__ handles exceptions gracefully (log, don't re-raise)
   [ ] CommError raised on connection failures
   [ ] Bound logger created in __init__
   [ ] connected attribute tracks state
   [ ] all_output records interactions
   [ ] Exported in peat/protocols/__init__.py
   [ ] Dependency added to pyproject.toml (if external library)
   [ ] Tests cover: construction, connection, operations, errors
   [ ] Works with "with" statements in module code
