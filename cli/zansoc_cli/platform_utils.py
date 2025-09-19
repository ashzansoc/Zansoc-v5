"""Platform detection and system utilities for ZanSoc CLI."""

import os
import platform
import shutil
import subprocess
import sys
import time
import psutil
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .utils.logger import get_logger


class PlatformType(Enum):
    """Platform type enumeration."""
    LINUX = "linux"
    MACOS = "darwin"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """Architecture enumeration."""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    ARM = "arm"
    I386 = "i386"
    UNKNOWN = "unknown"


@dataclass
class SystemInfo:
    """System information data class."""
    platform: PlatformType
    architecture: Architecture
    os_name: str
    os_version: str
    python_version: str
    cpu_count: int
    memory_total: int  # GB
    disk_free: int     # GB
    hostname: str
    username: str


@dataclass
class CommandResult:
    """Command execution result."""
    success: bool
    returncode: int
    stdout: str
    stderr: str
    execution_time: float
    command: str


class PlatformUtils:
    """Platform detection and system utilities."""
    
    def __init__(self):
        """Initialize platform utilities."""
        self.logger = get_logger(__name__)
        self._system_info = None
    
    def detect_platform(self) -> Dict[str, Any]:
        """Detect platform information.
        
        Returns:
            Dictionary with platform information
        """
        try:
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            # Map platform names
            platform_map = {
                'linux': PlatformType.LINUX,
                'darwin': PlatformType.MACOS,
                'windows': PlatformType.WINDOWS,
            }
            
            detected_platform = platform_map.get(system, PlatformType.UNKNOWN)
            
            # Map architecture names
            arch_map = {
                'x86_64': Architecture.X86_64,
                'amd64': Architecture.X86_64,
                'arm64': Architecture.ARM64,
                'aarch64': Architecture.ARM64,
                'armv7l': Architecture.ARM,
                'armv6l': Architecture.ARM,
                'i386': Architecture.I386,
                'i686': Architecture.I386,
            }
            
            detected_arch = arch_map.get(machine, Architecture.UNKNOWN)
            
            platform_info = {
                'platform': detected_platform,
                'architecture': detected_arch,
                'platform_string': f"{detected_platform.value}-{detected_arch.value}",
                'system': system,
                'machine': machine,
                'is_linux': detected_platform == PlatformType.LINUX,
                'is_macos': detected_platform == PlatformType.MACOS,
                'is_windows': detected_platform == PlatformType.WINDOWS,
                'is_arm': detected_arch in [Architecture.ARM64, Architecture.ARM],
                'is_x86': detected_arch in [Architecture.X86_64, Architecture.I386],
            }
            
            self.logger.info(f"Detected platform: {platform_info['platform_string']}")
            return platform_info
            
        except Exception as e:
            self.logger.error(f"Platform detection failed: {e}")
            return {
                'platform': PlatformType.UNKNOWN,
                'architecture': Architecture.UNKNOWN,
                'platform_string': 'unknown-unknown',
                'error': str(e)
            }
    
    def get_system_info(self) -> SystemInfo:
        """Get comprehensive system information.
        
        Returns:
            SystemInfo instance
        """
        if self._system_info is not None:
            return self._system_info
        
        try:
            platform_info = self.detect_platform()
            
            # Get memory info in GB
            memory = psutil.virtual_memory()
            memory_gb = round(memory.total / (1024**3), 1)
            
            # Get disk info in GB
            disk = psutil.disk_usage('/')
            disk_free_gb = round(disk.free / (1024**3), 1)
            
            self._system_info = SystemInfo(
                platform=platform_info['platform'],
                architecture=platform_info['architecture'],
                os_name=platform.system(),
                os_version=platform.release(),
                python_version=platform.python_version(),
                cpu_count=psutil.cpu_count(),
                memory_total=memory_gb,
                disk_free=disk_free_gb,
                hostname=platform.node(),
                username=os.getenv('USER', os.getenv('USERNAME', 'unknown'))
            )
            
            self.logger.info(f"System info collected: {self._system_info.platform.value} "
                           f"{self._system_info.architecture.value}, "
                           f"{self._system_info.cpu_count} CPUs, "
                           f"{self._system_info.memory_total}GB RAM")
            
            return self._system_info
            
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            # Return minimal info on error
            return SystemInfo(
                platform=PlatformType.UNKNOWN,
                architecture=Architecture.UNKNOWN,
                os_name="unknown",
                os_version="unknown",
                python_version=platform.python_version(),
                cpu_count=1,
                memory_total=0,
                disk_free=0,
                hostname="unknown",
                username="unknown"
            )
    
    def check_prerequisites(self) -> List[str]:
        """Check system prerequisites for ZanSoc onboarding.
        
        Returns:
            List of missing prerequisites or empty list if all met
        """
        missing = []
        
        try:
            system_info = self.get_system_info()
            
            # Check Python version (3.8+)
            python_version = tuple(map(int, system_info.python_version.split('.')))
            if python_version < (3, 8):
                missing.append(f"Python 3.8+ required (found {system_info.python_version})")
            
            # Check available disk space (minimum 2GB)
            if system_info.disk_free < 2:
                missing.append(f"At least 2GB free disk space required (found {system_info.disk_free}GB)")
            
            # Check available memory (minimum 1GB)
            if system_info.memory_total < 1:
                missing.append(f"At least 1GB RAM required (found {system_info.memory_total}GB)")
            
            # Check internet connectivity
            if not self._check_internet_connectivity():
                missing.append("Internet connectivity required")
            
            # Check for required system commands
            required_commands = ['git', 'curl']
            for cmd in required_commands:
                if not shutil.which(cmd):
                    missing.append(f"Command '{cmd}' not found in PATH")
            
            # Platform-specific checks
            if system_info.platform == PlatformType.LINUX:
                # Check for sudo access
                if not self._check_sudo_access():
                    missing.append("Sudo access required for system installations")
            
            if missing:
                self.logger.warning(f"Prerequisites check failed: {missing}")
            else:
                self.logger.info("All prerequisites met")
            
            return missing
            
        except Exception as e:
            self.logger.error(f"Prerequisites check failed: {e}")
            return [f"Prerequisites check error: {e}"]
    
    def execute_command(self, command: str, shell: bool = True, timeout: int = 300, 
                       cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> CommandResult:
        """Execute a system command with error handling and timeout.
        
        Args:
            command: Command to execute
            shell: Whether to use shell
            timeout: Command timeout in seconds
            cwd: Working directory
            env: Environment variables
            
        Returns:
            CommandResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Executing command: {command}")
            
            # Prepare command
            if shell:
                cmd = command
            else:
                cmd = command.split() if isinstance(command, str) else command
            
            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
            
            # Execute command
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=exec_env
            )
            
            execution_time = time.time() - start_time
            
            command_result = CommandResult(
                success=result.returncode == 0,
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                execution_time=execution_time,
                command=command
            )
            
            if command_result.success:
                self.logger.debug(f"Command succeeded in {execution_time:.2f}s: {command}")
            else:
                self.logger.warning(f"Command failed (code {result.returncode}) in {execution_time:.2f}s: {command}")
                if command_result.stderr:
                    self.logger.warning(f"Command stderr: {command_result.stderr}")
            
            return command_result
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            self.logger.error(f"Command timed out after {timeout}s: {command}")
            return CommandResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                execution_time=execution_time,
                command=command
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Command execution failed: {e}")
            return CommandResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                command=command
            )
    
    def download_file(self, url: str, destination: str, timeout: int = 300, 
                     chunk_size: int = 8192) -> bool:
        """Download a file with progress tracking and retry logic.
        
        Args:
            url: URL to download
            destination: Destination file path
            timeout: Download timeout in seconds
            chunk_size: Download chunk size in bytes
            
        Returns:
            True if download successful
        """
        try:
            self.logger.info(f"Downloading {url} to {destination}")
            
            # Create destination directory if needed
            dest_path = Path(destination)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with progress tracking
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress for large files
                        if total_size > 0 and downloaded % (chunk_size * 100) == 0:
                            progress = (downloaded / total_size) * 100
                            self.logger.debug(f"Download progress: {progress:.1f}%")
            
            # Verify download
            if dest_path.exists() and dest_path.stat().st_size > 0:
                self.logger.info(f"Successfully downloaded {url} ({downloaded} bytes)")
                return True
            else:
                self.logger.error(f"Download verification failed: {destination}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Download failed (network error): {e}")
            return False
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False
    
    def get_available_ports(self, start_port: int = 8000, count: int = 10) -> List[int]:
        """Get list of available ports.
        
        Args:
            start_port: Starting port number
            count: Number of ports to check
            
        Returns:
            List of available port numbers
        """
        available_ports = []
        
        for port in range(start_port, start_port + count * 10):
            if self._is_port_available(port):
                available_ports.append(port)
                if len(available_ports) >= count:
                    break
        
        self.logger.debug(f"Found {len(available_ports)} available ports starting from {start_port}")
        return available_ports
    
    def get_network_interfaces(self) -> Dict[str, Dict[str, Any]]:
        """Get network interface information.
        
        Returns:
            Dictionary of network interfaces
        """
        try:
            interfaces = {}
            
            for interface_name, addresses in psutil.net_if_addrs().items():
                interface_info = {
                    'addresses': [],
                    'is_up': False,
                    'is_loopback': interface_name.startswith('lo')
                }
                
                for addr in addresses:
                    if addr.family == 2:  # IPv4
                        interface_info['addresses'].append({
                            'type': 'IPv4',
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                    elif addr.family == 10:  # IPv6
                        interface_info['addresses'].append({
                            'type': 'IPv6',
                            'address': addr.address,
                            'netmask': addr.netmask
                        })
                
                # Check if interface is up
                try:
                    stats = psutil.net_if_stats()[interface_name]
                    interface_info['is_up'] = stats.isup
                    interface_info['speed'] = stats.speed
                except KeyError:
                    pass
                
                interfaces[interface_name] = interface_info
            
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Failed to get network interfaces: {e}")
            return {}
    
    def _check_internet_connectivity(self, timeout: int = 10) -> bool:
        """Check internet connectivity.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if internet is accessible
        """
        test_urls = [
            'https://www.google.com',
            'https://www.github.com',
            'https://httpbin.org/get'
        ]
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    return True
            except:
                continue
        
        return False
    
    def _check_sudo_access(self) -> bool:
        """Check if user has sudo access.
        
        Returns:
            True if sudo access available
        """
        try:
            result = self.execute_command('sudo -n true', timeout=5)
            return result.success
        except:
            return False
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available
        """
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except:
            return False
    
    def get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'count_logical': psutil.cpu_count(logical=True)
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system resources: {e}")
            return {}
    
    def create_directory(self, path: str, mode: int = 0o755) -> bool:
        """Create directory with proper permissions.
        
        Args:
            path: Directory path to create
            mode: Directory permissions
            
        Returns:
            True if successful
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True, mode=mode)
            self.logger.debug(f"Created directory: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    def get_environment_info(self) -> Dict[str, str]:
        """Get relevant environment variables.
        
        Returns:
            Dictionary of environment variables
        """
        relevant_vars = [
            'PATH', 'HOME', 'USER', 'USERNAME', 'SHELL',
            'PYTHON_PATH', 'VIRTUAL_ENV', 'CONDA_DEFAULT_ENV',
            'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'
        ]
        
        env_info = {}
        for var in relevant_vars:
            value = os.getenv(var)
            if value:
                env_info[var] = value
        
        return env_info