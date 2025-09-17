#!/usr/bin/env python3
"""Demo script to showcase platform utilities functionality."""

from zansoc_cli.platform_utils import PlatformUtils
from zansoc_cli.cli_interface import CLIInterface
from zansoc_cli.config_manager import ConfigManager


def demo_platform_utilities():
    """Demonstrate platform utilities features."""
    print("🔍 ZanSoc Platform Utilities Demo\n")
    
    # Initialize utilities
    platform_utils = PlatformUtils()
    config = ConfigManager()
    cli = CLIInterface(config)
    
    # Demo 1: Platform Detection
    print("1. Platform Detection:")
    platform_info = platform_utils.detect_platform()
    
    headers = ["Property", "Value"]
    rows = [
        ["Platform", platform_info['platform'].value],
        ["Architecture", platform_info['architecture'].value],
        ["Platform String", platform_info['platform_string']],
        ["Is Linux", str(platform_info['is_linux'])],
        ["Is macOS", str(platform_info['is_macos'])],
        ["Is Windows", str(platform_info['is_windows'])],
        ["Is ARM", str(platform_info['is_arm'])],
        ["Is x86", str(platform_info['is_x86'])],
    ]
    cli.show_table("Platform Information", headers, rows)
    
    # Demo 2: System Information
    print("\n2. System Information:")
    system_info = platform_utils.get_system_info()
    
    system_rows = [
        ["OS Name", system_info.os_name],
        ["OS Version", system_info.os_version],
        ["Python Version", system_info.python_version],
        ["CPU Count", str(system_info.cpu_count)],
        ["Memory Total", f"{system_info.memory_total} GB"],
        ["Disk Free", f"{system_info.disk_free} GB"],
        ["Hostname", system_info.hostname],
        ["Username", system_info.username],
    ]
    cli.show_table("System Information", headers, system_rows)
    
    # Demo 3: Prerequisites Check
    print("\n3. Prerequisites Check:")
    missing = platform_utils.check_prerequisites()
    
    if missing:
        cli.show_warning("Some prerequisites are missing:")
        for item in missing:
            print(f"  ❌ {item}")
    else:
        cli.show_success("All prerequisites are met!")
    
    # Demo 4: Command Execution
    print("\n4. Command Execution:")
    
    # Test simple command
    result = platform_utils.execute_command("echo 'Hello from ZanSoc!'")
    if result.success:
        cli.show_success(f"Command executed successfully: {result.stdout}")
        print(f"   Execution time: {result.execution_time:.3f}s")
    else:
        cli.show_error(f"Command failed: {result.stderr}")
    
    # Test system info command
    if platform_info['is_macos']:
        result = platform_utils.execute_command("sw_vers")
    elif platform_info['is_linux']:
        result = platform_utils.execute_command("uname -a")
    else:
        result = platform_utils.execute_command("ver", shell=True)
    
    if result.success:
        print(f"   System info: {result.stdout[:100]}...")
    
    # Demo 5: Network Interfaces
    print("\n5. Network Interfaces:")
    interfaces = platform_utils.get_network_interfaces()
    
    if interfaces:
        interface_rows = []
        for name, info in interfaces.items():
            status = "Up" if info['is_up'] else "Down"
            addresses = len(info['addresses'])
            is_loopback = "Yes" if info['is_loopback'] else "No"
            
            interface_rows.append([name, status, str(addresses), is_loopback])
        
        cli.show_table("Network Interfaces", 
                      ["Interface", "Status", "Addresses", "Loopback"], 
                      interface_rows)
    else:
        cli.show_warning("No network interfaces found")
    
    # Demo 6: System Resources
    print("\n6. System Resources:")
    resources = platform_utils.get_system_resources()
    
    if resources:
        resource_rows = [
            ["CPU Usage", f"{resources['cpu']['percent']:.1f}%"],
            ["CPU Cores", f"{resources['cpu']['count']} physical, {resources['cpu']['count_logical']} logical"],
            ["Memory Usage", f"{resources['memory']['percent']:.1f}%"],
            ["Memory Available", f"{resources['memory']['available'] / (1024**3):.1f} GB"],
            ["Disk Usage", f"{resources['disk']['percent']:.1f}%"],
            ["Disk Free", f"{resources['disk']['free'] / (1024**3):.1f} GB"],
        ]
        
        if resources.get('load_average'):
            load_avg = resources['load_average']
            resource_rows.append(["Load Average", f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"])
        
        cli.show_table("System Resources", ["Resource", "Value"], resource_rows)
    
    # Demo 7: Available Ports
    print("\n7. Available Ports:")
    ports = platform_utils.get_available_ports(8000, 5)
    if ports:
        cli.show_success(f"Found {len(ports)} available ports: {', '.join(map(str, ports))}")
    else:
        cli.show_warning("No available ports found in range")
    
    # Demo 8: Environment Information
    print("\n8. Environment Variables:")
    env_info = platform_utils.get_environment_info()
    
    if env_info:
        env_rows = [[key, value[:50] + "..." if len(value) > 50 else value] 
                   for key, value in env_info.items()]
        cli.show_table("Environment Variables", ["Variable", "Value"], env_rows)
    
    print("\n🎉 Platform Utilities Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("• Cross-platform detection (Linux, macOS, Windows)")
    print("• System resource monitoring")
    print("• Command execution with timeout and error handling")
    print("• Network interface discovery")
    print("• Prerequisites checking")
    print("• File download capabilities")
    print("• Port availability checking")


if __name__ == "__main__":
    demo_platform_utilities()