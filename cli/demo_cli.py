#!/usr/bin/env python3
"""Demo script to showcase CLI functionality."""

from zansoc_cli.cli_interface import CLIInterface
from zansoc_cli.config_manager import ConfigManager
from zansoc_cli.models import Provider, ProviderStatus
from datetime import datetime


def demo_cli_features():
    """Demonstrate CLI features without full authentication."""
    print("🚀 ZanSoc CLI Feature Demo\n")
    
    # Initialize CLI
    config = ConfigManager()
    cli = CLIInterface(config)
    
    # Demo 1: Banner
    print("1. Application Banner:")
    cli.show_banner()
    
    # Demo 2: Info Panel
    print("\n2. Info Panel:")
    cli.show_info_panel(
        "Demo Panel",
        "This is a demonstration of the info panel feature.\nIt supports multi-line content and styling.",
        "blue"
    )
    
    # Demo 3: Messages
    print("\n3. Message Types:")
    cli.show_success("This is a success message")
    cli.show_warning("This is a warning message")
    cli.show_error("This is an error message")
    
    # Demo 4: Table
    print("\n4. Table Display:")
    headers = ["Feature", "Status", "Description"]
    rows = [
        ["Authentication", "✅ Complete", "Username/password authentication"],
        ["Provider Registration", "✅ Complete", "UUID-based provider IDs"],
        ["Database Storage", "✅ Complete", "SQLite with full CRUD"],
        ["Progress Tracking", "✅ Complete", "Rich progress bars and spinners"],
        ["Menu System", "✅ Complete", "Interactive menu navigation"],
    ]
    cli.show_table("CLI Features", headers, rows)
    
    # Demo 5: Provider List
    print("\n5. Provider List Display:")
    demo_providers = [
        Provider(
            id="zansoc-demo001",
            username="demo_user1",
            status=ProviderStatus.ACTIVE,
            created_at=datetime.now(),
            platform="linux-x86_64",
            tailscale_ip="100.64.0.1",
            ray_node_id="ray-node-001"
        ),
        Provider(
            id="zansoc-demo002",
            username="demo_user2", 
            status=ProviderStatus.REGISTERING,
            created_at=datetime.now(),
            platform="darwin-arm64"
        )
    ]
    cli.show_provider_list(demo_providers)
    
    # Demo 6: Congratulations Screen
    print("\n6. Congratulations Screen:")
    provider_info = {
        'id': 'zansoc-demo001',
        'tailscale_ip': '100.64.0.1',
        'ray_status': 'connected',
        'platform': 'linux-x86_64'
    }
    cli.show_congratulations(provider_info)
    
    print("\n🎉 CLI Demo Complete!")
    print("\nTo run the full CLI with authentication:")
    print("  ./run_cli.sh")
    print("\nCredentials: admin / admin")


if __name__ == "__main__":
    demo_cli_features()