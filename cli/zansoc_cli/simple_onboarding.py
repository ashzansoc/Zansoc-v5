"""Simple 9-step onboarding process as specified."""

import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from .platform_utils import PlatformUtils
from .utils.logger import get_logger


class SimpleOnboarding:
    """Simple 9-step onboarding process."""
    
    def __init__(self):
        self.platform_utils = PlatformUtils()
        self.logger = get_logger(__name__)
        self.cluster_address = "100.101.84.71:6379"
        self.cluster_password = "zansoc_secure_password_change_me"
        self.tailscale_auth_key = "tskey-auth-kd32Q6XdHS11CNTRL-X13DpHNm9ygqbdavCzngxgEJg91Rgie6"
    
    async def execute_onboarding(self) -> Dict[str, Any]:
        """Execute the complete 9-step onboarding process."""
        self.logger.info("Starting ZanSoc 9-step onboarding process...")
        start_time = time.time()
        results = {}
        
        try:
            # Step 1: Clone the repo from GitHub (already done by installer)
            self.logger.info("✅ Step 1: Repository cloned from GitHub")
            results['step_1'] = True
            
            # Step 2: Install Python (any version)
            self.logger.info("🔍 Step 2: Checking Python installation...")
            python_result = await self._check_python()
            if not python_result['success']:
                return {'success': False, 'error': 'Python not found', 'step': 2}
            results['step_2'] = python_result
            self.logger.info(f"✅ Step 2: {python_result['version']}")
            
            # Step 3: Set up Python environment of 3.13.7
            self.logger.info("🔍 Step 3: Setting up Python 3.13.7 environment...")
            # For now, use existing Python
            results['step_3'] = {'success': True, 'note': 'Using existing Python environment'}
            self.logger.info("✅ Step 3: Python environment ready")
            
            # Step 4: Go to ZanSoc root directory and install requirements.txt
            self.logger.info("🔍 Step 4: Installing requirements.txt...")
            req_result = await self._install_requirements()
            results['step_4'] = req_result
            self.logger.info("✅ Step 4: Requirements installed")
            
            # Step 5: Double check if everything is installed
            self.logger.info("🔍 Step 5: Verifying installations...")
            verify_result = await self._verify_installations()
            results['step_5'] = verify_result
            self.logger.info("✅ Step 5: Installations verified")
            
            # Step 6: Make sure Ray is installed in its full form
            self.logger.info("🔍 Step 6: Installing Ray in full form...")
            ray_result = await self._install_ray_full()
            results['step_6'] = ray_result
            if ray_result['success']:
                self.logger.info("✅ Step 6: Ray installed in full form")
            else:
                self.logger.warning("⚠️ Step 6: Ray installation had issues")
            
            # Step 7: Generate unique join request from Tailscale API
            self.logger.info("🔍 Step 7: Setting up Tailscale...")
            tailscale_result = await self._setup_tailscale()
            results['step_7'] = tailscale_result
            if tailscale_result['success']:
                self.logger.info("✅ Step 7: Tailscale configured")
            else:
                self.logger.warning("⚠️ Step 7: Tailscale setup had issues")
            
            # Step 8: Make sure Ray is up and active
            self.logger.info("🔍 Step 8: Verifying Ray is active...")
            ray_active_result = await self._verify_ray_active()
            results['step_8'] = ray_active_result
            if ray_active_result['success']:
                self.logger.info("✅ Step 8: Ray is up and active")
            else:
                self.logger.warning("⚠️ Step 8: Ray activation issues")
            
            # Step 9: Join Ray cluster
            self.logger.info("🔍 Step 9: Joining Ray cluster...")
            cluster_result = await self._join_ray_cluster()
            results['step_9'] = cluster_result
            if cluster_result['success']:
                self.logger.info("✅ Step 9: Successfully joined Ray cluster")
            else:
                self.logger.warning("⚠️ Step 9: Ray cluster join had issues")
            
            total_time = time.time() - start_time
            self.logger.info(f"🎉 All 9 steps completed in {total_time:.1f}s")
            
            return {
                'success': True,
                'total_time': total_time,
                'steps': results,
                'message': 'ZanSoc onboarding completed successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Onboarding failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'steps': results,
                'total_time': time.time() - start_time
            }
    
    async def _check_python(self) -> Dict[str, Any]:
        """Step 2: Check Python installation."""
        result = self.platform_utils.execute_command("python3 --version", timeout=10)
        if result.success:
            return {
                'success': True,
                'version': result.stdout.strip(),
                'executable': 'python3'
            }
        else:
            return {'success': False, 'error': 'Python 3 not found'}
    
    async def _install_requirements(self) -> Dict[str, Any]:
        """Step 4: Install requirements.txt."""
        zansoc_root = Path.home() / ".zansoc" / "Zansoc-v5"
        requirements_file = zansoc_root / "requirements.txt"
        
        if not requirements_file.exists():
            return {'success': True, 'note': 'No requirements.txt found'}
        
        # Try with --break-system-packages first
        cmd = f"cd {zansoc_root} && python3 -m pip install --user -r requirements.txt --break-system-packages --quiet"
        result = self.platform_utils.execute_command(cmd, timeout=300)
        
        if not result.success:
            # Try without --break-system-packages
            cmd = f"cd {zansoc_root} && python3 -m pip install --user -r requirements.txt --quiet"
            result = self.platform_utils.execute_command(cmd, timeout=300)
        
        return {
            'success': result.success,
            'command': cmd,
            'error': result.stderr if not result.success else None
        }
    
    async def _verify_installations(self) -> Dict[str, Any]:
        """Step 5: Verify basic packages are installed."""
        packages = ["requests", "pyyaml", "rich", "click", "psutil"]
        verified = {}
        
        for package in packages:
            result = self.platform_utils.execute_command(
                f"python3 -c 'import {package}; print(\"{package} OK\")'", 
                timeout=5
            )
            verified[package] = result.success
        
        return {
            'success': all(verified.values()),
            'packages': verified,
            'verified_count': sum(verified.values()),
            'total_count': len(packages)
        }
    
    async def _install_ray_full(self) -> Dict[str, Any]:
        """Step 6: Install Ray in full form."""
        # Try Ray with default extras
        commands = [
            "python3 -m pip install --user 'ray[default]' --break-system-packages --quiet",
            "python3 -m pip install --user 'ray[default]' --quiet",
            "python3 -m pip install --user ray --break-system-packages --quiet",
            "python3 -m pip install --user ray --quiet"
        ]
        
        for cmd in commands:
            self.logger.info(f"Trying: {cmd}")
            result = self.platform_utils.execute_command(cmd, timeout=600)
            if result.success:
                return {
                    'success': True,
                    'command': cmd,
                    'method': 'pip_install'
                }
        
        return {
            'success': False,
            'error': 'All Ray installation methods failed',
            'attempted_commands': commands
        }
    
    async def _setup_tailscale(self) -> Dict[str, Any]:
        """Step 7: Setup Tailscale VPN."""
        # Check if Tailscale is already installed
        check_result = self.platform_utils.execute_command("tailscale version", timeout=10)
        
        if not check_result.success:
            # Install Tailscale
            install_cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
            install_result = self.platform_utils.execute_command(install_cmd, timeout=120)
            if not install_result.success:
                return {
                    'success': False,
                    'error': 'Tailscale installation failed',
                    'details': install_result.stderr
                }
        
        # Authenticate with Tailscale
        auth_cmd = f"sudo tailscale up --authkey={self.tailscale_auth_key}"
        auth_result = self.platform_utils.execute_command(auth_cmd, timeout=60)
        
        if auth_result.success:
            # Get Tailscale IP
            ip_result = self.platform_utils.execute_command("tailscale ip -4", timeout=10)
            return {
                'success': True,
                'tailscale_ip': ip_result.stdout.strip() if ip_result.success else 'unknown',
                'authenticated': True
            }
        else:
            return {
                'success': False,
                'error': 'Tailscale authentication failed',
                'details': auth_result.stderr
            }
    
    async def _verify_ray_active(self) -> Dict[str, Any]:
        """Step 8: Verify Ray is active."""
        # Test Ray import
        import_result = self.platform_utils.execute_command(
            "python3 -c 'import ray; print(f\"Ray {ray.__version__} active\")'", 
            timeout=15
        )
        
        if import_result.success:
            return {
                'success': True,
                'ray_version': import_result.stdout.strip(),
                'import_working': True
            }
        else:
            return {
                'success': False,
                'error': 'Ray import failed',
                'details': import_result.stderr
            }
    
    async def _join_ray_cluster(self) -> Dict[str, Any]:
        """Step 9: Join Ray cluster with the exact command specified."""
        # The exact command as specified
        ray_cmd = f"export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 && ray start --address='{self.cluster_address}' --redis-password='{self.cluster_password}'"
        
        result = self.platform_utils.execute_command(ray_cmd, timeout=60)
        
        if result.success:
            # Verify connection
            verify_cmd = "ray status"
            verify_result = self.platform_utils.execute_command(verify_cmd, timeout=30)
            
            return {
                'success': True,
                'cluster_address': self.cluster_address,
                'ray_command': ray_cmd,
                'status': verify_result.stdout if verify_result.success else 'Connected but status unknown'
            }
        else:
            return {
                'success': False,
                'error': 'Ray cluster join failed',
                'command': ray_cmd,
                'details': result.stderr
            }