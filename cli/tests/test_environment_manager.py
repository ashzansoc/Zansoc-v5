"""Tests for EnvironmentManager class."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from zansoc_cli.environment_manager import (
    EnvironmentManager, InstallationResult, InstallationStatus
)
from zansoc_cli.platform_utils import PlatformUtils, PlatformType, Architecture, SystemInfo


class TestEnvironmentManager:
    """Test cases for EnvironmentManager."""
    
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
        
        # Create temporary directory for installations
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize environment manager with mocked platform utils
        self.env_manager = EnvironmentManager(self.mock_platform_utils)
        
        # Override install paths to use temp directory
        self.env_manager.install_base = Path(self.temp_dir)
        self.env_manager.miniconda_path = Path(self.temp_dir) / "miniconda"
        self.env_manager.repo_path = Path(self.temp_dir) / "zansoc-beta"
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test environment manager initialization."""
        assert self.env_manager.platform_utils == self.mock_platform_utils
        assert self.env_manager.system_info == self.mock_system_info
        assert self.env_manager.install_base.exists()
    
    @patch('tempfile.TemporaryDirectory')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_miniconda_download_url')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._run_miniconda_installer')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_miniconda_python_version')
    def test_install_miniconda_success(self, mock_get_version, mock_run_installer, 
                                     mock_get_url, mock_is_installed, mock_temp_dir):
        """Test successful miniconda installation."""
        # Mock temporary directory
        mock_temp_dir.return_value.__enter__.return_value = self.temp_dir
        
        # Mock installation flow
        mock_is_installed.side_effect = [False, True]  # Not installed, then installed
        mock_get_url.return_value = "https://example.com/miniconda.sh"
        mock_run_installer.return_value = True
        mock_get_version.return_value = "3.13.7"
        
        # Mock download - create the installer file
        installer_path = Path(self.temp_dir) / "miniconda_installer"
        installer_path.touch()
        self.mock_platform_utils.download_file.return_value = True
        
        result = self.env_manager.install_miniconda("3.13.7")
        
        assert isinstance(result, InstallationResult)
        assert result.success is True
        assert result.status == InstallationStatus.COMPLETED
        assert "3.13.7" in result.message
        assert result.version == "3.13.7"
        assert result.execution_time > 0
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_miniconda_python_version')
    def test_install_miniconda_already_installed(self, mock_get_version, mock_is_installed):
        """Test miniconda installation when already installed."""
        mock_is_installed.return_value = True
        mock_get_version.return_value = "3.13.5"
        
        result = self.env_manager.install_miniconda("3.13.7")
        
        assert result.success is True
        assert result.status == InstallationStatus.SKIPPED
        assert "already installed" in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_miniconda_download_url')
    def test_install_miniconda_unsupported_platform(self, mock_get_url, mock_is_installed):
        """Test miniconda installation on unsupported platform."""
        mock_is_installed.return_value = False
        mock_get_url.return_value = None  # Unsupported platform
        
        result = self.env_manager.install_miniconda("3.13.7")
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "Unsupported platform" in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_miniconda_download_url')
    def test_install_miniconda_download_failed(self, mock_get_url, mock_is_installed):
        """Test miniconda installation when download fails."""
        mock_is_installed.return_value = False
        mock_get_url.return_value = "https://example.com/miniconda.sh"
        self.mock_platform_utils.download_file.return_value = False
        
        result = self.env_manager.install_miniconda("3.13.7")
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "Failed to download" in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_conda_command')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_conda_env_python_version')
    def test_create_conda_environment_success(self, mock_get_env_version, mock_get_conda_cmd,
                                            mock_env_exists, mock_is_installed):
        """Test successful conda environment creation."""
        mock_is_installed.return_value = True
        mock_env_exists.side_effect = [False, True]  # Not exists, then exists
        mock_get_conda_cmd.return_value = "/path/to/conda"
        mock_get_env_version.return_value = "3.13.7"
        
        # Mock successful command execution
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.env_manager.create_conda_environment("3.13.7", "test_env")
        
        assert result.success is True
        assert result.status == InstallationStatus.COMPLETED
        assert "test_env" in result.message
        assert result.version == "3.13.7"
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    def test_create_conda_environment_no_miniconda(self, mock_is_installed):
        """Test conda environment creation when miniconda not installed."""
        mock_is_installed.return_value = False
        
        result = self.env_manager.create_conda_environment("3.13.7", "test_env")
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "Miniconda not installed" in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_conda_env_python_version')
    def test_create_conda_environment_already_exists(self, mock_get_env_version, 
                                                    mock_env_exists, mock_is_installed):
        """Test conda environment creation when environment already exists."""
        mock_is_installed.return_value = True
        mock_env_exists.return_value = True
        mock_get_env_version.return_value = "3.13.5"
        
        result = self.env_manager.create_conda_environment("3.13.7", "test_env")
        
        assert result.success is True
        assert result.status == InstallationStatus.SKIPPED
        assert "already exists" in result.message
    
    def test_clone_repository_success(self):
        """Test successful repository cloning."""
        repo_url = "https://github.com/test/repo.git"
        target_path = Path(self.temp_dir) / "test_repo"
        
        # Mock successful git clone
        def mock_execute_command(cmd, **kwargs):
            # Create the directory and .git when git clone is called
            if "git clone" in cmd:
                target_path.mkdir(parents=True, exist_ok=True)
                (target_path / ".git").mkdir(exist_ok=True)
            
            mock_result = Mock()
            mock_result.success = True
            return mock_result
        
        self.mock_platform_utils.execute_command.side_effect = mock_execute_command
        
        result = self.env_manager.clone_repository(repo_url, str(target_path))
        
        assert result.success is True
        assert result.status == InstallationStatus.COMPLETED
        assert str(target_path) in result.message
        assert result.installation_path == str(target_path)
    
    def test_clone_repository_already_exists(self):
        """Test repository cloning when repository already exists."""
        repo_url = "https://github.com/test/repo.git"
        target_path = Path(self.temp_dir) / "test_repo"
        
        # Create existing repository
        target_path.mkdir(parents=True)
        (target_path / ".git").mkdir()
        
        # Mock git remote get-url command
        mock_result = Mock()
        mock_result.success = True
        mock_result.stdout = repo_url
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.env_manager.clone_repository(repo_url, str(target_path))
        
        assert result.success is True
        assert result.status == InstallationStatus.SKIPPED
        assert "already cloned" in result.message
    
    def test_clone_repository_failed(self):
        """Test failed repository cloning."""
        repo_url = "https://github.com/test/repo.git"
        target_path = Path(self.temp_dir) / "test_repo"
        
        # Mock failed git clone
        mock_result = Mock()
        mock_result.success = False
        mock_result.stderr = "Repository not found"
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.env_manager.clone_repository(repo_url, str(target_path))
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "Failed to clone" in result.message
        assert result.error == "Repository not found"
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_conda_command')
    def test_install_requirements_success(self, mock_get_conda_cmd, mock_env_exists):
        """Test successful requirements installation."""
        # Create temporary requirements file
        req_file = Path(self.temp_dir) / "requirements.txt"
        req_file.write_text("requests>=2.25.0\nclick>=8.0.0\n")
        
        mock_env_exists.return_value = True
        mock_get_conda_cmd.return_value = "/path/to/conda"
        
        # Mock successful pip install
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.env_manager.install_requirements(str(req_file), "test_env")
        
        assert result.success is True
        assert result.status == InstallationStatus.COMPLETED
        assert str(req_file) in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    def test_install_requirements_no_env(self, mock_env_exists):
        """Test requirements installation when environment doesn't exist."""
        req_file = Path(self.temp_dir) / "requirements.txt"
        req_file.write_text("requests>=2.25.0\n")
        
        mock_env_exists.return_value = False
        
        result = self.env_manager.install_requirements(str(req_file), "test_env")
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "not found" in result.message
    
    def test_install_requirements_no_file(self):
        """Test requirements installation when file doesn't exist."""
        nonexistent_file = Path(self.temp_dir) / "nonexistent.txt"
        
        result = self.env_manager.install_requirements(str(nonexistent_file), "test_env")
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "not found" in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_ray_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_conda_command')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_ray_version')
    def test_install_ray_success(self, mock_get_ray_version, mock_get_conda_cmd,
                                mock_is_ray_installed, mock_env_exists):
        """Test successful Ray installation."""
        mock_env_exists.return_value = True
        mock_is_ray_installed.side_effect = [False, True]  # Not installed, then installed
        mock_get_conda_cmd.return_value = "/path/to/conda"
        mock_get_ray_version.return_value = "2.8.0"
        
        # Mock successful pip install
        mock_result = Mock()
        mock_result.success = True
        self.mock_platform_utils.execute_command.return_value = mock_result
        
        result = self.env_manager.install_ray("test_env")
        
        assert result.success is True
        assert result.status == InstallationStatus.COMPLETED
        assert "Ray installed successfully" in result.message
        assert result.version == "2.8.0"
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_ray_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_ray_version')
    def test_install_ray_already_installed(self, mock_get_ray_version, 
                                         mock_is_ray_installed, mock_env_exists):
        """Test Ray installation when already installed."""
        mock_env_exists.return_value = True
        mock_is_ray_installed.return_value = True
        mock_get_ray_version.return_value = "2.8.0"
        
        result = self.env_manager.install_ray("test_env")
        
        assert result.success is True
        assert result.status == InstallationStatus.SKIPPED
        assert "already installed" in result.message
        assert result.version == "2.8.0"
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    def test_install_ray_no_env(self, mock_env_exists):
        """Test Ray installation when environment doesn't exist."""
        mock_env_exists.return_value = False
        
        result = self.env_manager.install_ray("test_env")
        
        assert result.success is False
        assert result.status == InstallationStatus.FAILED
        assert "not found" in result.message
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_ray_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_miniconda_python_version')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_conda_env_python_version')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._get_ray_version')
    def test_verify_installation_complete(self, mock_get_ray_version, mock_get_env_version,
                                        mock_get_miniconda_version, mock_is_ray_installed,
                                        mock_env_exists, mock_is_miniconda_installed):
        """Test installation verification when all components are installed."""
        # Mock all components as installed
        mock_is_miniconda_installed.return_value = True
        mock_env_exists.return_value = True
        mock_is_ray_installed.return_value = True
        mock_get_miniconda_version.return_value = "3.13.7"
        mock_get_env_version.return_value = "3.13.7"
        mock_get_ray_version.return_value = "2.8.0"
        
        # Create fake repository
        self.env_manager.repo_path.mkdir(parents=True)
        (self.env_manager.repo_path / ".git").mkdir()
        
        verification = self.env_manager.verify_installation()
        
        assert verification['miniconda']['installed'] is True
        assert verification['conda_env']['exists'] is True
        assert verification['repository']['cloned'] is True
        assert verification['ray']['installed'] is True
        assert verification['overall']['complete'] is True
        assert verification['overall']['components_ready'] == 4
    
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_miniconda_installed')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._conda_env_exists')
    @patch('zansoc_cli.environment_manager.EnvironmentManager._is_ray_installed')
    def test_verify_installation_incomplete(self, mock_is_ray_installed, 
                                          mock_env_exists, mock_is_miniconda_installed):
        """Test installation verification when some components are missing."""
        # Mock partial installation
        mock_is_miniconda_installed.return_value = True
        mock_env_exists.return_value = False  # Environment missing
        mock_is_ray_installed.return_value = False  # Ray not installed
        
        verification = self.env_manager.verify_installation()
        
        assert verification['miniconda']['installed'] is True
        assert verification['conda_env']['exists'] is False
        assert verification['repository']['cloned'] is False  # No repo created
        assert verification['ray']['installed'] is False
        assert verification['overall']['complete'] is False
        assert verification['overall']['components_ready'] == 1
    
    def test_get_miniconda_download_url_linux_x86_64(self):
        """Test miniconda download URL for Linux x86_64."""
        self.env_manager.system_info.platform = PlatformType.LINUX
        self.env_manager.system_info.architecture = Architecture.X86_64
        
        url = self.env_manager._get_miniconda_download_url()
        
        assert url is not None
        assert "Linux-x86_64.sh" in url
    
    def test_get_miniconda_download_url_macos_arm64(self):
        """Test miniconda download URL for macOS ARM64."""
        self.env_manager.system_info.platform = PlatformType.MACOS
        self.env_manager.system_info.architecture = Architecture.ARM64
        
        url = self.env_manager._get_miniconda_download_url()
        
        assert url is not None
        assert "MacOSX-arm64.sh" in url
    
    def test_get_miniconda_download_url_windows_x86_64(self):
        """Test miniconda download URL for Windows x86_64."""
        self.env_manager.system_info.platform = PlatformType.WINDOWS
        self.env_manager.system_info.architecture = Architecture.X86_64
        
        url = self.env_manager._get_miniconda_download_url()
        
        assert url is not None
        assert "Windows-x86_64.exe" in url
    
    def test_get_miniconda_download_url_unsupported(self):
        """Test miniconda download URL for unsupported platform."""
        self.env_manager.system_info.platform = PlatformType.UNKNOWN
        self.env_manager.system_info.architecture = Architecture.UNKNOWN
        
        url = self.env_manager._get_miniconda_download_url()
        
        assert url is None
    
    def test_is_miniconda_installed_true(self):
        """Test miniconda installation check when installed."""
        # Create fake conda executable
        conda_dir = self.env_manager.miniconda_path / "bin"
        conda_dir.mkdir(parents=True)
        (conda_dir / "conda").touch()
        
        result = self.env_manager._is_miniconda_installed()
        assert result is True
    
    def test_is_miniconda_installed_false(self):
        """Test miniconda installation check when not installed."""
        result = self.env_manager._is_miniconda_installed()
        assert result is False
    
    def test_get_conda_command_unix(self):
        """Test conda command path for Unix systems."""
        self.env_manager.system_info.platform = PlatformType.LINUX
        
        cmd = self.env_manager._get_conda_command()
        
        assert cmd.endswith("bin/conda")
        assert str(self.env_manager.miniconda_path) in cmd
    
    def test_get_conda_command_windows(self):
        """Test conda command path for Windows."""
        self.env_manager.system_info.platform = PlatformType.WINDOWS
        
        cmd = self.env_manager._get_conda_command()
        
        assert cmd.endswith("Scripts/conda.exe")
        assert str(self.env_manager.miniconda_path) in cmd