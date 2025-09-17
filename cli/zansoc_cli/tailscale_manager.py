"""Tailscale integration manager for ZanSoc CLI."""

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .platform_utils import PlatformUtils, PlatformType, Architecture
from .utils.logger import get_logger


class TailscaleStatus(Enum):
    """Tailscale status enumeration."""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    NEEDS_LOGIN = "needs_login"
    ERROR = "error"


@dataclass
class TailscaleDevice:
    """Tailscale device information."""
    id: str
    name: str
    ip: str
    os: str
    online: bool
    last_seen: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class TailscaleResult:
    """Tailscale operation result."""
    success: bool
    status: TailscaleStatus
    message: str
    ip_address: Optional[str] = None
    device_info: Optional[TailscaleDevice] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class TailscaleManager:
    """Manages Tailscale VPN network integration."""
    
    def __init__(self, platform_utils: Optional[PlatformUtils] = None):
        """Initialize Tailscale manager.
        
        Args:
            platform_utils: Platform utilities instance
        """
        self.platform_utils = platform_utils or PlatformUtils()
        self.logger = get_logger(__name__)
        self.system_info = self.platform_utils.get_system_info()
        
        # Tailscale configuration
        self.auth_key = None
        self.tailscale_binary = None
        
    def install_tailscale(self, auth_key: Optional[str] = None) -> TailscaleResult:
        """Install Tailscale using the official installation script or manual method.
        
        Args:
            auth_key: Tailscale auth key for automatic authentication
            
        Returns:
            TailscaleResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting Tailscale installation")
            
            # Store auth key for later use
            if auth_key:
                self.auth_key = auth_key
            
            # Check if already installed
            if self._is_tailscale_installed():
                existing_version = self._get_tailscale_version()
                self.logger.info(f"Tailscale already installed: {existing_version}")
                return TailscaleResult(
                    success=True,
                    status=TailscaleStatus.INSTALLED,
                    message=f"Tailscale already installed: {existing_version}",
                    execution_time=time.time() - start_time
                )
            
            # Try primary installation method first
            primary_result = self._install_tailscale_primary()
            if primary_result:
                # Verify installation
                if self._is_tailscale_installed():
                    version = self._get_tailscale_version()
                    self.logger.info(f"Tailscale installed successfully: {version}")
                    return TailscaleResult(
                        success=True,
                        status=TailscaleStatus.INSTALLED,
                        message=f"Tailscale installed successfully: {version}",
                        execution_time=time.time() - start_time
                    )
            
            # Try fallback installation method for ARM64
            if self.system_info.architecture == Architecture.ARM64:
                self.logger.info("Trying fallback ARM64 installation method")
                fallback_result = self._install_tailscale_arm64_fallback()
                if fallback_result and self._is_tailscale_installed():
                    version = self._get_tailscale_version()
                    self.logger.info(f"Tailscale installed via fallback method: {version}")
                    return TailscaleResult(
                        success=True,
                        status=TailscaleStatus.INSTALLED,
                        message=f"Tailscale installed via fallback method: {version}",
                        execution_time=time.time() - start_time
                    )
            
            return TailscaleResult(
                success=False,
                status=TailscaleStatus.ERROR,
                message="Tailscale installation failed",
                error="All installation methods failed",
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Tailscale installation failed: {e}")
            return TailscaleResult(
                success=False,
                status=TailscaleStatus.ERROR,
                message="Tailscale installation failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def authenticate_with_key(self, auth_key: str) -> TailscaleResult:
        """Authenticate Tailscale with provided auth key.
        
        Args:
            auth_key: Tailscale auth key
            
        Returns:
            TailscaleResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.info("Authenticating Tailscale with auth key")
            
            # Check if Tailscale is installed
            if not self._is_tailscale_installed():
                return TailscaleResult(
                    success=False,
                    status=TailscaleStatus.NOT_INSTALLED,
                    message="Tailscale not installed",
                    error="Tailscale must be installed before authentication",
                    execution_time=time.time() - start_time
                )
            
            # Store auth key
            self.auth_key = auth_key
            
            # Check current status
            current_status = self._get_tailscale_status()
            if current_status == TailscaleStatus.RUNNING:
                # Already authenticated and running
                ip_address = self.get_tailscale_ip()
                return TailscaleResult(
                    success=True,
                    status=TailscaleStatus.RUNNING,
                    message="Tailscale already authenticated and running",
                    ip_address=ip_address,
                    execution_time=time.time() - start_time
                )
            
            # Authenticate with auth key
            tailscale_cmd = self._get_tailscale_command()
            auth_cmd = f"sudo {tailscale_cmd} up --auth-key={auth_key}"
            
            result = self.platform_utils.execute_command(auth_cmd, timeout=120)
            
            if not result.success:
                return TailscaleResult(
                    success=False,
                    status=TailscaleStatus.ERROR,
                    message="Tailscale authentication failed",
                    error=result.stderr,
                    execution_time=time.time() - start_time
                )
            
            # Wait for connection to establish
            time.sleep(3)
            
            # Verify authentication
            final_status = self._get_tailscale_status()
            if final_status == TailscaleStatus.RUNNING:
                ip_address = self.get_tailscale_ip()
                device_info = self.get_device_info()
                
                self.logger.info(f"Tailscale authenticated successfully, IP: {ip_address}")
                return TailscaleResult(
                    success=True,
                    status=TailscaleStatus.RUNNING,
                    message=f"Tailscale authenticated successfully, IP: {ip_address}",
                    ip_address=ip_address,
                    device_info=device_info,
                    execution_time=time.time() - start_time
                )
            else:
                return TailscaleResult(
                    success=False,
                    status=final_status,
                    message="Tailscale authentication completed but not running",
                    error="Status check failed after authentication",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            self.logger.error(f"Tailscale authentication failed: {e}")
            return TailscaleResult(
                success=False,
                status=TailscaleStatus.ERROR,
                message="Tailscale authentication failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def get_tailscale_ip(self) -> Optional[str]:
        """Get Tailscale IP address.
        
        Returns:
            Tailscale IP address or None if not available
        """
        try:
            tailscale_cmd = self._get_tailscale_command()
            result = self.platform_utils.execute_command(f"{tailscale_cmd} ip -4")
            
            if result.success and result.stdout.strip():
                ip = result.stdout.strip()
                # Validate IP format
                if self._is_valid_ip(ip):
                    return ip
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Tailscale IP: {e}")
            return None
    
    def verify_connectivity(self, target_ip: str, timeout: int = 10) -> bool:
        """Verify network connectivity to target IP through Tailscale.
        
        Args:
            target_ip: Target IP address to test
            timeout: Connection timeout in seconds
            
        Returns:
            True if connectivity successful
        """
        try:
            self.logger.info(f"Verifying connectivity to {target_ip}")
            
            # Use ping to test connectivity
            if self.system_info.platform == PlatformType.WINDOWS:
                ping_cmd = f"ping -n 3 -w {timeout * 1000} {target_ip}"
            else:
                ping_cmd = f"ping -c 3 -W {timeout} {target_ip}"
            
            result = self.platform_utils.execute_command(ping_cmd, timeout=timeout + 5)
            
            if result.success:
                # Check for successful ping responses
                if self.system_info.platform == PlatformType.WINDOWS:
                    success_indicators = ["Reply from", "TTL="]
                else:
                    success_indicators = ["bytes from", "time="]
                
                return any(indicator in result.stdout for indicator in success_indicators)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Connectivity verification failed: {e}")
            return False
    
    def get_device_info(self) -> Optional[TailscaleDevice]:
        """Get current device information from Tailscale.
        
        Returns:
            TailscaleDevice instance or None if not available
        """
        try:
            tailscale_cmd = self._get_tailscale_command()
            result = self.platform_utils.execute_command(f"{tailscale_cmd} status --json")
            
            if result.success and result.stdout.strip():
                status_data = json.loads(result.stdout)
                
                # Find self device
                self_device = status_data.get("Self")
                if self_device:
                    return TailscaleDevice(
                        id=self_device.get("ID", ""),
                        name=self_device.get("HostName", ""),
                        ip=self_device.get("TailscaleIPs", [""])[0] if self_device.get("TailscaleIPs") else "",
                        os=self_device.get("OS", ""),
                        online=self_device.get("Online", False),
                        last_seen=self_device.get("LastSeen"),
                        tags=self_device.get("Tags", [])
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            return None
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive Tailscale network status.
        
        Returns:
            Dictionary with network status information
        """
        try:
            status = {
                'installed': self._is_tailscale_installed(),
                'version': self._get_tailscale_version() if self._is_tailscale_installed() else None,
                'status': self._get_tailscale_status(),
                'ip_address': self.get_tailscale_ip(),
                'device_info': None,
                'peers': [],
                'connectivity': {}
            }
            
            if status['status'] == TailscaleStatus.RUNNING:
                status['device_info'] = self.get_device_info()
                status['peers'] = self._get_peer_devices()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get network status: {e}")
            return {'error': str(e)}
    
    def _install_tailscale_primary(self) -> bool:
        """Install Tailscale using the primary method (official script).
        
        Returns:
            True if installation successful
        """
        try:
            if self.system_info.platform == PlatformType.WINDOWS:
                # Windows installation
                return self._install_tailscale_windows()
            else:
                # Unix installation using official script
                install_cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
                result = self.platform_utils.execute_command(install_cmd, shell=True, timeout=300)
                return result.success
                
        except Exception as e:
            self.logger.error(f"Primary Tailscale installation failed: {e}")
            return False
    
    def _install_tailscale_arm64_fallback(self) -> bool:
        """Install Tailscale using ARM64 fallback method (manual binary).
        
        Returns:
            True if installation successful
        """
        try:
            self.logger.info("Using ARM64 fallback installation method")
            
            # Download ARM64 binary
            if self.system_info.platform == PlatformType.LINUX:
                download_url = "https://pkgs.tailscale.com/stable/tailscale_1.88.1_arm64.tgz"
            else:
                # macOS ARM64
                download_url = "https://pkgs.tailscale.com/stable/tailscale_1.88.1_darwin_arm64.tgz"
            
            # Download to temporary location
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "tailscale.tgz"
                
                if not self.platform_utils.download_file(download_url, str(archive_path)):
                    return False
                
                # Extract archive
                extract_cmd = f"tar xzf {archive_path} -C {temp_dir}"
                result = self.platform_utils.execute_command(extract_cmd)
                if not result.success:
                    return False
                
                # Find extracted directory
                extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir() and d.name.startswith("tailscale_")]
                if not extracted_dirs:
                    return False
                
                extracted_dir = extracted_dirs[0]
                
                # Copy binaries to system locations
                tailscale_bin = extracted_dir / "tailscale"
                tailscaled_bin = extracted_dir / "tailscaled"
                
                if tailscale_bin.exists() and tailscaled_bin.exists():
                    # Copy to /usr/bin (requires sudo)
                    copy_cmds = [
                        f"sudo cp {tailscale_bin} /usr/bin/",
                        f"sudo cp {tailscaled_bin} /usr/sbin/",
                        "sudo chmod +x /usr/bin/tailscale",
                        "sudo chmod +x /usr/sbin/tailscaled"
                    ]
                    
                    for cmd in copy_cmds:
                        result = self.platform_utils.execute_command(cmd)
                        if not result.success:
                            self.logger.warning(f"Command failed: {cmd}")
                    
                    # Start tailscaled daemon
                    daemon_cmd = "sudo tailscaled &"
                    self.platform_utils.execute_command(daemon_cmd, shell=True)
                    
                    # Wait for daemon to start
                    time.sleep(2)
                    
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"ARM64 fallback installation failed: {e}")
            return False
    
    def _install_tailscale_windows(self) -> bool:
        """Install Tailscale on Windows.
        
        Returns:
            True if installation successful
        """
        try:
            # Download Windows installer
            download_url = "https://pkgs.tailscale.com/stable/tailscale-setup.exe"
            
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                installer_path = Path(temp_dir) / "tailscale-setup.exe"
                
                if not self.platform_utils.download_file(download_url, str(installer_path)):
                    return False
                
                # Run installer silently
                install_cmd = f'"{installer_path}" /S'
                result = self.platform_utils.execute_command(install_cmd, timeout=300)
                
                return result.success
                
        except Exception as e:
            self.logger.error(f"Windows Tailscale installation failed: {e}")
            return False
    
    def _is_tailscale_installed(self) -> bool:
        """Check if Tailscale is installed.
        
        Returns:
            True if Tailscale is installed
        """
        try:
            tailscale_cmd = self._get_tailscale_command()
            result = self.platform_utils.execute_command(f"{tailscale_cmd} version", timeout=10)
            return result.success
        except:
            return False
    
    def _get_tailscale_command(self) -> str:
        """Get Tailscale command path.
        
        Returns:
            Path to tailscale command
        """
        if self.tailscale_binary:
            return self.tailscale_binary
        
        # Try common locations
        common_paths = [
            "/usr/bin/tailscale",
            "/usr/local/bin/tailscale",
            "/opt/homebrew/bin/tailscale",
            "tailscale"  # In PATH
        ]
        
        for path in common_paths:
            try:
                result = self.platform_utils.execute_command(f"{path} version", timeout=5)
                if result.success:
                    self.tailscale_binary = path
                    return path
            except:
                continue
        
        return "tailscale"  # Fallback to PATH
    
    def _get_tailscale_version(self) -> Optional[str]:
        """Get Tailscale version.
        
        Returns:
            Version string or None
        """
        try:
            tailscale_cmd = self._get_tailscale_command()
            result = self.platform_utils.execute_command(f"{tailscale_cmd} version")
            
            if result.success and result.stdout:
                # Extract version from output
                lines = result.stdout.strip().split('\n')
                if lines:
                    # First line usually contains version
                    version_line = lines[0]
                    # Extract version number (e.g., "1.88.1" from "1.88.1-t12345")
                    version_match = re.search(r'(\d+\.\d+\.\d+)', version_line)
                    if version_match:
                        return version_match.group(1)
                    return version_line.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Tailscale version: {e}")
            return None
    
    def _get_tailscale_status(self) -> TailscaleStatus:
        """Get current Tailscale status.
        
        Returns:
            TailscaleStatus enum value
        """
        try:
            if not self._is_tailscale_installed():
                return TailscaleStatus.NOT_INSTALLED
            
            tailscale_cmd = self._get_tailscale_command()
            result = self.platform_utils.execute_command(f"{tailscale_cmd} status")
            
            if not result.success:
                return TailscaleStatus.ERROR
            
            status_output = result.stdout.lower()
            
            if "logged out" in status_output or "needs login" in status_output:
                return TailscaleStatus.NEEDS_LOGIN
            elif "stopped" in status_output:
                return TailscaleStatus.STOPPED
            elif "starting" in status_output:
                return TailscaleStatus.STARTING
            elif any(indicator in status_output for indicator in ["online", "connected", "100."]):
                return TailscaleStatus.RUNNING
            else:
                return TailscaleStatus.STOPPED
                
        except Exception as e:
            self.logger.error(f"Failed to get Tailscale status: {e}")
            return TailscaleStatus.ERROR
    
    def _get_peer_devices(self) -> List[TailscaleDevice]:
        """Get list of peer devices.
        
        Returns:
            List of TailscaleDevice instances
        """
        try:
            tailscale_cmd = self._get_tailscale_command()
            result = self.platform_utils.execute_command(f"{tailscale_cmd} status --json")
            
            if result.success and result.stdout.strip():
                status_data = json.loads(result.stdout)
                peers = []
                
                peer_data = status_data.get("Peer", {})
                for peer_id, peer_info in peer_data.items():
                    device = TailscaleDevice(
                        id=peer_id,
                        name=peer_info.get("HostName", ""),
                        ip=peer_info.get("TailscaleIPs", [""])[0] if peer_info.get("TailscaleIPs") else "",
                        os=peer_info.get("OS", ""),
                        online=peer_info.get("Online", False),
                        last_seen=peer_info.get("LastSeen"),
                        tags=peer_info.get("Tags", [])
                    )
                    peers.append(device)
                
                return peers
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get peer devices: {e}")
            return []
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format.
        
        Args:
            ip: IP address string
            
        Returns:
            True if valid IP address
        """
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False