"""Environment setup manager for ZanSoc CLI."""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from .platform_utils import PlatformUtils, PlatformType, Architecture
from .utils.logger import get_logger


class InstallationStatus(Enum):
    """Installation status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class InstallationResult:
    """Installation result data class."""
    success: bool
    status: InstallationStatus
    message: str
    installation_path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class EnvironmentManager:
    """Manages automated software installation and environment setup."""
    
    def __init__(self, platform_utils: Optional[PlatformUtils] = None):
        """Initialize environment manager.
        
        Args:
            platform_utils: Platform utilities instance
        """
        self.platform_utils = platform_utils or PlatformUtils()
        self.logger = get_logger(__name__)
        self.system_info = self.platform_utils.get_system_info()
        
        # Installation paths
        self.install_base = Path.home() / ".zansoc"
        self.miniconda_path = self.install_base / "miniconda"
        self.repo_path = self.install_base / "zansoc-beta"
        
        # Ensure base directory exists
        self.install_base.mkdir(exist_ok=True)
    
    def install_miniconda(self, python_version: str = "3.13.7") -> InstallationResult:
        """Download and install miniconda with platform-specific logic.
        
        Args:
            python_version: Target Python version
            
        Returns:
            InstallationResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting miniconda installation for Python {python_version}")
            
            # Check if already installed
            if self._is_miniconda_installed():
                existing_version = self._get_miniconda_python_version()
                if existing_version and existing_version.startswith(python_version[:3]):  # Match major.minor
                    self.logger.info(f"Miniconda already installed with Python {existing_version}")
                    return InstallationResult(
                        success=True,
                        status=InstallationStatus.SKIPPED,
                        message=f"Miniconda already installed with Python {existing_version}",
                        installation_path=str(self.miniconda_path),
                        version=existing_version,
                        execution_time=time.time() - start_time
                    )
            
            # Get download URL based on platform
            download_url = self._get_miniconda_download_url()
            if not download_url:
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Unsupported platform for miniconda installation",
                    error="No download URL available for this platform",
                    execution_time=time.time() - start_time
                )
            
            # Try to install miniconda
            install_success = False
            
            # Method 1: Try system package manager first (faster)
            if self.system_info.platform == PlatformType.LINUX:
                self.logger.info("Trying to install miniconda via system package manager...")
                # Try apt-get for Ubuntu/Debian
                result = self.platform_utils.execute_command("which apt-get", timeout=10)
                if result.success:
                    # Install miniconda via apt if available
                    result = self.platform_utils.execute_command(
                        "sudo apt-get update && sudo apt-get install -y wget", 
                        timeout=300
                    )
                    if result.success:
                        # Download and install via wget + bash
                        install_cmd = f"wget -q {download_url} -O /tmp/miniconda.sh && bash /tmp/miniconda.sh -b -p {self.miniconda_path} && rm /tmp/miniconda.sh"
                        result = self.platform_utils.execute_command(install_cmd, timeout=900)
                        install_success = result.success
                        if install_success:
                            self.logger.info("Miniconda installed via system package manager")
            
            # Method 2: Download and install manually if system method failed
            if not install_success:
                with tempfile.TemporaryDirectory() as temp_dir:
                    installer_path = Path(temp_dir) / "miniconda_installer"
                    
                    self.logger.info(f"Downloading miniconda from {download_url}")
                    if not self.platform_utils.download_file(download_url, str(installer_path), timeout=900):  # 15 minutes
                        return InstallationResult(
                            success=False,
                            status=InstallationStatus.FAILED,
                            message="Failed to download miniconda installer",
                            error="Download failed - check internet connection and try again",
                            execution_time=time.time() - start_time
                        )
                    
                    # Make installer executable (Unix systems)
                    if self.system_info.platform != PlatformType.WINDOWS:
                        os.chmod(installer_path, 0o755)
                    
                    # Run installer
                    self.logger.info("Running miniconda installer...")
                    install_result = self._run_miniconda_installer(installer_path)
                    if not install_result:
                        return InstallationResult(
                            success=False,
                            status=InstallationStatus.FAILED,
                            message="Miniconda installation failed",
                            error="Installer execution failed - check permissions and disk space",
                            execution_time=time.time() - start_time
                        )
            
            # Verify installation
            if not self._is_miniconda_installed():
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Miniconda installation verification failed",
                    error="Installation not found after installer completed",
                    execution_time=time.time() - start_time
                )
            
            # Get installed version
            installed_version = self._get_miniconda_python_version()
            
            self.logger.info(f"Miniconda installation completed successfully")
            return InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message=f"Miniconda installed successfully with Python {installed_version}",
                installation_path=str(self.miniconda_path),
                version=installed_version,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Miniconda installation failed: {e}")
            return InstallationResult(
                success=False,
                status=InstallationStatus.FAILED,
                message="Miniconda installation failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def create_conda_environment(self, python_version: str = "3.13.7", 
                                env_name: str = "zansoc") -> InstallationResult:
        """Create conda environment with specified Python version.
        
        Args:
            python_version: Python version to install
            env_name: Environment name
            
        Returns:
            InstallationResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Creating conda environment '{env_name}' with Python {python_version}")
            
            # Check if miniconda is installed
            if not self._is_miniconda_installed():
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Miniconda not installed",
                    error="Miniconda must be installed before creating environments",
                    execution_time=time.time() - start_time
                )
            
            # Check if environment already exists
            if self._conda_env_exists(env_name):
                env_python_version = self._get_conda_env_python_version(env_name)
                if env_python_version and env_python_version.startswith(python_version[:3]):
                    self.logger.info(f"Conda environment '{env_name}' already exists with Python {env_python_version}")
                    return InstallationResult(
                        success=True,
                        status=InstallationStatus.SKIPPED,
                        message=f"Conda environment '{env_name}' already exists with Python {env_python_version}",
                        version=env_python_version,
                        execution_time=time.time() - start_time
                    )
            
            # Create conda environment
            conda_cmd = self._get_conda_command()
            create_cmd = f"{conda_cmd} create -n {env_name} python={python_version} -y"
            
            result = self.platform_utils.execute_command(create_cmd, timeout=600)
            if not result.success:
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message=f"Failed to create conda environment '{env_name}'",
                    error=result.stderr,
                    execution_time=time.time() - start_time
                )
            
            # Verify environment creation
            if not self._conda_env_exists(env_name):
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message=f"Conda environment '{env_name}' verification failed",
                    error="Environment not found after creation",
                    execution_time=time.time() - start_time
                )
            
            # Get created environment Python version
            created_version = self._get_conda_env_python_version(env_name)
            
            self.logger.info(f"Conda environment '{env_name}' created successfully with Python {created_version}")
            return InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message=f"Conda environment '{env_name}' created with Python {created_version}",
                version=created_version,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Conda environment creation failed: {e}")
            return InstallationResult(
                success=False,
                status=InstallationStatus.FAILED,
                message="Conda environment creation failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def clone_repository(self, repo_url: str, target_dir: Optional[str] = None) -> InstallationResult:
        """Download ZanSoc repository as ZIP archive (no authentication required).
        
        Args:
            repo_url: Repository URL (will be converted to ZIP download URL)
            target_dir: Target directory (defaults to self.repo_path)
            
        Returns:
            InstallationResult instance
        """
        start_time = time.time()
        
        try:
            target_path = Path(target_dir) if target_dir else self.repo_path
            self.logger.info(f"Downloading repository from {repo_url} to {target_path}")
            
            # Check if repository already exists
            if target_path.exists() and any(target_path.iterdir()):
                self.logger.info(f"Repository already exists at {target_path}")
                return InstallationResult(
                    success=True,
                    status=InstallationStatus.SKIPPED,
                    message=f"Repository already exists at {target_path}",
                    installation_path=str(target_path),
                    execution_time=time.time() - start_time
                )
            
            # Remove existing directory if it exists
            if target_path.exists():
                shutil.rmtree(target_path)
            
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert GitHub repo URL to ZIP download URL
            if "github.com" in repo_url:
                # Convert https://github.com/user/repo.git to ZIP download URL
                repo_url = repo_url.replace(".git", "")
                zip_url = f"{repo_url}/archive/refs/heads/main.zip"
            else:
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Unsupported repository URL format",
                    error="Only GitHub repositories are supported",
                    execution_time=time.time() - start_time
                )
            
            # Download repository as ZIP
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "repo.zip"
                
                self.logger.info(f"Downloading repository archive from {zip_url}")
                if not self.platform_utils.download_file(zip_url, str(zip_path)):
                    return InstallationResult(
                        success=False,
                        status=InstallationStatus.FAILED,
                        message="Failed to download repository archive",
                        error="Download failed",
                        execution_time=time.time() - start_time
                    )
                
                # Extract ZIP archive
                import zipfile
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find the extracted directory (usually repo-name-main)
                    extracted_dirs = [d for d in Path(temp_dir).iterdir() if d.is_dir() and d.name != "__pycache__"]
                    if not extracted_dirs:
                        return InstallationResult(
                            success=False,
                            status=InstallationStatus.FAILED,
                            message="No directory found in extracted archive",
                            error="Archive extraction failed",
                            execution_time=time.time() - start_time
                        )
                    
                    # Move the extracted directory to target location
                    extracted_dir = extracted_dirs[0]
                    shutil.move(str(extracted_dir), str(target_path))
                    
                except zipfile.BadZipFile:
                    return InstallationResult(
                        success=False,
                        status=InstallationStatus.FAILED,
                        message="Downloaded file is not a valid ZIP archive",
                        error="Invalid ZIP file",
                        execution_time=time.time() - start_time
                    )
            
            # Verify download
            if not target_path.exists() or not any(target_path.iterdir()):
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Repository download verification failed",
                    error="Repository directory not found or empty after download",
                    execution_time=time.time() - start_time
                )
            
            self.logger.info(f"Repository downloaded successfully to {target_path}")
            return InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message=f"Repository downloaded successfully to {target_path}",
                installation_path=str(target_path),
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Repository download failed: {e}")
            return InstallationResult(
                success=False,
                status=InstallationStatus.FAILED,
                message="Repository download failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def install_requirements(self, requirements_file: str, env_name: str = "zansoc") -> InstallationResult:
        """Install Python requirements from requirements.txt.
        
        Args:
            requirements_file: Path to requirements.txt file
            env_name: Conda environment name
            
        Returns:
            InstallationResult instance
        """
        start_time = time.time()
        
        try:
            req_path = Path(requirements_file)
            self.logger.info(f"Installing requirements from {req_path} in environment '{env_name}'")
            
            # Check if requirements file exists
            if not req_path.exists():
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message=f"Requirements file not found: {req_path}",
                    error="Requirements file does not exist",
                    execution_time=time.time() - start_time
                )
            
            # Check if conda environment exists
            if not self._conda_env_exists(env_name):
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message=f"Conda environment '{env_name}' not found",
                    error="Target environment does not exist",
                    execution_time=time.time() - start_time
                )
            
            # Install requirements using conda run
            conda_cmd = self._get_conda_command()
            install_cmd = f"{conda_cmd} run -n {env_name} pip install --no-cache-dir -r {req_path}"
            
            result = self.platform_utils.execute_command(install_cmd, timeout=900)  # 15 minutes
            
            if not result.success:
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message=f"Failed to install requirements from {req_path}",
                    error=result.stderr,
                    execution_time=time.time() - start_time
                )
            
            self.logger.info(f"Requirements installed successfully from {req_path}")
            return InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message=f"Requirements installed successfully from {req_path}",
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Requirements installation failed: {e}")
            return InstallationResult(
                success=False,
                status=InstallationStatus.FAILED,
                message="Requirements installation failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def install_ray(self, env_name: str = "zansoc") -> InstallationResult:
        """Install Ray with all components.
        
        Args:
            env_name: Conda environment name
            
        Returns:
            InstallationResult instance
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Installing Ray in environment '{env_name}'")
            
            # Check if conda environment exists
            if not self._conda_env_exists(env_name):
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message=f"Conda environment '{env_name}' not found",
                    error="Target environment does not exist",
                    execution_time=time.time() - start_time
                )
            
            # Check if Ray is already installed
            if self._is_ray_installed(env_name):
                ray_version = self._get_ray_version(env_name)
                self.logger.info(f"Ray already installed in '{env_name}' with version {ray_version}")
                return InstallationResult(
                    success=True,
                    status=InstallationStatus.SKIPPED,
                    message=f"Ray already installed with version {ray_version}",
                    version=ray_version,
                    execution_time=time.time() - start_time
                )
            
            # Install Ray with all components
            conda_cmd = self._get_conda_command()
            ray_install_cmd = f'{conda_cmd} run -n {env_name} pip install "ray[default,data,train,tune,rllib]"'
            
            result = self.platform_utils.execute_command(ray_install_cmd, timeout=1200)  # 20 minutes
            
            if not result.success:
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Failed to install Ray",
                    error=result.stderr,
                    execution_time=time.time() - start_time
                )
            
            # Verify Ray installation
            if not self._is_ray_installed(env_name):
                return InstallationResult(
                    success=False,
                    status=InstallationStatus.FAILED,
                    message="Ray installation verification failed",
                    error="Ray not found after installation",
                    execution_time=time.time() - start_time
                )
            
            # Get installed Ray version
            ray_version = self._get_ray_version(env_name)
            
            self.logger.info(f"Ray installed successfully with version {ray_version}")
            return InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message=f"Ray installed successfully with version {ray_version}",
                version=ray_version,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            self.logger.error(f"Ray installation failed: {e}")
            return InstallationResult(
                success=False,
                status=InstallationStatus.FAILED,
                message="Ray installation failed with exception",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def verify_installation(self) -> Dict[str, Any]:
        """Verify all installation components.
        
        Returns:
            Dictionary with verification results
        """
        try:
            self.logger.info("Verifying installation components")
            
            verification = {
                'miniconda': {
                    'installed': self._is_miniconda_installed(),
                    'version': self._get_miniconda_python_version() if self._is_miniconda_installed() else None,
                    'path': str(self.miniconda_path) if self._is_miniconda_installed() else None
                },
                'conda_env': {
                    'exists': self._conda_env_exists("zansoc"),
                    'python_version': self._get_conda_env_python_version("zansoc") if self._conda_env_exists("zansoc") else None
                },
                'repository': {
                    'cloned': self.repo_path.exists() and (self.repo_path / ".git").exists(),
                    'path': str(self.repo_path) if self.repo_path.exists() else None
                },
                'ray': {
                    'installed': self._is_ray_installed("zansoc") if self._conda_env_exists("zansoc") else False,
                    'version': self._get_ray_version("zansoc") if self._conda_env_exists("zansoc") and self._is_ray_installed("zansoc") else None
                }
            }
            
            # Overall status
            all_components = [
                verification['miniconda']['installed'],
                verification['conda_env']['exists'],
                verification['repository']['cloned'],
                verification['ray']['installed']
            ]
            
            verification['overall'] = {
                'complete': all(all_components),
                'components_ready': sum(all_components),
                'total_components': len(all_components)
            }
            
            self.logger.info(f"Verification complete: {verification['overall']['components_ready']}/{verification['overall']['total_components']} components ready")
            return verification
            
        except Exception as e:
            self.logger.error(f"Installation verification failed: {e}")
            return {
                'error': str(e),
                'overall': {'complete': False, 'components_ready': 0, 'total_components': 4}
            }
    
    def _get_miniconda_download_url(self) -> Optional[str]:
        """Get miniconda download URL for current platform.
        
        Returns:
            Download URL or None if unsupported
        """
        base_url = "https://repo.anaconda.com/miniconda"
        
        if self.system_info.platform == PlatformType.LINUX:
            if self.system_info.architecture == Architecture.X86_64:
                return f"{base_url}/Miniconda3-latest-Linux-x86_64.sh"
            elif self.system_info.architecture == Architecture.ARM64:
                return f"{base_url}/Miniconda3-latest-Linux-aarch64.sh"
        elif self.system_info.platform == PlatformType.MACOS:
            if self.system_info.architecture == Architecture.X86_64:
                return f"{base_url}/Miniconda3-latest-MacOSX-x86_64.sh"
            elif self.system_info.architecture == Architecture.ARM64:
                return f"{base_url}/Miniconda3-latest-MacOSX-arm64.sh"
        elif self.system_info.platform == PlatformType.WINDOWS:
            if self.system_info.architecture == Architecture.X86_64:
                return f"{base_url}/Miniconda3-latest-Windows-x86_64.exe"
        
        return None
    
    def _run_miniconda_installer(self, installer_path: Path) -> bool:
        """Run miniconda installer.
        
        Args:
            installer_path: Path to installer file
            
        Returns:
            True if installation successful
        """
        try:
            if self.system_info.platform == PlatformType.WINDOWS:
                # Windows installer
                install_cmd = f'"{installer_path}" /InstallationType=JustMe /RegisterPython=0 /S /D={self.miniconda_path}'
            else:
                # Unix installer
                install_cmd = f'bash "{installer_path}" -b -p "{self.miniconda_path}"'
            
            self.logger.info(f"Executing installer command: {install_cmd}")
            result = self.platform_utils.execute_command(install_cmd, timeout=900)  # 15 minutes
            
            if not result.success:
                self.logger.error(f"Installer failed with exit code {result.return_code}")
                self.logger.error(f"Installer stderr: {result.stderr}")
                self.logger.error(f"Installer stdout: {result.stdout}")
            
            return result.success
            
        except Exception as e:
            self.logger.error(f"Miniconda installer execution failed: {e}")
            return False
    
    def _is_miniconda_installed(self) -> bool:
        """Check if miniconda is installed.
        
        Returns:
            True if miniconda is installed
        """
        conda_executable = self.miniconda_path / ("Scripts" if self.system_info.platform == PlatformType.WINDOWS else "bin") / "conda"
        return conda_executable.exists()
    
    def _get_conda_command(self) -> str:
        """Get conda command path.
        
        Returns:
            Full path to conda command
        """
        if self.system_info.platform == PlatformType.WINDOWS:
            return str(self.miniconda_path / "Scripts" / "conda.exe")
        else:
            return str(self.miniconda_path / "bin" / "conda")
    
    def _get_miniconda_python_version(self) -> Optional[str]:
        """Get miniconda Python version.
        
        Returns:
            Python version string or None
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(f"{conda_cmd} --version")
            if result.success:
                # Try to get Python version from base environment
                python_cmd = f"{conda_cmd} run -n base python --version"
                python_result = self.platform_utils.execute_command(python_cmd)
                if python_result.success:
                    # Extract version from "Python 3.x.x"
                    version_parts = python_result.stdout.split()
                    if len(version_parts) >= 2:
                        return version_parts[1]
            return None
        except:
            return None
    
    def _conda_env_exists(self, env_name: str) -> bool:
        """Check if conda environment exists.
        
        Args:
            env_name: Environment name
            
        Returns:
            True if environment exists
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(f"{conda_cmd} env list")
            if result.success:
                return env_name in result.stdout
            return False
        except:
            return False
    
    def _get_conda_env_python_version(self, env_name: str) -> Optional[str]:
        """Get Python version in conda environment.
        
        Args:
            env_name: Environment name
            
        Returns:
            Python version string or None
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(f"{conda_cmd} run -n {env_name} python --version")
            if result.success:
                version_parts = result.stdout.split()
                if len(version_parts) >= 2:
                    return version_parts[1]
            return None
        except:
            return None
    
    def _is_ray_installed(self, env_name: str) -> bool:
        """Check if Ray is installed in conda environment.
        
        Args:
            env_name: Environment name
            
        Returns:
            True if Ray is installed
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(f"{conda_cmd} run -n {env_name} python -c \"import ray; print('Ray installed')\"")
            return result.success and "Ray installed" in result.stdout
        except:
            return False
    
    def _get_ray_version(self, env_name: str) -> Optional[str]:
        """Get Ray version in conda environment.
        
        Args:
            env_name: Environment name
            
        Returns:
            Ray version string or None
        """
        try:
            conda_cmd = self._get_conda_command()
            result = self.platform_utils.execute_command(f"{conda_cmd} run -n {env_name} python -c \"import ray; print(ray.__version__)\"")
            if result.success:
                return result.stdout.strip()
            return None
        except:
            return None