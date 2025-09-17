#!/usr/bin/env python3
"""Demo script to showcase environment manager functionality."""

import tempfile
from pathlib import Path
from zansoc_cli.environment_manager import EnvironmentManager
from zansoc_cli.platform_utils import PlatformUtils
from zansoc_cli.cli_interface import CLIInterface
from zansoc_cli.config_manager import ConfigManager


def demo_environment_manager():
    """Demonstrate environment manager features."""
    print("🔧 ZanSoc Environment Manager Demo\n")
    
    # Initialize components
    platform_utils = PlatformUtils()
    env_manager = EnvironmentManager(platform_utils)
    config = ConfigManager()
    cli = CLIInterface(config)
    
    # Demo 1: System Information
    print("1. System Information:")
    system_info = platform_utils.get_system_info()
    
    system_rows = [
        ["Platform", f"{system_info.platform.value}-{system_info.architecture.value}"],
        ["OS", f"{system_info.os_name} {system_info.os_version}"],
        ["Python", system_info.python_version],
        ["CPU Cores", str(system_info.cpu_count)],
        ["Memory", f"{system_info.memory_total} GB"],
        ["Disk Free", f"{system_info.disk_free} GB"],
        ["Username", system_info.username],
    ]
    cli.show_table("System Information", ["Property", "Value"], system_rows)
    
    # Demo 2: Installation Paths
    print("\n2. Installation Paths:")
    path_rows = [
        ["Install Base", str(env_manager.install_base)],
        ["Miniconda Path", str(env_manager.miniconda_path)],
        ["Repository Path", str(env_manager.repo_path)],
    ]
    cli.show_table("Installation Paths", ["Component", "Path"], path_rows)
    
    # Demo 3: Miniconda Download URLs
    print("\n3. Platform-Specific Download URLs:")
    
    # Test different platforms
    test_platforms = [
        ("Linux x86_64", "linux", "x86_64", "Linux-x86_64.sh"),
        ("Linux ARM64", "linux", "aarch64", "Linux-aarch64.sh"),
        ("macOS x86_64", "darwin", "x86_64", "MacOSX-x86_64.sh"),
        ("macOS ARM64", "darwin", "arm64", "MacOSX-arm64.sh"),
        ("Windows x86_64", "windows", "x86_64", "Windows-x86_64.exe"),
    ]
    
    url_rows = []
    for platform_name, platform, arch, expected_suffix in test_platforms:
        # Temporarily modify system info for demo
        original_platform = env_manager.system_info.platform
        original_arch = env_manager.system_info.architecture
        
        from zansoc_cli.platform_utils import PlatformType, Architecture
        platform_map = {
            'linux': PlatformType.LINUX,
            'darwin': PlatformType.MACOS,
            'windows': PlatformType.WINDOWS
        }
        arch_map = {
            'x86_64': Architecture.X86_64,
            'aarch64': Architecture.ARM64,
            'arm64': Architecture.ARM64
        }
        
        env_manager.system_info.platform = platform_map[platform]
        env_manager.system_info.architecture = arch_map[arch]
        
        url = env_manager._get_miniconda_download_url()
        url_display = url[-50:] + "..." if url and len(url) > 50 else (url or "Not supported")
        url_rows.append([platform_name, url_display])
        
        # Restore original values
        env_manager.system_info.platform = original_platform
        env_manager.system_info.architecture = original_arch
    
    cli.show_table("Miniconda Download URLs", ["Platform", "URL"], url_rows)
    
    # Demo 4: Installation Status Check
    print("\n4. Current Installation Status:")
    verification = env_manager.verify_installation()
    
    status_rows = [
        ["Miniconda", "✅ Installed" if verification['miniconda']['installed'] else "❌ Not Installed"],
        ["Conda Environment", "✅ Exists" if verification['conda_env']['exists'] else "❌ Missing"],
        ["Repository", "✅ Cloned" if verification['repository']['cloned'] else "❌ Not Cloned"],
        ["Ray", "✅ Installed" if verification['ray']['installed'] else "❌ Not Installed"],
    ]
    
    if verification['miniconda']['version']:
        status_rows[0][1] += f" (Python {verification['miniconda']['version']})"
    if verification['conda_env']['python_version']:
        status_rows[1][1] += f" (Python {verification['conda_env']['python_version']})"
    if verification['ray']['version']:
        status_rows[3][1] += f" (v{verification['ray']['version']})"
    
    cli.show_table("Installation Status", ["Component", "Status"], status_rows)
    
    # Demo 5: Prerequisites Check
    print("\n5. Prerequisites Check:")
    missing = platform_utils.check_prerequisites()
    
    if missing:
        cli.show_warning("Some prerequisites are missing:")
        for item in missing:
            print(f"  ❌ {item}")
    else:
        cli.show_success("All prerequisites are met!")
    
    # Demo 6: Simulated Installation Results
    print("\n6. Simulated Installation Results:")
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Simulate different installation results
        from zansoc_cli.environment_manager import InstallationResult, InstallationStatus
        
        demo_results = [
            InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message="Miniconda installed successfully with Python 3.13.7",
                installation_path=str(temp_path / "miniconda"),
                version="3.13.7",
                execution_time=45.2
            ),
            InstallationResult(
                success=True,
                status=InstallationStatus.SKIPPED,
                message="Conda environment 'zansoc' already exists with Python 3.13.7",
                version="3.13.7",
                execution_time=1.1
            ),
            InstallationResult(
                success=True,
                status=InstallationStatus.COMPLETED,
                message="Repository cloned successfully",
                installation_path=str(temp_path / "zansoc-beta"),
                execution_time=12.8
            ),
            InstallationResult(
                success=False,
                status=InstallationStatus.FAILED,
                message="Ray installation failed",
                error="Network timeout during download",
                execution_time=180.0
            )
        ]
        
        result_rows = []
        for i, result in enumerate(demo_results, 1):
            status_icon = "✅" if result.success else "❌"
            status_text = f"{status_icon} {result.status.value.title()}"
            time_text = f"{result.execution_time:.1f}s"
            
            result_rows.append([
                f"Step {i}",
                status_text,
                result.message[:40] + "..." if len(result.message) > 40 else result.message,
                time_text
            ])
        
        cli.show_table("Installation Results", 
                      ["Step", "Status", "Message", "Time"], 
                      result_rows)
    
    # Demo 7: Environment Commands
    print("\n7. Environment Commands:")
    
    # Show what commands would be executed
    conda_cmd = env_manager._get_conda_command()
    
    command_rows = [
        ["Create Environment", f"{conda_cmd} create -n zansoc python=3.13.7 -y"],
        ["Install Requirements", f"{conda_cmd} run -n zansoc pip install -r requirements.txt"],
        ["Install Ray", f'{conda_cmd} run -n zansoc pip install "ray[default,data,train,tune,rllib]"'],
        ["Clone Repository", "git clone https://github.com/zansoc/zansoc-beta.git"],
    ]
    
    cli.show_table("Environment Commands", ["Operation", "Command"], command_rows)
    
    print("\n🎉 Environment Manager Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("• Cross-platform miniconda installation")
    print("• Conda environment creation with specific Python versions")
    print("• Git repository cloning with verification")
    print("• Python package installation (requirements.txt + Ray)")
    print("• Installation verification and status checking")
    print("• Comprehensive error handling and retry logic")
    print("• Platform-specific installation paths and commands")


if __name__ == "__main__":
    demo_environment_manager()