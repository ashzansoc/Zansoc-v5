#!/usr/bin/env python3
"""Demo script for RayManager functionality."""

import sys
import time
from pathlib import Path

# Add the CLI package to the path
sys.path.insert(0, str(Path(__file__).parent))

from zansoc_cli.ray_manager import RayManager
from zansoc_cli.platform_utils import PlatformUtils


def print_separator(title: str):
    """Print a section separator."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def print_status(status: str, success: bool = True):
    """Print status with color coding."""
    symbol = "✓" if success else "✗"
    print(f"{symbol} {status}")


def demo_ray_manager():
    """Demonstrate Ray manager functionality."""
    print_separator("Ray Manager Demo")
    
    # Initialize Ray manager
    print("Initializing Ray manager...")
    platform_utils = PlatformUtils()
    ray_manager = RayManager(platform_utils)
    
    system_info = platform_utils.get_system_info()
    print(f"Platform: {system_info.platform.value}")
    print(f"Architecture: {system_info.architecture.value}")
    print(f"Python Version: {system_info.python_version}")
    
    print_separator("Ray Availability Check")
    
    # Check if Ray is available
    env_name = "zansoc"
    ray_available = ray_manager._is_ray_available(env_name)
    print_status(f"Ray available in '{env_name}' environment: {ray_available}", ray_available)
    
    if ray_available:
        ray_version = ray_manager._get_ray_version(env_name)
        print_status(f"Ray version: {ray_version}", ray_version is not None)
    
    print_separator("Cluster Connectivity Test")
    
    # Test cluster connectivity
    cluster_address = "100.101.84.71:6379"
    print(f"Testing connectivity to {cluster_address}...")
    
    connectivity = ray_manager.test_cluster_connectivity(cluster_address, timeout=5)
    print_status(f"Cluster connectivity: {connectivity}", connectivity)
    
    print_separator("Ray Environment Setup")
    
    # Setup Ray environment
    print("Setting up Ray environment variables...")
    ray_manager._setup_ray_environment()
    print_status("Ray environment configured")
    
    print_separator("Node Status Check")
    
    # Get current node status
    print("Checking current node status...")
    node_status = ray_manager.get_node_status(env_name)
    
    print(f"Ray Available: {node_status.get('ray_available', False)}")
    print(f"Ray Version: {node_status.get('ray_version', 'Unknown')}")
    print(f"Connected: {node_status.get('connected', False)}")
    print(f"Node ID: {node_status.get('node_id', 'None')}")
    print(f"Cluster Address: {node_status.get('cluster_address', 'None')}")
    print(f"Connection Active: {node_status.get('connection_active', False)}")
    
    print_separator("Connection Health Check")
    
    # Get connection health
    print("Checking connection health...")
    health = ray_manager.get_connection_health(env_name)
    
    print(f"Ray Available: {health.get('ray_available', False)}")
    print(f"Connected: {health.get('connected', False)}")
    print(f"Node ID: {health.get('node_id', 'None')}")
    print(f"Cluster Address: {health.get('cluster_address', 'None')}")
    print(f"Errors: {health.get('errors', [])}")
    
    if ray_available and connectivity:
        print_separator("Ray Cluster Connection Test")
        
        # Attempt to connect to cluster
        print(f"Attempting to connect to Ray cluster at {cluster_address}...")
        print("Note: This will only work if the cluster is actually running and accessible")
        
        cluster_password = "zansoc_secure_password_change_me"
        connection_result = ray_manager.connect_to_cluster(
            cluster_address, 
            cluster_password, 
            env_name
        )
        
        print(f"Connection Success: {connection_result.success}")
        print(f"Status: {connection_result.status.value}")
        print(f"Message: {connection_result.message}")
        print(f"Execution Time: {connection_result.execution_time:.2f}s")
        
        if connection_result.error:
            print(f"Error: {connection_result.error}")
        
        if connection_result.success:
            print_separator("Cluster Information")
            
            # Get cluster info
            cluster_info = ray_manager.get_cluster_info(env_name)
            if cluster_info:
                print(f"Cluster ID: {cluster_info.cluster_id}")
                print(f"Head Node: {cluster_info.head_node}")
                print(f"Total Nodes: {cluster_info.total_nodes}")
                print(f"Active Nodes: {cluster_info.active_nodes}")
                print(f"Total Resources: {cluster_info.total_resources}")
                print(f"Cluster Status: {cluster_info.cluster_status}")
                print(f"Ray Version: {cluster_info.ray_version}")
            
            print_separator("Node Registration Verification")
            
            # Verify node registration
            registration_verified = ray_manager.verify_node_registration(env_name)
            print_status(f"Node registration verified: {registration_verified}", registration_verified)
            
            print_separator("Disconnection Test")
            
            # Disconnect from cluster
            print("Disconnecting from Ray cluster...")
            disconnect_result = ray_manager.disconnect_from_cluster(env_name)
            print_status(f"Disconnection successful: {disconnect_result}", disconnect_result)
    
    else:
        print_separator("Connection Skipped")
        print("Skipping connection test due to:")
        if not ray_available:
            print("- Ray not available in environment")
        if not connectivity:
            print("- Cluster not reachable")
        print("\nTo test connection:")
        print("1. Install Ray in the 'zansoc' conda environment")
        print("2. Ensure the Ray cluster is running and accessible")
        print("3. Run this demo again")
    
    print_separator("Demo Complete")
    print("Ray manager demo completed successfully!")


if __name__ == "__main__":
    try:
        demo_ray_manager()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)