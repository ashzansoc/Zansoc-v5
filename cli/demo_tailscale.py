#!/usr/bin/env python3
"""Demo script to showcase Tailscale manager functionality."""

from zansoc_cli.tailscale_manager import TailscaleManager, TailscaleStatus, TailscaleDevice
from zansoc_cli.platform_utils import PlatformUtils
from zansoc_cli.cli_interface import CLIInterface
from zansoc_cli.config_manager import ConfigManager


def demo_tailscale_manager():
    """Demonstrate Tailscale manager features."""
    print("🌐 ZanSoc Tailscale Manager Demo\n")
    
    # Initialize components
    platform_utils = PlatformUtils()
    tailscale_manager = TailscaleManager(platform_utils)
    config = ConfigManager()
    cli = CLIInterface(config)
    
    # Demo 1: System Information
    print("1. System Information:")
    system_info = platform_utils.get_system_info()
    
    system_rows = [
        ["Platform", f"{system_info.platform.value}-{system_info.architecture.value}"],
        ["OS", f"{system_info.os_name} {system_info.os_version}"],
        ["Hostname", system_info.hostname],
        ["Username", system_info.username],
    ]
    cli.show_table("System Information", ["Property", "Value"], system_rows)
    
    # Demo 2: Tailscale Status Check
    print("\n2. Current Tailscale Status:")
    network_status = tailscale_manager.get_network_status()
    
    status_rows = [
        ["Installed", "✅ Yes" if network_status.get('installed') else "❌ No"],
        ["Version", network_status.get('version', 'N/A')],
        ["Status", network_status.get('status', TailscaleStatus.NOT_INSTALLED).value.title()],
        ["IP Address", network_status.get('ip_address', 'N/A')],
    ]
    cli.show_table("Tailscale Status", ["Property", "Value"], status_rows)
    
    # Demo 3: Installation Methods by Platform
    print("\n3. Platform-Specific Installation Methods:")
    
    installation_methods = [
        ("Linux x86_64", "curl -fsSL https://tailscale.com/install.sh | sh"),
        ("Linux ARM64", "Official script + ARM64 fallback if needed"),
        ("macOS x86_64", "curl -fsSL https://tailscale.com/install.sh | sh"),
        ("macOS ARM64", "Official script + ARM64 fallback if needed"),
        ("Windows x86_64", "Download and run tailscale-setup.exe"),
    ]
    
    method_rows = []
    for platform, method in installation_methods:
        method_display = method[:60] + "..." if len(method) > 60 else method
        method_rows.append([platform, method_display])
    
    cli.show_table("Installation Methods", ["Platform", "Method"], method_rows)
    
    # Demo 4: Tailscale Commands
    print("\n4. Tailscale Commands:")
    
    tailscale_cmd = tailscale_manager._get_tailscale_command()
    
    command_rows = [
        ["Check Version", f"{tailscale_cmd} version"],
        ["Check Status", f"{tailscale_cmd} status"],
        ["Get IP Address", f"{tailscale_cmd} ip -4"],
        ["Authenticate", f"sudo {tailscale_cmd} up --auth-key=<AUTH_KEY>"],
        ["Get JSON Status", f"{tailscale_cmd} status --json"],
        ["Logout", f"sudo {tailscale_cmd} logout"],
    ]
    
    cli.show_table("Tailscale Commands", ["Operation", "Command"], command_rows)
    
    # Demo 5: Simulated Installation Results
    print("\n5. Simulated Installation Results:")
    
    from zansoc_cli.tailscale_manager import TailscaleResult
    
    demo_results = [
        TailscaleResult(
            success=True,
            status=TailscaleStatus.INSTALLED,
            message="Tailscale installed successfully: 1.88.1",
            execution_time=45.2
        ),
        TailscaleResult(
            success=True,
            status=TailscaleStatus.RUNNING,
            message="Tailscale authenticated successfully, IP: 100.64.0.1",
            ip_address="100.64.0.1",
            execution_time=8.1
        ),
        TailscaleResult(
            success=True,
            status=TailscaleStatus.INSTALLED,
            message="Tailscale already installed: 1.88.1",
            execution_time=0.5
        ),
        TailscaleResult(
            success=False,
            status=TailscaleStatus.ERROR,
            message="Tailscale installation failed",
            error="Network timeout during download",
            execution_time=120.0
        )
    ]
    
    result_rows = []
    for i, result in enumerate(demo_results, 1):
        status_icon = "✅" if result.success else "❌"
        status_text = f"{status_icon} {result.status.value.title()}"
        time_text = f"{result.execution_time:.1f}s"
        
        result_rows.append([
            f"Result {i}",
            status_text,
            result.message[:40] + "..." if len(result.message) > 40 else result.message,
            time_text
        ])
    
    cli.show_table("Installation Results", 
                  ["Result", "Status", "Message", "Time"], 
                  result_rows)
    
    # Demo 6: Device Information Example
    print("\n6. Example Device Information:")
    
    example_device = TailscaleDevice(
        id="device123abc",
        name="zansoc-provider-01",
        ip="100.64.0.1",
        os="linux",
        online=True,
        last_seen="2025-01-15T10:30:00Z",
        tags=["tag:provider", "tag:zansoc"]
    )
    
    device_rows = [
        ["Device ID", example_device.id],
        ["Hostname", example_device.name],
        ["Tailscale IP", example_device.ip],
        ["Operating System", example_device.os.title()],
        ["Online Status", "🟢 Online" if example_device.online else "🔴 Offline"],
        ["Last Seen", example_device.last_seen or "N/A"],
        ["Tags", ", ".join(example_device.tags) if example_device.tags else "None"],
    ]
    
    cli.show_table("Device Information", ["Property", "Value"], device_rows)
    
    # Demo 7: Network Connectivity Test
    print("\n7. Network Connectivity Testing:")
    
    connectivity_tests = [
        ("ZanSoc Master Node", "100.101.84.71", "✅ Connected"),
        ("Peer Provider Node", "100.64.0.2", "✅ Connected"),
        ("External Service", "8.8.8.8", "✅ Connected"),
        ("Unreachable Node", "100.64.0.99", "❌ Timeout"),
    ]
    
    connectivity_rows = []
    for name, ip, status in connectivity_tests:
        connectivity_rows.append([name, ip, status])
    
    cli.show_table("Connectivity Tests", ["Target", "IP Address", "Status"], connectivity_rows)
    
    # Demo 8: Configuration Information
    print("\n8. Configuration Information:")
    
    auth_key = config.get("tailscale.auth_key", "Not configured")
    auth_key_display = auth_key[:20] + "..." if len(auth_key) > 20 else auth_key
    
    config_rows = [
        ["Auth Key", auth_key_display],
        ["Master Address", config.get("cluster.master_address", "Not configured")],
        ["Installation Path", "~/.zansoc/tailscale (if manual install)"],
        ["Config File", "/etc/tailscale/ (system-wide)"],
    ]
    
    cli.show_table("Configuration", ["Setting", "Value"], config_rows)
    
    print("\n🎉 Tailscale Manager Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("• Cross-platform Tailscale installation")
    print("• Primary installation via official script")
    print("• ARM64 fallback installation method")
    print("• Authentication with auth keys")
    print("• Network status monitoring")
    print("• Device information retrieval")
    print("• Connectivity verification")
    print("• Comprehensive error handling")
    print("• Integration with ZanSoc configuration")


if __name__ == "__main__":
    demo_tailscale_manager()