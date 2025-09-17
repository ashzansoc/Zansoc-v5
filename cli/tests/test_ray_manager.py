"""Tests for RayManager class."""

import pytest
import json
import os
import time
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from zansoc_cli.ray_manager import (
    RayManager, RayConnectionResult, RayNodeStatus, RayNodeType,
    RayNodeInfo, RayClusterInfo
)
from zansoc_cli.platform_utils import PlatformUtils, PlatformType, Architecture, SystemInfo


class TestRayManager:
    """Test cases for RayManager."""
    
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
        
        # Initialize Ray manager with mocked platform utils
        self.ray_manager = RayManager(self.mock_platform_utils)
    
    def test_initialization(self):
        """Test Ray manager initialization."""
        assert self.ray_manager.platform_utils == self.mock_platform_utils
        assert self.ray_manager.system_info == self.mock_system_info
        assert self.ray_manager.cluster_address is None
        assert self.ray_manager.cluster_password is None
        assert self.ray_manager.node_id is None
        assert self.ray_manager.connection_active is False
    
    @patch('zansoc_cli.ray_manager.RayManager._is_ray_available')
    def test_connect_to_cluster_ray_not_available(self, mock_is_ray_available):
        """Test cluster connection when Ray is not available."""
        mock_is_ray_available.return_value = False
        
        result = self.ray_manager.connect_to_cluster("100.101.84.71:6379", "password")
        
        assert isinstance(result, RayConnectionResult)
        assert result.success is False
        assert result.status == RayNodeStatus.ERROR
        assert "not available" in result.message
        assert result.execution_time > 0
    
    @patch('zansoc_cli.ray_manager.RayManager._is_ray_available')
    @patch('zansoc_cli.ray_manager.RayManager._is_connected_to_cluster')
    @patch('zansoc_cli.ray_manager.RayManager._get_current_node_info')
    def test_connect_to_cluster_already_connected(self, mock_get_node_info, 
                                                mock_is_connected, mock_is_ray_available):
        """Test cluster connection when already connected."""
        mock_is_ray_available.return_value = True
        mock_is_connected.return_value = True
        
        # Mock existing node info
        existing_node = {
            'node_id': 'node123',
            'cluster_address': '100.101.84.71:6379',
            'status': 'connected'
        }
        mock_get_node_info.return_value = existing_node
        
        result = self.ray_manager.connect_to_cluster("100.101.84.71:6379", "password")
        
        assert result.success is True
        assert result.status == RayNodeStatus.CONNECTED
        assert "Already connected" in result.message
        assert result.node_id == "node123"
    
    @patch('zansoc_cli.ray_manager.RayManager._is_ray_available')
    @patch('zansoc_cli.ray_manager.RayManager._is_connected_to_cluster')
    @patch('zansoc_cli.ray_manager.RayManager._disconnect_from_cluster')
    @patch('zansoc_cli.ray_manager.RayManager._setup_ray_environment')
    @patch('zansoc_cli.ray_manager.RayManager._execute_ray_start')
    @patch('zansoc_cli.ray_manager.RayManager.verify_node_registration')
    @patch('zansoc_cli.ray_manager.RayManager._get_current_node_info')
    @patch('zansoc_cli.ray_manager.RayManager._get_cluster_info')
    @patch('time.sleep')
    def test_connect_to_cluster_success(self, mock_sleep, mock_get_cluster_info, 
                                      mock_get_node_info, mock_verify_registration,
                                      mock_execute_start, mock_setup_env, 
                                      mock_disconnect, mock_is_connected, mock_is_ray_available):
        """Test successful cluster connection."""
        mock_is_ray_available.return_value = True
        mock_is_connected.return_value = False  # Not connected initially
        mock_disconnect.return_value = True
        mock_execute_start.return_value = True
        mock_verify_registration.return_value = True
        
        # Mock node and cluster info
        node_info = {
            'node_id': 'node456',
            'cluster_address': '100.101.84.71:6379',
            'status': 'connected'
        }
        cluster_info = {
            'cluster_id': '100.101.84.71:6379',
            'total_nodes': 2,
            'active_nodes': 2
        }
        mock_get_node_info.return_value = node_info
        mock_get_cluster_info.return_value = cluster_info
        
        result = self.ray_manager.connect_to_cluster("100.101.84.71:6379", "password")
        
        assert result.success is True
        assert result.status == RayNodeStatus.CONNECTED
        assert "Connected to Ray cluster" in result.message
        assert result.node_id == "node456"
        assert self.ray_manager.node_id == "node456"
        assert self.ray_manager.cluster_address == "100.101.84.71:6379"
        assert self.ray_manager.cluster_password == "password"
        assert self.ray_manager.connection_active is True
    
    @patch('zansoc_cli.ray_manager.RayManager._is_ray_available')
    @patch('zansoc_cli.ray_manager.RayManager._is_connected_to_cluster')
    @patch('zansoc_cli.ray_manager.RayManager._disconnect_from_cluster')
    @patch('zansoc_cli.ray_manager.RayManager._setup_ray_environment')
    @patch('zansoc_cli.ray_manager.RayManager._execute_ray_start')
    def test_connect_to_cluster_start_failure(self, mock_execute_start, mock_setup_env,
                                            mock_disconnect, mock_is_connected, mock_is_ray_available):
        """Test cluster connection when Ray start command fails."""
        mock_is_ray_available.return_value = True
        mock_is_connected.return_value = False
        mock_disconnect.return_value = True
        mock_execute_start.return_value = False
        
        result = self.ray_manager.connect_to_cluster("100.101.84.71:6379", "password")
        
        assert result.success is False
        assert result.status == RayNodeStatus.ERROR
        assert "Failed to start Ray worker" in result.message
    
    @patch('zansoc_cli.ray_manager.RayManager._get_ray_status')
    def test_verify_node_registration_success(self, mock_get_ray_status):
        """Test successful node registration verification."""
        mock_ray_status = {
            'cluster': True,
            'nodes': [
                {'alive': True, 'node_id': 'node123'},
                {'alive': False, 'node_id': 'node456'}
            ]
        }
        mock_get_ray_status.return_value = mock_ray_status
        
        result = self.ray_manager.verify_node_registration()
        
        assert result is True
    
    @patch('zansoc_cli.ray_manager.RayManager._get_ray_status')
    def test_verify_node_registration_failure(self, mock_get_ray_status):
        """Test node registration verification failure."""
        mock_ray_status = {
            'cluster': False,
            'nodes': []
        }
        mock_get_ray_status.return_value = mock_ray_status
        
        result = self.ray_manager.verify_node_registration()
        
        assert result is False
    
    @patch('zansoc_cli.ray_manager.RayManager._get_cluster_info')
    def test_get_cluster_info_success(self, mock_get_cluster_info_dict):
        """Test successful cluster info retrieval."""
        cluster_info_dict = {
            'cluster_id': 'cluster123',
            'head_node': '100.101.84.71:6379',
            'total_nodes': 3,
            'active_nodes': 2,
            'total_resources': {'CPU': 12, 'memory': 24000},
            'cluster_status': 'active',
            'ray_version': '2.8.0'
        }
        mock_get_cluster_info_dict.return_value = cluster_info_dict
        
        result = self.ray_manager.get_cluster_info()
        
        assert isinstance(result, RayClusterInfo)
        assert result.cluster_id == 'cluster123'
        assert result.head_node == '100.101.84.71:6379'
        assert result.total_nodes == 3
        assert result.active_nodes == 2
    
    @patch('zansoc_cli.ray_manager.RayManager._disconnect_from_cluster')
    def test_disconnect_from_cluster_success(self, mock_disconnect):
        """Test successful disconnection."""
        # Set up initial state
        self.ray_manager.connection_active = True
        self.ray_manager.node_id = "node123"
        
        mock_disconnect.return_value = True
        
        result = self.ray_manager.disconnect_from_cluster()
        
        assert result is True
        assert self.ray_manager.connection_active is False
        assert self.ray_manager.node_id is None
    
    @patch('zansoc_cli.ray_manager.RayManager._disconnect_from_cluster')
    def test_disconnect_from_cluster_failure(self, mock_disconnect):
        """Test disconnection failure."""
        mock_disconnect.return_value = False
        
        result = self.ray_manager.disconnect_from_cluster()
        
        assert result is False
    
    @patch('zansoc_cli.ray_manager.RayManager._is_ray_available')
    @patch('zansoc_cli.ray_manager.RayManager._get_ray_version')
    @patch('zansoc_cli.ray_manager.RayManager._is_connected_to_cluster')
    @patch('zansoc_cli.ray_manager.RayManager._get_current_node_info')
    @patch('zansoc_cli.ray_manager.RayManager._get_cluster_info')
    def test_get_node_status(self, mock_get_cluster_info, mock_get_node_info,
                           mock_is_connected, mock_get_version, mock_is_available):
        """Test node status retrieval."""
        mock_is_available.return_value = True
        mock_get_version.return_value = "2.8.0"
        mock_is_connected.return_value = True
        mock_get_node_info.return_value = {'node_id': 'node123'}
        mock_get_cluster_info.return_value = {'cluster_id': 'cluster123'}
        
        # Set up manager state
        self.ray_manager.cluster_address = "100.101.84.71:6379"
        self.ray_manager.node_id = "node123"
        self.ray_manager.connection_active = True
        
        result = self.ray_manager.get_node_status()
        
        assert result['ray_available'] is True
        assert result['ray_version'] == "2.8.0"
        assert result['connected'] is True
        assert result['node_id'] == "node123"
        assert result['cluster_address'] == "100.101.84.71:6379"
        assert result['connection_active'] is True
        assert result['node_info'] == {'node_id': 'node123'}
        assert result['cluster_info'] == {'cluster_id': 'cluster123'}
    
    @patch('os.environ')
    def test_setup_ray_environment_windows(self, mock_environ):
        """Test Ray environment setup for Windows."""
        # Mock Windows system
        self.ray_manager.system_info.platform = PlatformType.WINDOWS
        
        self.ray_manager._setup_ray_environment()
        
        # Verify environment variables were set
        mock_environ.__setitem__.assert_any_call('RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER', '1')
        mock_environ.__setitem__.assert_any_call('RAY_DISABLE_IMPORT_WARNING', '1')
        mock_environ.__setitem__.assert_any_call('RAY_DEDUP_LOGS', '0')
    
    @patch('os.environ')
    def test_setup_ray_environment_macos(self, mock_environ):
        """Test Ray environment setup for macOS."""
        # Mock macOS system
        self.ray_manager.system_info.platform = PlatformType.MACOS
        
        self.ray_manager._setup_ray_environment()
        
        # Verify environment variables were set
        mock_environ.__setitem__.assert_any_call('RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER', '1')
    
    @patch('os.environ')
    def test_setup_ray_environment_linux(self, mock_environ):
        """Test Ray environment setup for Linux."""
        # Linux system (default)
        self.ray_manager.system_info.platform = PlatformType.LINUX
        
        self.ray_manager._setup_ray_environment()
        
        # Should not set RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER for Linux
        calls = [call for call in mock_environ.__setitem__.call_args_list 
                if call[0][0] == 'RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER']
        assert len(calls) == 0
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_execute_ray_start_success(self, mock_get_conda_command):
        """Test successful Ray start execution."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock successful command execution
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._execute_ray_start("100.101.84.71:6379", "password", "zansoc")
        
        assert result is True
        
        # Verify command was called correctly
        expected_cmd = "conda run -n zansoc ray start --address='100.101.84.71:6379' --redis-password='password'"
        self.mock_platform_utils.execute_command.assert_called_once()
        call_args = self.mock_platform_utils.execute_command.call_args
        assert expected_cmd in call_args[0][0]
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_execute_ray_start_failure(self, mock_get_conda_command):
        """Test Ray start execution failure."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock failed command execution
        mock_result = Mock()
        mock_result.success = False
        mock_result.stderr = "Connection refused"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._execute_ray_start("100.101.84.71:6379", "password", "zansoc")
        
        assert result is False
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_is_ray_available_true(self, mock_get_conda_command):
        """Test Ray availability check when Ray is available."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock successful Ray import
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "Ray available"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._is_ray_available("zansoc")
        
        assert result is True
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_is_ray_available_false(self, mock_get_conda_command):
        """Test Ray availability check when Ray is not available."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock failed Ray import
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._is_ray_available("zansoc")
        
        assert result is False
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_get_ray_version(self, mock_get_conda_command):
        """Test Ray version retrieval."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock successful version retrieval
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = "2.8.0\n"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._get_ray_version("zansoc")
        
        assert result == "2.8.0"
    
    @patch('zansoc_cli.ray_manager.RayManager._get_ray_status')
    def test_is_connected_to_cluster_true(self, mock_get_ray_status):
        """Test cluster connection check when connected."""
        mock_ray_status = {
            'initialized': True,
            'cluster_address': '100.101.84.71:6379'
        }
        mock_get_ray_status.return_value = mock_ray_status
        
        result = self.ray_manager._is_connected_to_cluster("100.101.84.71:6379", "zansoc")
        
        assert result is True
    
    @patch('zansoc_cli.ray_manager.RayManager._get_ray_status')
    def test_is_connected_to_cluster_false(self, mock_get_ray_status):
        """Test cluster connection check when not connected."""
        mock_ray_status = {
            'initialized': False
        }
        mock_get_ray_status.return_value = mock_ray_status
        
        result = self.ray_manager._is_connected_to_cluster("100.101.84.71:6379", "zansoc")
        
        assert result is False
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_get_ray_status_success(self, mock_get_conda_command):
        """Test successful Ray status retrieval."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock successful status retrieval
        status_data = {
            'initialized': True,
            'cluster_address': '100.101.84.71:6379',
            'node_id': 'node123',
            'ray_version': '2.8.0'
        }
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = json.dumps(status_data)
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._get_ray_status("zansoc")
        
        assert result == status_data
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_get_ray_status_failure(self, mock_get_conda_command):
        """Test Ray status retrieval failure."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock failed status retrieval
        mock_result = Mock()
        mock_result.success = False
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._get_ray_status("zansoc")
        
        assert result is None
    
    @patch('zansoc_cli.ray_manager.RayManager._get_conda_command')
    def test_disconnect_from_cluster_internal_success(self, mock_get_conda_command):
        """Test internal disconnect method success."""
        mock_get_conda_command.return_value = "conda"
        
        # Mock successful ray stop
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._disconnect_from_cluster("zansoc")
        
        assert result is True
    
    def test_get_conda_command_default(self):
        """Test conda command detection with default path."""
        # Mock successful conda version check
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.ray_manager._get_conda_command()
        
        assert result == "conda"
    
    @patch('os.path.expanduser')
    def test_get_conda_command_custom_path(self, mock_expanduser):
        """Test conda command detection with custom path."""
        mock_expanduser.return_value = "/home/user/.zansoc/miniconda/bin/conda"
        
        # Mock failed conda version check for default, success for custom path
        def mock_execute_side_effect(cmd, **kwargs):
            mock_result = Mock()
            if "conda --version" in cmd and "/home/user" in cmd:
                mock_result.success = True
            else:
                mock_result.success = False
            return mock_result
        
        self.mock_platform_utils.execute_command.side_effect = mock_execute_side_effect
        
        result = self.ray_manager._get_conda_command()
        
        assert result == "/home/user/.zansoc/miniconda/bin/conda"
    
    @patch('zansoc_cli.ray_manager.RayManager._is_ray_available')
    @patch('zansoc_cli.ray_manager.RayManager._get_current_node_info')
    def test_get_connection_health(self, mock_get_node_info, mock_is_ray_available):
        """Test connection health retrieval."""
        mock_is_ray_available.return_value = True
        mock_get_node_info.return_value = {'node_id': 'node123'}
        
        # Set up manager state
        self.ray_manager.connection_active = True
        self.ray_manager.node_id = "node123"
        self.ray_manager.cluster_address = "100.101.84.71:6379"
        
        result = self.ray_manager.get_connection_health()
        
        assert result['ray_available'] is True
        assert result['connected'] is True
        assert result['node_id'] == "node123"
        assert result['cluster_address'] == "100.101.84.71:6379"
        assert result['last_heartbeat'] == 'active'
    
    @patch('socket.socket')
    def test_test_cluster_connectivity_success(self, mock_socket):
        """Test successful cluster connectivity test."""
        # Mock successful socket connection
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = self.ray_manager.test_cluster_connectivity("100.101.84.71:6379")
        
        assert result is True
        mock_sock.connect_ex.assert_called_once_with(("100.101.84.71", 6379))
    
    @patch('socket.socket')
    def test_test_cluster_connectivity_failure(self, mock_socket):
        """Test failed cluster connectivity test."""
        # Mock failed socket connection
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1  # Connection failed
        mock_socket.return_value.__enter__.return_value = mock_sock
        
        result = self.ray_manager.test_cluster_connectivity("100.101.84.71:6379")
        
        assert result is False
    
    def test_test_cluster_connectivity_default_port(self):
        """Test cluster connectivity test with default port."""
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            result = self.ray_manager.test_cluster_connectivity("100.101.84.71")
            
            assert result is True
            mock_sock.connect_ex.assert_called_once_with(("100.101.84.71", 6379))


class TestRayDataClasses:
    """Test Ray data classes."""
    
    def test_ray_node_info_creation(self):
        """Test RayNodeInfo creation."""
        node_info = RayNodeInfo(
            node_id="node123",
            node_type=RayNodeType.WORKER,
            status=RayNodeStatus.CONNECTED,
            ip_address="192.168.1.100",
            port=6379,
            resources={"CPU": 4, "memory": 8000},
            uptime=3600.0
        )
        
        assert node_info.node_id == "node123"
        assert node_info.node_type == RayNodeType.WORKER
        assert node_info.status == RayNodeStatus.CONNECTED
        assert node_info.ip_address == "192.168.1.100"
        assert node_info.port == 6379
        assert node_info.resources == {"CPU": 4, "memory": 8000}
        assert node_info.uptime == 3600.0
        assert node_info.last_heartbeat is None
    
    def test_ray_cluster_info_creation(self):
        """Test RayClusterInfo creation."""
        cluster_info = RayClusterInfo(
            cluster_id="cluster123",
            head_node="100.101.84.71:6379",
            total_nodes=3,
            active_nodes=2,
            total_resources={"CPU": 12, "memory": 24000},
            cluster_status="active",
            ray_version="2.8.0"
        )
        
        assert cluster_info.cluster_id == "cluster123"
        assert cluster_info.head_node == "100.101.84.71:6379"
        assert cluster_info.total_nodes == 3
        assert cluster_info.active_nodes == 2
        assert cluster_info.total_resources == {"CPU": 12, "memory": 24000}
        assert cluster_info.cluster_status == "active"
        assert cluster_info.ray_version == "2.8.0"
    
    def test_ray_connection_result_creation(self):
        """Test RayConnectionResult creation."""
        result = RayConnectionResult(
            success=True,
            status=RayNodeStatus.CONNECTED,
            message="Successfully connected",
            node_id="node123",
            execution_time=2.5
        )
        
        assert result.success is True
        assert result.status == RayNodeStatus.CONNECTED
        assert result.message == "Successfully connected"
        assert result.node_id == "node123"
        assert result.cluster_info is None
        assert result.error is None
        assert result.execution_time == 2.5


class TestRayEnums:
    """Test Ray enumeration classes."""
    
    def test_ray_node_status_enum(self):
        """Test RayNodeStatus enum values."""
        assert RayNodeStatus.NOT_CONNECTED.value == "not_connected"
        assert RayNodeStatus.CONNECTING.value == "connecting"
        assert RayNodeStatus.CONNECTED.value == "connected"
        assert RayNodeStatus.DISCONNECTED.value == "disconnected"
        assert RayNodeStatus.ERROR.value == "error"
    
    def test_ray_node_type_enum(self):
        """Test RayNodeType enum values."""
        assert RayNodeType.HEAD.value == "head"
        assert RayNodeType.WORKER.value == "worker"
        assert RayNodeType.UNKNOWN.value == "unknown"