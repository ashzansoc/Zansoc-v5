"""Ray cluster connection manager for ZanSoc CLI."""

import json
import os
import time
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .platform_utils import PlatformUtils, PlatformType
from .utils.logger import get_logger


class RayNodeStatus(Enum):
    """Ray node status enumeration."""
    NOT_CONNECTED = "not_connected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class RayNodeType(Enum):
    """Ray node type enumeration."""
    HEAD = "head"
    WORKER = "worker"
    UNKNOWN = "unknown"


@dataclass
class RayNodeInfo:
    """Ray node information."""
    node_id: str
    node_type: RayNodeType
    status: RayNodeStatus
    ip_address: str
    port: int
    resources: Dict[str, Any]
    uptime: float
    last_heartbeat: Optional[str] = None


@dataclass
class RayClusterInfo:
    """Ray cluster information."""
    cluster_id: str
    head_node: str
    total_nodes: int
    active_nodes: int
    total_resources: Dict[str, Any]
    cluster_status: str
    ray_version: str


@dataclass
class RayConnectionResult:
    """Ray connection operation result."""
    success: bool
    status: RayNodeStatus
    message: str
    node_id: Optional[str] = None
    cluster_info: Optional[RayClusterInfo] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class RayManager:
    """Manages Ray cluster connections and operations."""
    
    def __init__(self, platform_utils: Optional[PlatformUtils] = None):
        """Initialize Ray manager.
        
        Args:
            platform_utils: Platform utilities instance
        """
        self.platform_utils = platform_utils or PlatformUtils()
        self.logger = get_logger(__name__)
        self.system_info = self.platform_utils.get_system_info()
        
        # Ray configuration
        self.cluster_address = None
        self.cluster_password = None
        self.node_id = None
        self.connection_active = False
    
    def connect_to_cluster(self, address: str, password: str, 
                          env_name: str = "zansoc") -> RayConnectionResult:
        """Connect to Ray cluster as worker node.
        
        Args:
            address: Ray cluster head node address (host:port)
            password: Cluster authentication password
            env_name: Conda environment name where Ray is installed
            
        Returns:
            RayConnectionResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Connecting to Ray cluster at {address}")
            
            # Store connection parameters
            self.cluster_address = address
            self.cluster_password = password
            
            # Check if Ray is available
            if not self._is_ray_available(env_name):
                return RayConnectionResult(
                    success=False,
                    status=RayNodeStatus.ERROR,
                    message="Ray not available in specified environment",
                    error=f"Ray not found in conda environment '{env_name}'",
                    execution_time=time.time() - start_time
                )
            
            # Check if already connected to this cluster
            if self._is_connected_to_cluster(address, env_name):
                node_info = self._get_current_node_info(env_name)
                return RayConnectionResult(
                    success=True,
                    status=RayNodeStatus.CONNECTED,
                    message=f"Already connected to cluster at {address}",
                    node_id=node_info.get('node_id') if node_info else None,
                    execution_time=time.time() - start_time
                )
            
            # Disconnect from any existing cluster
            self._disconnect_from_cluster(env_name)
            
            # Set up environment variables for cross-platform compatibility
            self._setup_ray_environment()
            
            # Connect to cluster
            connection_result = self._execute_ray_start(address, password, env_name)
            if not connection_result:
                return RayConnectionResult(
                    success=False,
                    status=RayNodeStatus.ERROR,
                    message="Failed to start Ray worker node",
                    error="Ray start command failed",
                    execution_time=time.time() - start_time
                )
            
            # Wait for connection to establish
            time.sleep(3)
            
            # Verify connection
            if self.verify_node_registration(env_name):
                node_info = self._get_current_node_info(env_name)
                cluster_info = self._get_cluster_info(env_name)
                
                self.connection_active = True
                self.node_id = node_info.get('node_id') if node_info else None
                
                self.logger.info(f"Successfully connected to Ray cluster as node {self.node_id}")
                return RayConnectionResult(
                    success=True,
                    status=RayNodeStatus.CONNECTED,
                    message=f"Connected to Ray cluster as worker node {self.node_id}",
                    node_id=self.node_id,
                    cluster_info=cluster_info,
                    execution_time=time.time() - start_time
                )
            else:
                return RayConnectionResult(
                    success=False,
                    status=RayNodeStatus.ERROR,
                    message="Ray connection verification failed",
                    error="Node registration not confirmed",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            self.logger.error(f"Ray cluster connection failed: {e}")
            return RayConnectionResult(
                success=False,
                status=RayNodeStatus.ERROR,
                message="Ray cluster connection failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def verify_node_registration(self, env_name: str = "zansoc") -> bool:
        """Verify that node is registered in Ray cluster.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            True if node is registered
        """
        try:
            # Get Ray status
            ray_status = self._get_ray_status(env_name)
            if not ray_status:
                return False
            
            # Check if connected to cluster
            if 'cluster' in ray_status and ray_status['cluster']:
                # Check if this node is listed
                nodes = ray_status.get('nodes', [])
                if nodes:
                    # Look for this node in the cluster
                    for node in nodes:
                        if node.get('alive', False):
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Node registration verification failed: {e}")
            return False
    
    def get_cluster_info(self, env_name: str = "zansoc") -> Optional[RayClusterInfo]:
        """Get Ray cluster information.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            RayClusterInfo instance or None
        """
        try:
            cluster_info_dict = self._get_cluster_info(env_name)
            if cluster_info_dict:
                return RayClusterInfo(
                    cluster_id=cluster_info_dict.get('cluster_id', 'unknown'),
                    head_node=cluster_info_dict.get('head_node', 'unknown'),
                    total_nodes=cluster_info_dict.get('total_nodes', 0),
                    active_nodes=cluster_info_dict.get('active_nodes', 0),
                    total_resources=cluster_info_dict.get('total_resources', {}),
                    cluster_status=cluster_info_dict.get('cluster_status', 'unknown'),
                    ray_version=cluster_info_dict.get('ray_version', 'unknown')
                )
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster info: {e}")
            return None
    
    def disconnect_from_cluster(self, env_name: str = "zansoc") -> bool:
        """Disconnect from Ray cluster.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            True if disconnection successful
        """
        try:
            self.logger.info("Disconnecting from Ray cluster")
            
            result = self._disconnect_from_cluster(env_name)
            if result:
                self.connection_active = False
                self.node_id = None
                self.logger.info("Successfully disconnected from Ray cluster")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from cluster: {e}")
            return False
    
    def get_node_status(self, env_name: str = "zansoc") -> Dict[str, Any]:
        """Get current node status information.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            Dictionary with node status information
        """
        try:
            status = {
                'ray_available': self._is_ray_available(env_name),
                'ray_version': self._get_ray_version(env_name),
                'connected': self._is_connected_to_cluster(self.cluster_address, env_name) if self.cluster_address else False,
                'node_id': self.node_id,
                'cluster_address': self.cluster_address,
                'connection_active': self.connection_active,
                'node_info': None,
                'cluster_info': None
            }
            
            if status['connected']:
                status['node_info'] = self._get_current_node_info(env_name)
                status['cluster_info'] = self._get_cluster_info(env_name)
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get node status: {e}")
            return {'error': str(e)}
    
    def _setup_ray_environment(self) -> None:
        """Set up environment variables for Ray cross-platform compatibility."""
        try:
            # Set environment variable for Windows/macOS compatibility
            if self.system_info.platform in [PlatformType.WINDOWS, PlatformType.MACOS]:
                os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'
                self.logger.info("Set RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 for cross-platform compatibility")
            
            # Set other Ray environment variables if needed
            ray_env_vars = {
                'RAY_DISABLE_IMPORT_WARNING': '1',
                'RAY_DEDUP_LOGS': '0',
            }
            
            for var, value in ray_env_vars.items():
                os.environ[var] = value
                self.logger.debug(f"Set {var}={value}")
                
        except Exception as e:
            self.logger.error(f"Failed to setup Ray environment: {e}")
    
    def _execute_ray_start(self, address: str, password: str, env_name: str) -> bool:
        """Execute Ray start command to connect to cluster.
        
        Args:
            address: Cluster address
            password: Cluster password
            env_name: Conda environment name
            
        Returns:
            True if command executed successfully
        """
        try:
            # Build Ray start command
            ray_cmd = f"ray start --address='{address}' --redis-password='{password}'"
            
            # Execute in conda environment
            conda_cmd = self._get_conda_command()
            full_cmd = f"{conda_cmd} run -n {env_name} {ray_cmd}"
            
            # Set environment variables for the command
            env_vars = os.environ.copy()
            if self.system_info.platform in [PlatformType.WINDOWS, PlatformType.MACOS]:
                env_vars['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'
            
            result = self.platform_utils.execute_command(
                full_cmd, 
                timeout=120, 
                env=env_vars
            )
            
            if result.success:
                self.logger.info("Ray start command executed successfully")
                return True
            else:
                self.logger.error(f"Ray start command failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ray start execution failed: {e}")
            return False
    
    def _is_ray_available(self, env_name: str) -> bool:
        """Check if Ray is available in the specified environment.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            True if Ray is available
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(
                f"{conda_cmd} run -n {env_name} python -c \"import ray; print('Ray available')\""
            )
            return result.success and "Ray available" in result.stdout
        except:
            return False
    
    def _get_ray_version(self, env_name: str) -> Optional[str]:
        """Get Ray version in the specified environment.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            Ray version string or None
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(
                f"{conda_cmd} run -n {env_name} python -c \"import ray; print(ray.__version__)\""
            )
            if result.success:
                return result.stdout.strip()
            return None
        except:
            return None
    
    def _is_connected_to_cluster(self, address: Optional[str], env_name: str) -> bool:
        """Check if currently connected to a Ray cluster.
        
        Args:
            address: Expected cluster address
            env_name: Conda environment name
            
        Returns:
            True if connected to cluster
        """
        try:
            ray_status = self._get_ray_status(env_name)
            if not ray_status:
                return False
            
            # Check if Ray is initialized and connected
            if ray_status.get('initialized', False):
                # If address is specified, verify it matches
                if address:
                    cluster_address = ray_status.get('cluster_address')
                    return cluster_address == address
                else:
                    # Just check if connected to any cluster
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check cluster connection: {e}")
            return False
    
    def _get_ray_status(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Get Ray status information.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            Dictionary with Ray status or None
        """
        try:
            conda_cmd = self._get_conda_command()
            
            # Get Ray status using Python script
            status_script = '''
import ray
import json
try:
    if ray.is_initialized():
        cluster_resources = ray.cluster_resources()
        nodes = ray.nodes()
        status = {
            "initialized": True,
            "cluster_address": ray.get_runtime_context().gcs_address,
            "node_id": ray.get_runtime_context().node_id.hex(),
            "cluster_resources": cluster_resources,
            "nodes": [{"node_id": node["NodeID"], "alive": node["Alive"], "resources": node["Resources"]} for node in nodes],
            "ray_version": ray.__version__
        }
    else:
        status = {"initialized": False}
    print(json.dumps(status))
except Exception as e:
    print(json.dumps({"error": str(e), "initialized": False}))
'''
            
            result = self.platform_utils.execute_command(
                f"{conda_cmd} run -n {env_name} python -c \"{status_script}\"",
                timeout=30
            )
            
            if result.success and result.stdout.strip():
                try:
                    return json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse Ray status JSON")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Ray status: {e}")
            return None
    
    def _get_current_node_info(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Get current node information.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            Dictionary with node information or None
        """
        try:
            ray_status = self._get_ray_status(env_name)
            if ray_status and ray_status.get('initialized'):
                return {
                    'node_id': ray_status.get('node_id'),
                    'cluster_address': ray_status.get('cluster_address'),
                    'ray_version': ray_status.get('ray_version'),
                    'resources': ray_status.get('cluster_resources', {}),
                    'status': 'connected'
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get current node info: {e}")
            return None
    
    def _get_cluster_info(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Get cluster information.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            Dictionary with cluster information or None
        """
        try:
            ray_status = self._get_ray_status(env_name)
            if ray_status and ray_status.get('initialized'):
                nodes = ray_status.get('nodes', [])
                active_nodes = sum(1 for node in nodes if node.get('alive', False))
                
                return {
                    'cluster_id': ray_status.get('cluster_address', 'unknown'),
                    'head_node': ray_status.get('cluster_address', 'unknown'),
                    'total_nodes': len(nodes),
                    'active_nodes': active_nodes,
                    'total_resources': ray_status.get('cluster_resources', {}),
                    'cluster_status': 'active' if active_nodes > 0 else 'inactive',
                    'ray_version': ray_status.get('ray_version', 'unknown')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster info: {e}")
            return None
    
    def _disconnect_from_cluster(self, env_name: str) -> bool:
        """Disconnect from Ray cluster.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            True if disconnection successful
        """
        try:
            conda_cmd = self._get_conda_command()
            
            # Stop Ray
            result = self.platform_utils.execute_command(
                f"{conda_cmd} run -n {env_name} ray stop",
                timeout=30
            )
            
            # Ray stop command may return non-zero even on success
            # So we'll consider it successful if it doesn't throw an exception
            self.logger.info("Ray stop command executed")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from cluster: {e}")
            return False
    
    def _get_conda_command(self) -> str:
        """Get conda command path.
        
        Returns:
            Path to conda command
        """
        # Try to find conda in common locations
        conda_paths = [
            "conda",  # In PATH
            os.path.expanduser("~/.zansoc/miniconda/bin/conda"),
            "/opt/miniconda3/bin/conda",
            "/usr/local/miniconda3/bin/conda",
        ]
        
        for path in conda_paths:
            try:
                result = self.platform_utils.execute_command(f"{path} --version", timeout=5)
                if result.success:
                    return path
            except:
                continue
        
        return "conda"  # Fallback to PATH
    
    def get_connection_health(self, env_name: str = "zansoc") -> Dict[str, Any]:
        """Get connection health information.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            Dictionary with health information
        """
        try:
            health = {
                'ray_available': self._is_ray_available(env_name),
                'connected': self.connection_active,
                'node_id': self.node_id,
                'cluster_address': self.cluster_address,
                'last_heartbeat': None,
                'uptime': 0,
                'errors': []
            }
            
            if self.connection_active:
                node_info = self._get_current_node_info(env_name)
                if node_info:
                    health['last_heartbeat'] = 'active'
                    health['uptime'] = time.time()  # Simplified uptime
                else:
                    health['errors'].append('Node info not available')
                    health['connected'] = False
            
            return health
            
        except Exception as e:
            self.logger.error(f"Failed to get connection health: {e}")
            return {'error': str(e)}
    
    def test_cluster_connectivity(self, address: str, timeout: int = 10) -> bool:
        """Test connectivity to Ray cluster head node.
        
        Args:
            address: Cluster address (host:port)
            timeout: Connection timeout in seconds
            
        Returns:
            True if cluster is reachable
        """
        try:
            # Parse address
            if ':' in address:
                host, port = address.split(':', 1)
                port = int(port)
            else:
                host = address
                port = 6379  # Default Ray port
            
            # Test TCP connectivity
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
                
        except Exception as e:
            self.logger.error(f"Cluster connectivity test failed: {e}")
            return False