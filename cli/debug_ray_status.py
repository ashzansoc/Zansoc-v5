#!/usr/bin/env python3
"""
Debug script to check Ray status after onboarding.
Run this to see detailed Ray connection information.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🚀 ZanSoc Ray Status Debug Tool")
    print("=" * 60)
    
    # Set PATH to include local bin
    os.environ['PATH'] = f"{os.path.expanduser('~')}/.local/bin:{os.environ.get('PATH', '')}"
    os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'
    
    # Check 1: Ray CLI availability
    run_command("which ray", "Ray CLI Location")
    run_command("ray --version", "Ray CLI Version")
    
    # Check 2: Ray processes
    run_command("ps aux | grep -E '(ray|gcs|raylet)' | grep -v grep", "Ray Processes")
    
    # Check 3: Ray status
    run_command("ray status", "Ray Status")
    
    # Check 4: Python Ray import
    python_test = '''
import ray
import os
print("Ray version:", ray.__version__)
print("Ray initialized:", ray.is_initialized())

if ray.is_initialized():
    print("Cluster Address:", ray.get_runtime_context().gcs_address)
    print("Node ID:", ray.get_runtime_context().node_id.hex())
    print("Cluster Resources:", ray.cluster_resources())
else:
    print("Ray is not initialized - checking if we can connect...")
    try:
        ray.init(address="auto")
        print("Connected to local Ray cluster")
        print("Cluster Address:", ray.get_runtime_context().gcs_address)
        print("Node ID:", ray.get_runtime_context().node_id.hex())
        ray.shutdown()
    except Exception as e:
        print("Failed to connect:", e)
'''
    
    run_command(f'python3 -c "{python_test}"', "Python Ray Test")
    
    # Check 5: Network connectivity to ZanSoc cluster
    run_command("ping -c 3 100.101.84.71", "Ping ZanSoc Cluster")
    
    # Check 6: Tailscale status
    run_command("tailscale status", "Tailscale Status")
    run_command("tailscale ip -4", "Tailscale IP")
    
    # Check 7: Try manual Ray connection
    manual_connect = '''
import ray
import os
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"
try:
    ray.init(address="100.101.84.71:6379", _redis_password="zansoc_secure_password_change_me")
    print("Successfully connected to ZanSoc cluster!")
    print("Cluster Address:", ray.get_runtime_context().gcs_address)
    print("Node ID:", ray.get_runtime_context().node_id.hex())
    print("Cluster Resources:", ray.cluster_resources())
    ray.shutdown()
except Exception as e:
    print("Failed to connect to ZanSoc cluster:", e)
'''
    
    run_command(f'python3 -c "{manual_connect}"', "Manual ZanSoc Cluster Connection Test")
    
    print("\n" + "=" * 60)
    print("🏁 Debug complete!")
    print("\nIf Ray processes are running but not connected to the cluster,")
    print("try stopping Ray and reconnecting:")
    print("  ray stop")
    print("  export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1")
    print("  ray start --address='100.101.84.71:6379' --redis-password='zansoc_secure_password_change_me'")

if __name__ == "__main__":
    main()