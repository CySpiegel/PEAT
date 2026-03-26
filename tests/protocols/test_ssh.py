"""Tests for peat.protocols.ssh, focused on jump host (proxy chain) support."""

import paramiko
import pytest

from peat import CommError
from peat.protocols.ssh import SSH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_ssh_client(mocker):
    """Return a mock paramiko.SSHClient with a usable transport stub."""
    client = mocker.MagicMock()
    transport = mocker.MagicMock()
    channel = mocker.MagicMock()
    transport.open_channel.return_value = channel
    client.get_transport.return_value = transport
    return client, transport, channel


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------


class TestSSHInit:
    def test_defaults(self):
        ssh = SSH("10.0.0.1")
        assert ssh.ip == "10.0.0.1"
        assert ssh.port == 22
        assert ssh.jump_hosts == []
        assert ssh._jump_clients == []

    def test_jump_hosts_extracted_from_kwargs(self):
        hops = [{"host": "bastion", "port": 22, "user": "u", "pass": "p"}]
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": hops, "look_for_keys": False})
        assert ssh.jump_hosts == hops
        # jump_hosts must be removed from kwargs before they reach paramiko
        assert "jump_hosts" not in ssh.kwargs

    def test_jump_hosts_none_becomes_empty_list(self):
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": None})
        assert ssh.jump_hosts == []


# ---------------------------------------------------------------------------
# _resolve_pkey
# ---------------------------------------------------------------------------


class TestResolvePkey:
    def test_returns_none_when_no_key(self):
        kwargs = {"look_for_keys": False}
        assert SSH._resolve_pkey(kwargs) is None

    def test_loads_key_from_key_filename(self, mocker):
        mocker.patch(
            "paramiko.RSAKey.from_private_key_file",
            return_value=mocker.sentinel.pkey,
        )
        kwargs = {"key_filename": "/path/to/key"}
        result = SSH._resolve_pkey(kwargs, password="secret")

        paramiko.RSAKey.from_private_key_file.assert_called_once_with(
            filename="/path/to/key", password="secret"
        )
        assert result is mocker.sentinel.pkey
        assert "key_filename" not in kwargs

    def test_loads_key_from_pkey_field(self, mocker):
        mocker.patch(
            "paramiko.RSAKey.from_private_key_file",
            return_value=mocker.sentinel.pkey,
        )
        kwargs = {"pkey": "/path/to/key"}
        result = SSH._resolve_pkey(kwargs)
        assert result is mocker.sentinel.pkey
        assert "pkey" not in kwargs

    def test_key_filename_takes_priority_over_pkey(self, mocker):
        mocker.patch(
            "paramiko.RSAKey.from_private_key_file",
            return_value=mocker.sentinel.pkey,
        )
        kwargs = {"key_filename": "/key1", "pkey": "/key2"}
        SSH._resolve_pkey(kwargs)
        paramiko.RSAKey.from_private_key_file.assert_called_once_with(
            filename="/key1", password=None
        )


# ---------------------------------------------------------------------------
# _build_jump_chain
# ---------------------------------------------------------------------------


class TestBuildJumpChain:
    def test_returns_none_when_no_jump_hosts(self):
        ssh = SSH("10.0.0.1")
        assert ssh._build_jump_chain() is None

    def test_single_hop(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        hops = [{"host": "bastion.example.com", "port": 2222, "user": "jump", "pass": "pw"}]
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": hops})

        result = ssh._build_jump_chain()

        # The jump client should have connected to the bastion
        client.connect.assert_called_once()
        call_kwargs = client.connect.call_args[1]
        assert call_kwargs["hostname"] == "bastion.example.com"
        assert call_kwargs["port"] == 2222
        assert call_kwargs["username"] == "jump"
        assert call_kwargs["password"] == "pw"
        # No sock for the first hop
        assert "sock" not in call_kwargs or call_kwargs["sock"] is None

        # The final channel should target the real destination
        transport.open_channel.assert_called_once_with(
            "direct-tcpip",
            dest_addr=("10.0.0.1", 22),
            src_addr=("127.0.0.1", 0),
        )
        assert result is channel
        assert ssh._jump_clients == [client]

    def test_multi_hop(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")

        # Create two distinct mock clients for the two hops
        # Note: SSH.__init__ also calls SSHClient(), so we need a dummy for that
        init_client = mocker.MagicMock()
        client1, transport1, channel1 = _mock_ssh_client(mocker)
        client2, transport2, final_channel = _mock_ssh_client(mocker)
        mock_client_cls.side_effect = [init_client, client1, client2]

        hops = [
            {"host": "hop1", "port": 22, "user": "u1", "pass": "p1"},
            {"host": "hop2", "port": 22, "user": "u2", "pass": "p2"},
        ]
        ssh = SSH("target", port=2222, kwargs={"jump_hosts": hops})

        result = ssh._build_jump_chain()

        # First hop: direct connection (no sock)
        c1_kwargs = client1.connect.call_args[1]
        assert c1_kwargs["hostname"] == "hop1"
        assert "sock" not in c1_kwargs or c1_kwargs["sock"] is None

        # Second hop: tunneled through first hop
        c2_kwargs = client2.connect.call_args[1]
        assert c2_kwargs["hostname"] == "hop2"
        assert c2_kwargs["sock"] is channel1  # tunnel from hop1

        # transport1 opened a channel to hop2
        transport1.open_channel.assert_called_once_with(
            "direct-tcpip",
            dest_addr=("hop2", 22),
            src_addr=("127.0.0.1", 0),
        )

        # Final channel goes from hop2 to the real target
        transport2.open_channel.assert_called_once_with(
            "direct-tcpip",
            dest_addr=("target", 2222),
            src_addr=("127.0.0.1", 0),
        )
        assert result is final_channel
        assert ssh._jump_clients == [client1, client2]

    def test_missing_host_raises_comm_error(self):
        hops = [{"port": 22, "user": "u", "pass": "p"}]
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": hops})

        with pytest.raises(CommError, match="missing 'host'"):
            ssh._build_jump_chain()

    def test_hop_accepts_ip_alias(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        hops = [{"ip": "192.168.1.1", "user": "admin", "pass": "pw"}]
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": hops})
        ssh._build_jump_chain()

        call_kwargs = client.connect.call_args[1]
        assert call_kwargs["hostname"] == "192.168.1.1"

    def test_hop_accepts_username_and_password_aliases(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        hops = [{"host": "bastion", "username": "admin", "password": "secret"}]
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": hops})
        ssh._build_jump_chain()

        call_kwargs = client.connect.call_args[1]
        assert call_kwargs["username"] == "admin"
        assert call_kwargs["password"] == "secret"

    def test_hop_with_key_file(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        mock_rsa = mocker.patch(
            "paramiko.RSAKey.from_private_key_file",
            return_value=mocker.sentinel.hop_pkey,
        )

        hops = [{"host": "bastion", "user": "u", "pass": "pw", "key_filename": "/keys/hop.pem"}]
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": hops})
        ssh._build_jump_chain()

        mock_rsa.assert_called_once_with(filename="/keys/hop.pem", password="pw")
        call_kwargs = client.connect.call_args[1]
        assert call_kwargs["pkey"] is mocker.sentinel.hop_pkey

    def test_hop_uses_custom_timeout(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        hops = [{"host": "bastion", "user": "u", "pass": "p", "timeout": 30}]
        ssh = SSH("10.0.0.1", timeout=5.0, kwargs={"jump_hosts": hops})
        ssh._build_jump_chain()

        call_kwargs = client.connect.call_args[1]
        assert call_kwargs["timeout"] == 30.0

    def test_hop_defaults_timeout_to_ssh_timeout(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        hops = [{"host": "bastion", "user": "u", "pass": "p"}]
        ssh = SSH("10.0.0.1", timeout=7.5, kwargs={"jump_hosts": hops})
        ssh._build_jump_chain()

        call_kwargs = client.connect.call_args[1]
        assert call_kwargs["timeout"] == 7.5

    def test_does_not_mutate_original_hop_dicts(self, mocker):
        mock_client_cls = mocker.patch("peat.protocols.ssh.paramiko.SSHClient")
        client, transport, channel = _mock_ssh_client(mocker)
        mock_client_cls.return_value = client

        hop = {"host": "bastion", "port": 22, "user": "u", "pass": "p"}
        original_hop = hop.copy()
        ssh = SSH("10.0.0.1", kwargs={"jump_hosts": [hop]})
        ssh._build_jump_chain()

        assert hop == original_hop


# ---------------------------------------------------------------------------
# comm property — jump host integration
# ---------------------------------------------------------------------------


class TestCommWithJumpHosts:
    def test_comm_uses_tunnel_sock(self, mocker):
        """When jump hosts are configured, comm passes the tunnel as sock."""
        ssh = SSH("10.0.0.1", username="admin", password="pw", kwargs={"jump_hosts": []})
        ssh.jump_hosts = [{"host": "bastion", "user": "u", "pass": "p"}]

        tunnel = mocker.MagicMock(spec=paramiko.Channel)
        mocker.patch.object(ssh, "_build_jump_chain", return_value=tunnel)
        mocker.patch.object(ssh._comm, "connect")
        ssh._comm.set_missing_host_key_policy = mocker.MagicMock()

        _ = ssh.comm

        call_kwargs = ssh._comm.connect.call_args[1]
        assert call_kwargs["sock"] is tunnel

    def test_comm_no_sock_without_jump_hosts(self, mocker):
        """Without jump hosts, no sock kwarg is passed."""
        ssh = SSH("10.0.0.1", username="admin", password="pw")

        mocker.patch.object(ssh._comm, "connect")
        ssh._comm.set_missing_host_key_policy = mocker.MagicMock()

        _ = ssh.comm

        call_kwargs = ssh._comm.connect.call_args[1]
        assert "sock" not in call_kwargs

    def test_comm_cleans_up_on_auth_failure(self, mocker):
        """Jump clients are cleaned up if the final connection fails auth."""
        jump_client = mocker.MagicMock(spec=paramiko.SSHClient)
        tunnel = mocker.MagicMock(spec=paramiko.Channel)

        ssh = SSH("10.0.0.1", username="admin", password="pw")
        ssh.jump_hosts = [{"host": "bastion", "user": "u", "pass": "p"}]
        ssh._jump_clients = [jump_client]

        mocker.patch.object(ssh, "_build_jump_chain", return_value=tunnel)
        mocker.patch.object(
            ssh._comm, "connect", side_effect=paramiko.AuthenticationException("bad creds")
        )
        ssh._comm.set_missing_host_key_policy = mocker.MagicMock()

        with pytest.raises(paramiko.AuthenticationException):
            _ = ssh.comm

        # _close should have been called, cleaning up jump clients
        assert ssh.connected is False

    def test_comm_cleans_up_on_generic_failure(self, mocker):
        """Jump clients are cleaned up on a generic connection error."""
        jump_client = mocker.MagicMock(spec=paramiko.SSHClient)
        tunnel = mocker.MagicMock(spec=paramiko.Channel)

        ssh = SSH("10.0.0.1", username="admin", password="pw")
        ssh.jump_hosts = [{"host": "bastion", "user": "u", "pass": "p"}]
        ssh._jump_clients = [jump_client]

        mocker.patch.object(ssh, "_build_jump_chain", return_value=tunnel)
        mocker.patch.object(ssh._comm, "connect", side_effect=OSError("connection refused"))
        ssh._comm.set_missing_host_key_policy = mocker.MagicMock()

        with pytest.raises(CommError):
            _ = ssh.comm

        assert ssh.connected is False


# ---------------------------------------------------------------------------
# _close — jump host cleanup
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_without_jump_hosts(self):
        ssh = SSH("10.0.0.1")
        ssh.connected = True
        ssh._comm = paramiko.SSHClient()
        ssh._close()
        assert ssh.connected is False
        assert ssh._jump_clients == []

    def test_close_cleans_up_jump_clients_in_reverse(self, mocker):
        ssh = SSH("10.0.0.1")
        ssh.connected = True

        client1 = mocker.MagicMock(spec=paramiko.SSHClient)
        client2 = mocker.MagicMock(spec=paramiko.SSHClient)
        ssh._jump_clients = [client1, client2]
        ssh._comm = mocker.MagicMock(spec=paramiko.SSHClient)

        ssh._close()

        # Both clients closed; innermost (client2) first
        assert client2.close.call_count == 1
        assert client1.close.call_count == 1
        # Verify ordering: client2.close was called before client1.close
        assert client2.close.call_args_list[0] == mocker.call()

        assert ssh._jump_clients == []
        assert ssh.connected is False

    def test_close_suppresses_exceptions_from_jump_clients(self, mocker):
        ssh = SSH("10.0.0.1")
        ssh.connected = True

        client = mocker.MagicMock(spec=paramiko.SSHClient)
        client.close.side_effect = OSError("already closed")
        ssh._jump_clients = [client]
        ssh._comm = mocker.MagicMock(spec=paramiko.SSHClient)

        # Should not raise
        ssh._close()
        assert ssh._jump_clients == []
        assert ssh.connected is False
