"""Tests for TailscaleManager class."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

from zansoc_cli.tailscale_manager import (
    TailscaleManager, TailscaleResult, TailscaleStatus, TailscaleDevice
)
from zansoc_cli.platform_utils import PlatformUtils, PlatformType, Architecture, SystemInfo


class TestTailscaleManager:
    """Test cases for TailscaleManager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create mock platform utils
        self.mock_platform_utils = Mock(spec=PlatformUtils)
        
        # Mock system info
        self.mock_system_info = SystemInfo(
            platform=PlatformType.LINUX,
            architecture=Architecture.X86_64,
            os_name="Linux",
            os_version="5.4.0",
            python_version="3.9.0",
            cpu_count=4,
            memory_total=8.0,
            disk_free=100.0,
            hostname="test-host",
            username="testuser"
        )
        
        self.mock_platform_utils.get_system_info.return_value = self.mock_system_info
        
        # Initialize Tailscale manager with mocked platform utils
        self.tailscale_manager = TailscaleManager(self.mock_platform_utils)
    
    def test_initialization(self):
        """Test Tailscale manager initialization."""
        assert self.tailscale_manager.platform_utils == self.mock_platform_utils
        assert self.tailscale_manager.system_info == self.mock_system_info
        assert self.tailscale_manager.auth_key is None
        assert self.tailscale_manager.tailscale_binary is None
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_version')
    def test_install_tailscale_already_installed(self, mock_get_version, mock_is_installed):
        """Test Tailscale installation when already installed."""
        mock_is_installed.return_value = True
        mock_get_version.return_value = "1.88.1"
        
        result = self.tailscale_manager.install_tailscale("test-auth-key")
        
        assert isinstance(result, TailscaleResult)
        assert result.success is True
        assert result.status == TailscaleStatus.INSTALLED
        assert "already installed" in result.message
        assert result.execution_time > 0
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._install_tailscale_primary')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_version')
    def test_install_tailscale_success_primary(self, mock_get_version, mock_install_primary, mock_is_installed):
        """Test successful Tailscale installation using primary method."""
        mock_is_installed.side_effect = [False, True]  # Not installed, then installed
        mock_install_primary.return_value = True
        mock_get_version.return_value = "1.88.1"
        
        result = self.tailscale_manager.install_tailscale("test-auth-key")
        
        assert result.success is True
        assert result.status == TailscaleStatus.INSTALLED
        assert "installed successfully" in result.message
        assert self.tailscale_manager.auth_key == "test-auth-key"
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._install_tailscale_primary')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._install_tailscale_arm64_fallback')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_version')
    def test_install_tailscale_success_fallback(self, mock_get_version, mock_install_fallback, 
                                              mock_install_primary, mock_is_installed):
        """Test successful Tailscale installation using ARM64 fallback method."""
        # Set ARM64 architecture
        self.tailscale_manager.system_info.architecture = Architecture.ARM64
        
        # Mock sequence: not installed initially, then installed after fallback
        mock_is_installed.side_effect = [False, True]
        mock_install_primary.return_value = False
        mock_install_fallback.return_value = True
        mock_get_version.return_value = "1.88.1"
        
        result = self.tailscale_manager.install_tailscale("test-auth-key")
        
        assert result.success is True
        assert result.status == TailscaleStatus.INSTALLED
        assert "fallback method" in result.message
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._install_tailscale_primary')
    def test_install_tailscale_failure(self, mock_install_primary, mock_is_installed):
        """Test failed Tailscale installation."""
        mock_is_installed.return_value = False
        mock_install_primary.return_value = False
        
        result = self.tailscale_manager.install_tailscale("test-auth-key")
        
        assert result.success is False
        assert result.status == TailscaleStatus.ERROR
        assert "installation failed" in result.message
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    def test_authenticate_with_key_not_installed(self, mock_is_installed):
        """Test authentication when Tailscale is not installed."""
        mock_is_installed.return_value = False
        
        result = self.tailscale_manager.authenticate_with_key("test-auth-key")
        
        assert result.success is False
        assert result.status == TailscaleStatus.NOT_INSTALLED
        assert "not installed" in result.message
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_status')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager.get_tailscale_ip')
    def test_authenticate_with_key_already_running(self, mock_get_ip, mock_get_status, mock_is_installed):
        """Test authentication when Tailscale is already running."""
        mock_is_installed.return_value = True
        mock_get_status.return_value = TailscaleStatus.RUNNING
        mock_get_ip.return_value = "100.64.0.1"
        
        result = self.tailscale_manager.authenticate_with_key("test-auth-key")
        
        assert result.success is True
        assert result.status == TailscaleStatus.RUNNING
        assert "already authenticated" in result.message
        assert result.ip_address == "100.64.0.1"
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_status')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager.get_tailscale_ip')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager.get_device_info')
    @patch('time.sleep')
    def test_authenticate_with_key_success(self, mock_sleep, mock_get_device_info, mock_get_ip, 
                                         mock_get_command, mock_get_status, mock_is_installed):
        """Test successful authentication with auth key."""
        mock_is_installed.return_value = True
        mock_get_status.side_effect = [TailscaleStatus.NEEDS_LOGIN, TailscaleStatus.RUNNING]
        mock_get_command.return_value = "/usr/bin/tailscale"
        mock_get_ip.return_value = "100.64.0.1"
        mock_get_device_info.return_value = TailscaleDevice(
            id="device123", name="test-host", ip="100.64.0.1", os="linux", online=True
        )
        
        # Mock successful command execution
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.tailscale_manager.authenticate_with_key("test-auth-key")
        
        assert result.success is True
        assert result.status == TailscaleStatus.RUNNING
        assert "authenticated successfully" in result.message
        assert result.ip_address == "100.64.0.1"
        assert result.device_info is not None
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_status')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_authenticate_with_key_command_failure(self, mock_get_command, mock_get_status, mock_is_installed):
        """Test authentication failure due to command execution failure."""
        mock_is_installed.return_value = True
        mock_get_status.return_value = TailscaleStatus.NEEDS_LOGIN
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock failed command execution
        mock_result = Mock()
        mock_result.success = False
        mock_result.stderr = "Authentication failed"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.tailscale_manager.authenticate_with_key("test-auth-key")
        
        assert result.success is False
        assert result.status == TailscaleStatus.ERROR
        assert "authentication failed" in result.message
        assert result.error == "Authentication failed"
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_valid_ip')
    def test_get_tailscale_ip_success(self, mock_is_valid_ip, mock_get_command):
        """Test successful Tailscale IP retrieval."""
        mock_get_command.return_value = "/usr/bin/tailscale"
        mock_is_valid_ip.return_value = True
        
        # Mock successful IP command
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "100.64.0.1\n"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        ip = self.tailscale_manager.get_tailscale_ip()
        
        assert ip == "100.64.0.1"
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_tailscale_ip_failure(self, mock_get_command):
        """Test failed Tailscale IP retrieval."""
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock failed IP command
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        ip = self.tailscale_manager.get_tailscale_ip()
        
        assert ip is None
    
    def test_verify_connectivity_success_linux(self):
        """Test successful connectivity verification on Linux."""
        self.tailscale_manager.system_info.platform = PlatformType.LINUX
        
        # Mock successful ping
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "64 bytes from 100.64.0.2: icmp_seq=1 ttl=64 time=1.23 ms"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.tailscale_manager.verify_connectivity("100.64.0.2")
        
        assert result is True
    
    def test_verify_connectivity_success_windows(self):
        """Test successful connectivity verification on Windows."""
        self.tailscale_manager.system_info.platform = PlatformType.WINDOWS
        
        # Mock successful ping
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "Reply from 100.64.0.2: bytes=32 time=1ms TTL=64"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.tailscale_manager.verify_connectivity("100.64.0.2")
        
        assert result is True
    
    def test_verify_connectivity_failure(self):
        """Test failed connectivity verification."""
        # Mock failed ping
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.tailscale_manager.verify_connectivity("100.64.0.2")
        
        assert result is False
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_device_info_success(self, mock_get_command):
        """Test successful device info retrieval."""
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock JSON status response
        status_data = {
            "Self": {
                "ID": "device123",
                "HostName": "test-host",
                "TailscaleIPs": ["100.64.0.1"],
                "OS": "linux",
                "Online": True,
                "LastSeen": "2023-01-01T12:00:00Z",
                "Tags": ["tag:server"]
            }
        }
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = json.dumps(status_data)
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        device_info = self.tailscale_manager.get_device_info()
        
        assert isinstance(device_info, TailscaleDevice)
        assert device_info.id == "device123"
        assert device_info.name == "test-host"
        assert device_info.ip == "100.64.0.1"
        assert device_info.os == "linux"
        assert device_info.online is True
        assert device_info.tags == ["tag:server"]
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_device_info_failure(self, mock_get_command):
        """Test failed device info retrieval."""
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock failed command
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        device_info = self.tailscale_manager.get_device_info()
        
        assert device_info is None
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_version')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_status')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager.get_tailscale_ip')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager.get_device_info')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_peer_devices')
    def test_get_network_status_complete(self, mock_get_peers, mock_get_device_info, mock_get_ip,
                                       mock_get_status, mock_get_version, mock_is_installed):
        """Test comprehensive network status retrieval."""
        mock_is_installed.return_value = True
        mock_get_version.return_value = "1.88.1"
        mock_get_status.return_value = TailscaleStatus.RUNNING
        mock_get_ip.return_value = "100.64.0.1"
        mock_get_device_info.return_value = TailscaleDevice(
            id="device123", name="test-host", ip="100.64.0.1", os="linux", online=True
        )
        mock_get_peers.return_value = [
            TailscaleDevice(id="peer1", name="peer-host", ip="100.64.0.2", os="linux", online=True)
        ]
        
        status = self.tailscale_manager.get_network_status()
        
        assert status['installed'] is True
        assert status['version'] == "1.88.1"
        assert status['status'] == TailscaleStatus.RUNNING
        assert status['ip_address'] == "100.64.0.1"
        assert status['device_info'] is not None
        assert len(status['peers']) == 1
    
    def test_install_tailscale_primary_unix(self):
        """Test primary Tailscale installation on Unix systems."""
        # Mock successful installation
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.tailscale_manager._install_tailscale_primary()
        
        assert result is True
        # Verify the correct command was called
        self.mock_platform_utils.execute_command.assert_called_with(
            "curl -fsSL https://tailscale.com/install.sh | sh",
            shell=True,
            timeout=300
        )
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._install_tailscale_windows')
    def test_install_tailscale_primary_windows(self, mock_install_windows):
        """Test primary Tailscale installation on Windows."""
        self.tailscale_manager.system_info.platform = PlatformType.WINDOWS
        mock_install_windows.return_value = True
        
        result = self.tailscale_manager._install_tailscale_primary()
        
        assert result is True
        mock_install_windows.assert_called_once()
    
    def test_get_tailscale_command_found(self):
        """Test Tailscale command detection when installed."""
        # Mock successful version check
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        cmd = self.tailscale_manager._get_tailscale_command()
        
        assert cmd == "/usr/bin/tailscale"  # First successful path
        assert self.tailscale_manager.tailscale_binary == "/usr/bin/tailscale"
    
    def test_get_tailscale_command_not_found(self):
        """Test Tailscale command detection when not installed."""
        # Mock failed version checks
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        cmd = self.tailscale_manager._get_tailscale_command()
        
        assert cmd == "tailscale"  # Fallback to PATH
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_tailscale_version_success(self, mock_get_command):
        """Test successful Tailscale version retrieval."""
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock version command output
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "1.88.1-t12345\ntailscaled version: 1.88.1-t12345"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        version = self.tailscale_manager._get_tailscale_version()
        
        assert version == "1.88.1"
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_tailscale_version_failure(self, mock_get_command):
        """Test failed Tailscale version retrieval."""
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock failed version command
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        version = self.tailscale_manager._get_tailscale_version()
        
        assert version is None
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_tailscale_status_running(self, mock_get_command, mock_is_installed):
        """Test Tailscale status detection when running."""
        mock_is_installed.return_value = True
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock status command output
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "100.64.0.1    test-host    linux   online"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        status = self.tailscale_manager._get_tailscale_status()
        
        assert status == TailscaleStatus.RUNNING
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._get_tailscale_command')
    def test_get_tailscale_status_needs_login(self, mock_get_command, mock_is_installed):
        """Test Tailscale status detection when needs login."""
        mock_is_installed.return_value = True
        mock_get_command.return_value = "/usr/bin/tailscale"
        
        # Mock status command output
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "Logged out. Run 'tailscale up' to log in."
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        status = self.tailscale_manager._get_tailscale_status()
        
        assert status == TailscaleStatus.NEEDS_LOGIN
    
    @patch('zansoc_cli.tailscale_manager.TailscaleManager._is_tailscale_installed')
    def test_get_tailscale_status_not_installed(self, mock_is_installed):
        """Test Tailscale status detection when not installed."""
        mock_is_installed.return_value = False
        
        status = self.tailscale_manager._get_tailscale_status()
        
        assert status == TailscaleStatus.NOT_INSTALLED
    
    def test_is_valid_ip_valid(self):
        """Test IP address validation with valid IPs."""
        valid_ips = ["192.168.1.1", "100.64.0.1", "10.0.0.1", "127.0.0.1"]
        
        for ip in valid_ips:
            assert self.tailscale_manager._is_valid_ip(ip) is True
    
    def test_is_valid_ip_invalid(self):
        """Test IP address validation with invalid IPs."""
        invalid_ips = ["256.256.256.256", "not.an.ip", "", "192.168.1"]
        
        for ip in invalid_ips:
            assert self.tailscale_manager._is_valid_ip(ip) is False