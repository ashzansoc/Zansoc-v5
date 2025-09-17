"""Tests for PlatformUtils class."""

import pytest
import os
import tempfile
import shutil
import subprocess
import requests
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from zansoc_cli.platform_utils import (
    PlatformUtils, PlatformType, Architecture, SystemInfo, CommandResult
)


class TestPlatformUtils:
    """Test cases for PlatformUtils."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.platform_utils = PlatformUtils()
    
    def test_initialization(self):
        """Test platform utils initialization."""
        assert self.platform_utils is not None
        assert self.platform_utils._system_info is None
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_detect_platform_linux_x86_64(self, mock_machine, mock_system):
        """Test platform detection for Linux x86_64."""
        mock_system.return_value = 'Linux'
        mock_machine.return_value = 'x86_64'
        
        result = self.platform_utils.detect_platform()
        
        assert result['platform'] == PlatformType.LINUX
        assert result['architecture'] == Architecture.X86_64
        assert result['platform_string'] == 'linux-x86_64'
        assert result['is_linux'] is True
        assert result['is_macos'] is False
        assert result['is_windows'] is False
        assert result['is_x86'] is True
        assert result['is_arm'] is False
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_detect_platform_macos_arm64(self, mock_machine, mock_system):
        """Test platform detection for macOS ARM64."""
        mock_system.return_value = 'Darwin'
        mock_machine.return_value = 'arm64'
        
        result = self.platform_utils.detect_platform()
        
        assert result['platform'] == PlatformType.MACOS
        assert result['architecture'] == Architecture.ARM64
        assert result['platform_string'] == 'darwin-arm64'
        assert result['is_macos'] is True
        assert result['is_linux'] is False
        assert result['is_arm'] is True
        assert result['is_x86'] is False
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_detect_platform_windows_amd64(self, mock_machine, mock_system):
        """Test platform detection for Windows AMD64."""
        mock_system.return_value = 'Windows'
        mock_machine.return_value = 'AMD64'
        
        result = self.platform_utils.detect_platform()
        
        assert result['platform'] == PlatformType.WINDOWS
        assert result['architecture'] == Architecture.X86_64
        assert result['platform_string'] == 'windows-x86_64'
        assert result['is_windows'] is True
        assert result['is_x86'] is True
    
    @patch('platform.system')
    @patch('platform.machine')
    def test_detect_platform_unknown(self, mock_machine, mock_system):
        """Test platform detection for unknown platform."""
        mock_system.return_value = 'UnknownOS'
        mock_machine.return_value = 'unknown_arch'
        
        result = self.platform_utils.detect_platform()
        
        assert result['platform'] == PlatformType.UNKNOWN
        assert result['architecture'] == Architecture.UNKNOWN
        assert result['platform_string'] == 'unknown-unknown'
    
    @patch('platform.system', side_effect=Exception("Platform error"))
    def test_detect_platform_error(self, mock_system):
        """Test platform detection error handling."""
        result = self.platform_utils.detect_platform()
        
        assert result['platform'] == PlatformType.UNKNOWN
        assert result['architecture'] == Architecture.UNKNOWN
        assert 'error' in result
    
    @patch('zansoc_cli.platform_utils.PlatformUtils.detect_platform')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_count')
    @patch('platform.system')
    @patch('platform.release')
    @patch('platform.python_version')
    @patch('platform.node')
    @patch('os.getenv')
    def test_get_system_info(self, mock_getenv, mock_node, mock_python_version,
                           mock_release, mock_system, mock_cpu_count,
                           mock_disk_usage, mock_virtual_memory, mock_detect_platform):
        """Test system information gathering."""
        # Mock platform detection
        mock_detect_platform.return_value = {
            'platform': PlatformType.LINUX,
            'architecture': Architecture.X86_64
        }
        
        # Mock system info
        mock_system.return_value = 'Linux'
        mock_release.return_value = '5.4.0'
        mock_python_version.return_value = '3.9.0'
        mock_node.return_value = 'test-host'
        mock_getenv.side_effect = lambda key, default=None: {
            'USER': 'testuser',
            'USERNAME': None
        }.get(key, default)
        
        # Mock resource info
        mock_cpu_count.return_value = 4
        
        mock_memory = Mock()
        mock_memory.total = 8 * 1024**3  # 8GB
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.free = 100 * 1024**3  # 100GB
        mock_disk_usage.return_value = mock_disk
        
        # Get system info
        system_info = self.platform_utils.get_system_info()
        
        assert isinstance(system_info, SystemInfo)
        assert system_info.platform == PlatformType.LINUX
        assert system_info.architecture == Architecture.X86_64
        assert system_info.os_name == 'Linux'
        assert system_info.os_version == '5.4.0'
        assert system_info.python_version == '3.9.0'
        assert system_info.cpu_count == 4
        assert system_info.memory_total == 8.0
        assert system_info.disk_free == 100.0
        assert system_info.hostname == 'test-host'
        assert system_info.username == 'testuser'
    
    @patch('zansoc_cli.platform_utils.PlatformUtils.get_system_info')
    @patch('zansoc_cli.platform_utils.PlatformUtils._check_internet_connectivity')
    @patch('shutil.which')
    @patch('zansoc_cli.platform_utils.PlatformUtils._check_sudo_access')
    def test_check_prerequisites_all_met(self, mock_sudo, mock_which, mock_internet, mock_system_info):
        """Test prerequisites check when all requirements are met."""
        # Mock system info
        system_info = SystemInfo(
            platform=PlatformType.LINUX,
            architecture=Architecture.X86_64,
            os_name='Linux',
            os_version='5.4.0',
            python_version='3.9.0',
            cpu_count=4,
            memory_total=8.0,
            disk_free=10.0,
            hostname='test-host',
            username='testuser'
        )
        mock_system_info.return_value = system_info
        
        # Mock other checks
        mock_internet.return_value = True
        mock_which.return_value = '/usr/bin/git'  # Commands found
        mock_sudo.return_value = True
        
        missing = self.platform_utils.check_prerequisites()
        
        assert missing == []
    
    @patch('zansoc_cli.platform_utils.PlatformUtils.get_system_info')
    @patch('zansoc_cli.platform_utils.PlatformUtils._check_internet_connectivity')
    @patch('shutil.which')
    def test_check_prerequisites_missing(self, mock_which, mock_internet, mock_system_info):
        """Test prerequisites check with missing requirements."""
        # Mock system info with issues
        system_info = SystemInfo(
            platform=PlatformType.LINUX,
            architecture=Architecture.X86_64,
            os_name='Linux',
            os_version='5.4.0',
            python_version='3.7.0',  # Too old
            cpu_count=4,
            memory_total=0.5,  # Too little memory
            disk_free=1.0,     # Too little disk
            hostname='test-host',
            username='testuser'
        )
        mock_system_info.return_value = system_info
        
        # Mock other checks
        mock_internet.return_value = False  # No internet
        mock_which.return_value = None      # Commands not found
        
        missing = self.platform_utils.check_prerequisites()
        
        assert len(missing) > 0
        assert any('Python 3.8+' in item for item in missing)
        assert any('2GB free disk space' in item for item in missing)
        assert any('1GB RAM' in item for item in missing)
        assert any('Internet connectivity' in item for item in missing)
        assert any("Command 'git'" in item for item in missing)
    
    @patch('subprocess.run')
    def test_execute_command_success(self, mock_run):
        """Test successful command execution."""
        # Mock successful command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'command output'
        mock_result.stderr = ''
        mock_run.return_value = mock_result
        
        result = self.platform_utils.execute_command('echo hello')
        
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout == 'command output'
        assert result.stderr == ''
        assert result.command == 'echo hello'
        assert result.execution_time > 0
    
    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run):
        """Test failed command execution."""
        # Mock failed command
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ''
        mock_result.stderr = 'command error'
        mock_run.return_value = mock_result
        
        result = self.platform_utils.execute_command('false')
        
        assert result.success is False
        assert result.returncode == 1
        assert result.stderr == 'command error'
    
    @patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 5))
    def test_execute_command_timeout(self, mock_run):
        """Test command execution timeout."""
        result = self.platform_utils.execute_command('sleep 10', timeout=5)
        
        assert result.success is False
        assert result.returncode == -1
        assert 'timed out' in result.stderr
    
    @patch('subprocess.run', side_effect=Exception('Command error'))
    def test_execute_command_exception(self, mock_run):
        """Test command execution exception."""
        result = self.platform_utils.execute_command('invalid_command')
        
        assert result.success is False
        assert result.returncode == -1
        assert 'Command error' in result.stderr
    
    @patch('requests.get')
    def test_download_file_success(self, mock_get):
        """Test successful file download."""
        # Mock successful download
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b'test data']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            result = self.platform_utils.download_file('http://example.com/file', temp_path)
            
            assert result is True
            assert Path(temp_path).exists()
            
        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
    
    @patch('requests.get', side_effect=requests.exceptions.RequestException('Network error'))
    def test_download_file_network_error(self, mock_get):
        """Test file download network error."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            result = self.platform_utils.download_file('http://example.com/file', temp_path)
            assert result is False
        finally:
            if Path(temp_path).exists():
                Path(temp_path).unlink()
    
    @patch('zansoc_cli.platform_utils.PlatformUtils._is_port_available')
    def test_get_available_ports(self, mock_is_available):
        """Test getting available ports."""
        # Mock port availability
        mock_is_available.side_effect = lambda port: port in [8001, 8003, 8005]
        
        ports = self.platform_utils.get_available_ports(8000, 3)
        
        assert len(ports) == 3
        assert 8001 in ports
        assert 8003 in ports
        assert 8005 in ports
    
    @patch('psutil.net_if_addrs')
    @patch('psutil.net_if_stats')
    def test_get_network_interfaces(self, mock_stats, mock_addrs):
        """Test getting network interfaces."""
        # Mock network interfaces
        mock_addr = Mock()
        mock_addr.family = 2  # IPv4
        mock_addr.address = '192.168.1.100'
        mock_addr.netmask = '255.255.255.0'
        mock_addr.broadcast = '192.168.1.255'
        
        mock_addrs.return_value = {
            'eth0': [mock_addr]
        }
        
        mock_stat = Mock()
        mock_stat.isup = True
        mock_stat.speed = 1000
        
        mock_stats.return_value = {
            'eth0': mock_stat
        }
        
        interfaces = self.platform_utils.get_network_interfaces()
        
        assert 'eth0' in interfaces
        assert interfaces['eth0']['is_up'] is True
        assert len(interfaces['eth0']['addresses']) == 1
        assert interfaces['eth0']['addresses'][0]['address'] == '192.168.1.100'
    
    @patch('requests.get')
    def test_check_internet_connectivity_success(self, mock_get):
        """Test internet connectivity check success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.platform_utils._check_internet_connectivity()
        assert result is True
    
    @patch('requests.get', side_effect=requests.exceptions.RequestException())
    def test_check_internet_connectivity_failure(self, mock_get):
        """Test internet connectivity check failure."""
        result = self.platform_utils._check_internet_connectivity()
        assert result is False
    
    @patch('zansoc_cli.platform_utils.PlatformUtils.execute_command')
    def test_check_sudo_access_success(self, mock_execute):
        """Test sudo access check success."""
        mock_result = Mock()
        mock_result.success = True
        mock_execute.return_value = mock_result
        
        result = self.platform_utils._check_sudo_access()
        assert result is True
    
    @patch('zansoc_cli.platform_utils.PlatformUtils.execute_command')
    def test_check_sudo_access_failure(self, mock_execute):
        """Test sudo access check failure."""
        mock_result = Mock()
        mock_result.success = False
        mock_execute.return_value = mock_result
        
        result = self.platform_utils._check_sudo_access()
        assert result is False
    
    @patch('socket.socket')
    def test_is_port_available_true(self, mock_socket):
        """Test port availability check when port is available."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1  # Connection failed (port available)
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = self.platform_utils._is_port_available(8080)
        assert result is True
    
    @patch('socket.socket')
    def test_is_port_available_false(self, mock_socket):
        """Test port availability check when port is in use."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # Connection succeeded (port in use)
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = self.platform_utils._is_port_available(8080)
        assert result is False
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_count')
    @patch('os.getloadavg')
    def test_get_system_resources(self, mock_loadavg, mock_cpu_count, 
                                mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test getting system resources."""
        # Mock resource data
        mock_cpu_percent.return_value = 25.5
        mock_cpu_count.side_effect = [4, 8]  # physical, logical
        
        mock_memory = Mock()
        mock_memory.total = 8 * 1024**3
        mock_memory.available = 4 * 1024**3
        mock_memory.percent = 50.0
        mock_memory.used = 4 * 1024**3
        mock_memory.free = 4 * 1024**3
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.total = 100 * 1024**3
        mock_disk.used = 60 * 1024**3
        mock_disk.free = 40 * 1024**3
        mock_disk_usage.return_value = mock_disk
        
        mock_loadavg.return_value = (1.0, 1.5, 2.0)
        
        resources = self.platform_utils.get_system_resources()
        
        assert resources['cpu']['percent'] == 25.5
        assert resources['cpu']['count'] == 4
        assert resources['cpu']['count_logical'] == 8
        assert resources['memory']['percent'] == 50.0
        assert resources['disk']['percent'] == 60.0
        assert resources['load_average'] == (1.0, 1.5, 2.0)
    
    def test_create_directory_success(self):
        """Test successful directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / 'test_subdir' / 'nested'
            
            result = self.platform_utils.create_directory(str(test_path))
            
            assert result is True
            assert test_path.exists()
            assert test_path.is_dir()
    
    @patch('pathlib.Path.mkdir', side_effect=PermissionError('Permission denied'))
    def test_create_directory_failure(self, mock_mkdir):
        """Test directory creation failure."""
        result = self.platform_utils.create_directory('/invalid/path')
        assert result is False
    
    @patch('os.getenv')
    def test_get_environment_info(self, mock_getenv):
        """Test getting environment information."""
        # Mock environment variables
        env_vars = {
            'PATH': '/usr/bin:/bin',
            'HOME': '/home/user',
            'USER': 'testuser',
            'SHELL': '/bin/bash',
            'VIRTUAL_ENV': '/path/to/venv'
        }
        
        mock_getenv.side_effect = lambda key: env_vars.get(key)
        
        env_info = self.platform_utils.get_environment_info()
        
        assert env_info['PATH'] == '/usr/bin:/bin'
        assert env_info['HOME'] == '/home/user'
        assert env_info['USER'] == 'testuser'
        assert env_info['SHELL'] == '/bin/bash'
        assert env_info['VIRTUAL_ENV'] == '/path/to/venv'