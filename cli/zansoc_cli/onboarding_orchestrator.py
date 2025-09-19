"""Onboarding orchestrator for seamless provider enrollment."""

import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .platform_utils import PlatformUtils
from .environment_manager import EnvironmentManager
from .tailscale_manager import TailscaleManager
from .ray_manager import RayManager
from .provider_manager import ProviderManager
from .database import DatabaseManager
from .config_manager import ConfigManager
from .models import Provider, ProviderStatus
from .simple_onboarding import SimpleOnboarding
from .utils.logger import get_logger


class OnboardingStep(Enum):
    """Onboarding step enumeration."""
    REGISTRATION = "registration"
    ENVIRONMENT_SETUP = "environment_setup"
    TAILSCALE_SETUP = "tailscale_setup"
    RAY_CONNECTION = "ray_connection"
    VERIFICATION = "verification"
    COMPLETION = "completion"


@dataclass
class StepResult:
    """Result of an onboarding step."""
    success: bool
    step: OnboardingStep
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_suggested: bool = False


@dataclass
class OnboardingProgress:
    """Onboarding progress tracking."""
    current_step: OnboardingStep
    completed_steps: List[OnboardingStep]
    failed_steps: List[OnboardingStep]
    total_steps: int
    start_time: float
    provider_id: Optional[str] = None
    session_id: Optional[str] = None


class OnboardingOrchestrator:
    """Orchestrates the complete provider onboarding process."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize onboarding orchestrator.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = get_logger(__name__)
        
        # Initialize managers
        self.platform_utils = PlatformUtils()
        self.db = DatabaseManager(str(self.config.get_database_path()))
        self.provider_manager = ProviderManager(self.db)
        self.environment_manager = EnvironmentManager(self.platform_utils)
        self.tailscale_manager = TailscaleManager(self.platform_utils)
        self.ray_manager = RayManager(self.platform_utils)
        
        # Progress tracking
        self.progress: Optional[OnboardingProgress] = None
        self.progress_callback: Optional[Callable[[OnboardingProgress], None]] = None
        
        # Configuration
        self.cluster_address = "100.101.84.71:6379"
        self.cluster_password = "zansoc_secure_password_change_me"
        self.tailscale_auth_key = "tskey-auth-kd32Q6XdHS11CNTRL-X13DpHNm9ygqbdavCzngxgEJg91Rgie6"
        
        # Step definitions
        self.steps = [
            OnboardingStep.REGISTRATION,
            OnboardingStep.ENVIRONMENT_SETUP,
            OnboardingStep.TAILSCALE_SETUP,
            OnboardingStep.RAY_CONNECTION,
            OnboardingStep.VERIFICATION,
            OnboardingStep.COMPLETION
        ]
    
    def set_progress_callback(self, callback: Callable[[OnboardingProgress], None]) -> None:
        """Set progress callback for UI updates.
        
        Args:
            callback: Function to call with progress updates
        """
        self.progress_callback = callback
    
    async def start_onboarding(self, username: str) -> StepResult:
        """Start the complete onboarding process.
        
        Args:
            username: Username for provider registration
            
        Returns:
            Final step result
        """
        self.logger.info(f"Starting onboarding for user: {username}")
        
        # Initialize progress tracking
        self.progress = OnboardingProgress(
            current_step=OnboardingStep.REGISTRATION,
            completed_steps=[],
            failed_steps=[],
            total_steps=len(self.steps),
            start_time=time.time()
        )
        
        try:
            # Execute each step
            for step in self.steps:
                self.progress.current_step = step
                self._update_progress()
                
                self.logger.info(f"Executing step: {step.value}")
                result = await self._execute_step(step, username)
                
                if result.success:
                    self.progress.completed_steps.append(step)
                    self.logger.info(f"Step {step.value} completed successfully")
                else:
                    self.progress.failed_steps.append(step)
                    self.logger.error(f"Step {step.value} failed: {result.error}")
                    
                    # Handle failure
                    if result.retry_suggested:
                        retry_result = await self._retry_step(step, username)
                        if retry_result.success:
                            self.progress.completed_steps.append(step)
                            self.progress.failed_steps.remove(step)
                        else:
                            return retry_result
                    else:
                        return result
                
                self._update_progress()
            
            # All steps completed successfully
            total_time = time.time() - self.progress.start_time
            return StepResult(
                success=True,
                step=OnboardingStep.COMPLETION,
                message=f"Onboarding completed successfully in {total_time:.1f}s",
                data={
                    'provider_id': self.progress.provider_id,
                    'session_id': self.progress.session_id,
                    'total_time': total_time,
                    'completed_steps': len(self.progress.completed_steps)
                },
                execution_time=total_time
            )
            
        except Exception as e:
            self.logger.error(f"Onboarding failed with exception: {e}")
            return StepResult(
                success=False,
                step=self.progress.current_step if self.progress else OnboardingStep.REGISTRATION,
                message="Onboarding failed with unexpected error",
                error=str(e),
                execution_time=time.time() - (self.progress.start_time if self.progress else time.time())
            )
    
    async def _execute_step(self, step: OnboardingStep, username: str) -> StepResult:
        """Execute a single onboarding step.
        
        Args:
            step: Step to execute
            username: Username for registration
            
        Returns:
            Step execution result
        """
        start_time = time.time()
        
        try:
            if step == OnboardingStep.REGISTRATION:
                return await self._step_registration(username, start_time)
            elif step == OnboardingStep.ENVIRONMENT_SETUP:
                return await self._step_environment_setup(start_time)
            elif step == OnboardingStep.TAILSCALE_SETUP:
                return await self._step_tailscale_setup(start_time)
            elif step == OnboardingStep.RAY_CONNECTION:
                return await self._step_ray_connection(start_time)
            elif step == OnboardingStep.VERIFICATION:
                return await self._step_verification(start_time)
            elif step == OnboardingStep.COMPLETION:
                return await self._step_completion(start_time)
            else:
                return StepResult(
                    success=False,
                    step=step,
                    message=f"Unknown step: {step.value}",
                    error=f"Step {step.value} not implemented",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            self.logger.error(f"Step {step.value} failed with exception: {e}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            return StepResult(
                success=False,
                step=step,
                message=f"Step {step.value} failed with exception: {type(e).__name__}",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )
    
    async def _step_registration(self, username: str, start_time: float) -> StepResult:
        """Execute provider registration step."""
        try:
            # Register provider
            provider = self.provider_manager.register_provider(username)
            if not provider:
                return StepResult(
                    success=False,
                    step=OnboardingStep.REGISTRATION,
                    message="Failed to register provider",
                    error="Provider registration returned None",
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            self.progress.provider_id = provider.id
            
            # Create onboarding session
            session = self.provider_manager.create_onboarding_session(
                provider.id, 
                OnboardingStep.ENVIRONMENT_SETUP.value
            )
            
            if not session:
                return StepResult(
                    success=False,
                    step=OnboardingStep.REGISTRATION,
                    message="Failed to create onboarding session",
                    error="Session creation returned None",
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            self.progress.session_id = session.session_id
            
            return StepResult(
                success=True,
                step=OnboardingStep.REGISTRATION,
                message=f"Provider registered successfully: {provider.id}",
                data={
                    'provider_id': provider.id,
                    'session_id': session.session_id,
                    'username': username
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                step=OnboardingStep.REGISTRATION,
                message="Registration failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )
    
    async def _step_environment_setup(self, start_time: float) -> StepResult:
        """Execute the simple 9-step process."""
        try:
            self.logger.info("Starting simple 9-step onboarding process...")
            
            # Use the simple onboarding class
            simple_onboarding = SimpleOnboarding()
            result = await simple_onboarding.execute_onboarding()
            
            if result['success']:
                return StepResult(
                    success=True,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="9-step onboarding completed successfully",
                    data=result,
                    execution_time=time.time() - start_time
                )
            else:
                return StepResult(
                    success=False,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="9-step onboarding failed",
                    error=result.get('error', 'Unknown error'),
                    data=result,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
                
        except Exception as e:
            self.logger.error(f"Simple onboarding failed: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            return StepResult(
                success=False,
                step=OnboardingStep.ENVIRONMENT_SETUP,
                message="Simple onboarding failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )

    async def _step_environment_setup_old(self, start_time: float) -> StepResult:
        """Execute environment setup step with smart detection of existing installations."""
        try:
            self.logger.info("Starting smart environment setup...")
            
            # Step 1: Comprehensive environment validation
            self.logger.info("Validating environment...")
            
            # Check Python version
            python_check = self.platform_utils.execute_command("python3 --version", timeout=10)
            if not python_check.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="Python 3 is not available",
                    error="Python 3 is required but not found",
                    execution_time=time.time() - start_time,
                    retry_suggested=False
                )
            
            python_version = python_check.stdout.strip()
            self.logger.info(f"Found {python_version}")
            
            # Check pip availability
            pip_check = self.platform_utils.execute_command("python3 -m pip --version", timeout=10)
            if not pip_check.success:
                self.logger.warning("Pip not available, this may cause installation issues")
            
            # Check internet connectivity
            connectivity_check = self.platform_utils.execute_command("python3 -c 'import urllib.request; urllib.request.urlopen(\"https://pypi.org\", timeout=5)'", timeout=15)
            if not connectivity_check.success:
                self.logger.warning("Internet connectivity issues detected")
            
            # Check available disk space
            disk_check = self.platform_utils.execute_command("df -h . | tail -1 | awk '{print $4}'", timeout=5)
            if disk_check.success:
                self.logger.info(f"Available disk space: {disk_check.stdout.strip()}")
            
            self.logger.info("Environment validation completed")
            
            # Step 2: Check if Ray is already installed (safer method)
            self.logger.info("Checking for existing Ray installation...")
            
            # First check if ray package exists without importing
            ray_check = self.platform_utils.execute_command(
                "python3 -c 'import pkg_resources; pkg_resources.get_distribution(\"ray\"); print(\"Ray package found\")'", 
                timeout=5
            )
            
            if ray_check.success and "Ray package found" in ray_check.stdout:
                # Package exists, now try safe import with timeout
                ray_version_check = self.platform_utils.execute_command(
                    "timeout 5 python3 -c 'import ray; print(f\"Ray {ray.__version__} available\")'", 
                    timeout=10
                )
                
                if ray_version_check.success and "Ray" in ray_version_check.stdout:
                    ray_version = ray_version_check.stdout.strip()
                    self.logger.info(f"✅ {ray_version} - skipping installation")
                    
                    return StepResult(
                        success=True,
                        step=OnboardingStep.ENVIRONMENT_SETUP,
                        message="Environment setup completed (existing Ray installation detected)",
                        data={
                            'python_version': python_version,
                            'ray_version': ray_version,
                            'installation_method': 'existing_installation',
                            'skipped_installation': True
                        },
                        execution_time=time.time() - start_time
                    )
                else:
                    self.logger.warning("Ray package found but import failed, will try to reinstall")
            else:
                self.logger.info("Ray package not found, proceeding with installation")
            
            if ray_check.success and "Ray" in ray_check.stdout:
                # Ray is already installed and working!
                ray_version = ray_check.stdout.strip()
                self.logger.info(f"✅ {ray_version} - skipping installation")
                
                return StepResult(
                    success=True,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="Environment setup completed (existing Ray installation detected)",
                    data={
                        'python_version': python_version,
                        'ray_version': ray_version,
                        'installation_method': 'existing_installation',
                        'skipped_installation': True
                    },
                    execution_time=time.time() - start_time
                )
            
            # Step 3: Ray not found, try to install it
            self.logger.info("Ray not found, attempting installation...")
            
            # Try conda first if available
            conda_check = self.platform_utils.execute_command("conda --version", timeout=10)
            if conda_check.success:
                self.logger.info("Conda detected, trying conda installation...")
                conda_install = self.platform_utils.execute_command(
                    "conda install -c conda-forge ray -y", 
                    timeout=300
                )
                if conda_install.success:
                    # Verify conda installation
                    ray_verify = self.platform_utils.execute_command(
                        "python3 -c 'import ray; print(f\"Ray {ray.__version__} installed via conda\")'", 
                        timeout=30
                    )
                    if ray_verify.success:
                        ray_version = ray_verify.stdout.strip()
                        self.logger.info(f"✅ Conda installation successful: {ray_version}")
                        
                        return StepResult(
                            success=True,
                            step=OnboardingStep.ENVIRONMENT_SETUP,
                            message="Environment setup completed (conda installation)",
                            data={
                                'python_version': python_version,
                                'ray_version': ray_version,
                                'installation_method': 'conda',
                            },
                            execution_time=time.time() - start_time
                        )
            
            # Step 4: Fallback to pip installation (handle PEP 668)
            self.logger.info("Installing Ray via pip...")
            
            # Try lightweight Ray installation first
            pip_commands = [
                "python3 -m pip install --user ray --no-deps --quiet --break-system-packages",
                "python3 -m pip install --user ray --no-deps --quiet",
                "python3 -m pip install --user ray --quiet --break-system-packages", 
                "python3 -m pip install --user ray --quiet"
            ]
            
            pip_success = False
            successful_cmd = None
            
            for cmd in pip_commands:
                self.logger.info(f"Trying: {cmd}")
                pip_install = self.platform_utils.execute_command(cmd, timeout=600)
                if pip_install.success:
                    pip_success = True
                    successful_cmd = cmd
                    self.logger.info(f"✅ Ray installation successful with: {cmd}")
                    break
                else:
                    self.logger.warning(f"Failed: {cmd} - {pip_install.stderr}")
            
            if pip_success:
                # Verify installation with safer method
                self.logger.info("Verifying Ray installation...")
                
                # First check package exists
                pkg_check = self.platform_utils.execute_command(
                    "python3 -c 'import pkg_resources; print(pkg_resources.get_distribution(\"ray\").version)'", 
                    timeout=10
                )
                
                if pkg_check.success:
                    ray_version = f"Ray {pkg_check.stdout.strip()}"
                    self.logger.info(f"✅ Ray package verification successful: {ray_version}")
                    
                    return StepResult(
                        success=True,
                        step=OnboardingStep.ENVIRONMENT_SETUP,
                        message="Environment setup completed (Ray installed via pip)",
                        data={
                            'python_version': python_version,
                            'ray_version': ray_version,
                            'installation_method': 'pip',
                            'install_command': successful_cmd
                        },
                        execution_time=time.time() - start_time
                    )
                else:
                    self.logger.warning("Ray package verification failed")
            
            # Step 5: All installation methods failed - skip Ray for now
            self.logger.warning("Ray installation failed, continuing without Ray for testing")
            return StepResult(
                success=True,
                step=OnboardingStep.ENVIRONMENT_SETUP,
                message="Environment setup completed (Ray installation skipped)",
                data={
                    'python_version': python_version,
                    'ray_version': 'not_installed',
                    'installation_method': 'skip_ray',
                    'note': 'Ray installation was skipped due to installation issues'
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                step=OnboardingStep.ENVIRONMENT_SETUP,
                message="Environment setup failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )
    
    async def _step_tailscale_setup(self, start_time: float) -> StepResult:
        """Tailscale setup (handled in 9-step process)."""
        self.logger.info("Tailscale setup was handled in environment setup step")
        return StepResult(
            success=True,
            step=OnboardingStep.TAILSCALE_SETUP,
            message="Tailscale setup completed in 9-step process",
            data={'handled_in_environment_setup': True},
            execution_time=time.time() - start_time
        )
    
    async def _step_ray_connection(self, start_time: float) -> StepResult:
        """Ray connection (handled in 9-step process)."""
        self.logger.info("Ray connection was handled in environment setup step")
        return StepResult(
            success=True,
            step=OnboardingStep.RAY_CONNECTION,
            message="Ray connection completed in 9-step process",
            data={'handled_in_environment_setup': True},
            execution_time=time.time() - start_time
        )
    
    async def _step_verification(self, start_time: float) -> StepResult:
        """Execute verification step."""
        try:
            verification_results = {}
            
            # Verify Ray connection
            self.logger.info("Verifying Ray connection...")
            ray_verify = self.platform_utils.execute_command(
                "python3 -c 'import ray; print(\"Ray available\")'",
                timeout=10
            )
            ray_verified = ray_verify.success and "Ray available" in ray_verify.stdout
            verification_results['ray_connected'] = ray_verified
            
            # Verify Tailscale connection
            self.logger.info("Verifying Tailscale connection...")
            tailscale_ip = self.tailscale_manager.get_tailscale_ip()
            verification_results['tailscale_connected'] = tailscale_ip is not None
            verification_results['tailscale_ip'] = tailscale_ip
            
            # Test cluster connectivity (simple ping test)
            self.logger.info("Testing cluster connectivity...")
            cluster_host = self.cluster_address.split(':')[0]
            ping_result = self.platform_utils.execute_command(f"ping -c 1 {cluster_host}", timeout=10)
            cluster_reachable = ping_result.success
            verification_results['cluster_reachable'] = cluster_reachable
            
            # Simple health check
            verification_results['connection_health'] = {'connected': ray_verified and cluster_reachable}
            
            # Check if all verifications passed
            all_verified = (
                ray_verified and 
                tailscale_ip is not None and 
                cluster_reachable and
                verification_results['connection_health'].get('connected', False)
            )
            
            if not all_verified:
                failed_checks = []
                if not ray_verified:
                    failed_checks.append("Ray node registration")
                if tailscale_ip is None:
                    failed_checks.append("Tailscale connection")
                if not cluster_reachable:
                    failed_checks.append("Cluster connectivity")
                if not verification_results['connection_health'].get('connected', False):
                    failed_checks.append("Connection health")
                
                return StepResult(
                    success=False,
                    step=OnboardingStep.VERIFICATION,
                    message=f"Verification failed: {', '.join(failed_checks)}",
                    error=f"Failed checks: {failed_checks}",
                    data=verification_results,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            return StepResult(
                success=True,
                step=OnboardingStep.VERIFICATION,
                message="All verifications passed successfully",
                data=verification_results,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                step=OnboardingStep.VERIFICATION,
                message="Verification failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )
    
    async def _step_completion(self, start_time: float) -> StepResult:
        """Execute completion step."""
        try:
            # Update provider status to active
            if self.progress.provider_id:
                self.provider_manager.update_provider_status(
                    self.progress.provider_id,
                    ProviderStatus.ACTIVE
                )
            
            # Update onboarding session
            if self.progress.session_id:
                self.provider_manager.complete_onboarding_session(self.progress.session_id)
            
            # Get final provider info
            provider_info = None
            if self.progress.provider_id:
                provider_info = self.provider_manager.get_provider(self.progress.provider_id)
            
            return StepResult(
                success=True,
                step=OnboardingStep.COMPLETION,
                message="Onboarding completed successfully! You are now an active provider.",
                data={
                    'provider_info': provider_info.__dict__ if provider_info else None,
                    'total_time': time.time() - self.progress.start_time,
                    'completed_steps': len(self.progress.completed_steps)
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                step=OnboardingStep.COMPLETION,
                message="Completion step failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=False
            )
    
    async def _retry_step(self, step: OnboardingStep, username: str, max_retries: int = 2) -> StepResult:
        """Retry a failed step.
        
        Args:
            step: Step to retry
            username: Username for registration
            max_retries: Maximum number of retries
            
        Returns:
            Retry result
        """
        self.logger.info(f"Retrying step: {step.value}")
        
        for attempt in range(max_retries):
            self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} for step {step.value}")
            
            # Wait before retry
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            result = await self._execute_step(step, username)
            if result.success:
                self.logger.info(f"Step {step.value} succeeded on retry attempt {attempt + 1}")
                return result
        
        self.logger.error(f"Step {step.value} failed after {max_retries} retry attempts")
        return StepResult(
            success=False,
            step=step,
            message=f"Step {step.value} failed after {max_retries} retry attempts",
            error="Maximum retries exceeded",
            execution_time=0.0,
            retry_suggested=False
        )
    
    def _update_progress(self) -> None:
        """Update progress and call callback if set."""
        if self.progress_callback and self.progress:
            self.progress_callback(self.progress)
    
    def get_progress(self) -> Optional[OnboardingProgress]:
        """Get current onboarding progress.
        
        Returns:
            Current progress or None
        """
        return self.progress
    
    def cleanup_on_failure(self) -> None:
        """Cleanup resources on onboarding failure."""
        try:
            self.logger.info("Cleaning up after onboarding failure...")
            
            # Disconnect from Ray cluster
            try:
                self.ray_manager.disconnect_from_cluster("zansoc")
            except Exception as e:
                self.logger.warning(f"Failed to disconnect from Ray cluster: {e}")
            
            # Stop Tailscale (optional, user might want to keep it)
            # try:
            #     self.tailscale_manager.stop_tailscale()
            # except Exception as e:
            #     self.logger.warning(f"Failed to stop Tailscale: {e}")
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")