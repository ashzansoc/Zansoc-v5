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
            return StepResult(
                success=False,
                step=step,
                message=f"Step {step.value} failed with exception",
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
        """Execute environment setup step."""
        try:
            # Install miniconda
            self.logger.info("Installing miniconda...")
            miniconda_result = self.environment_manager.install_miniconda()
            if not miniconda_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="Failed to install miniconda",
                    error=miniconda_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Create conda environment
            self.logger.info("Creating conda environment...")
            env_result = self.environment_manager.create_conda_environment("3.13.7", "zansoc")
            if not env_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="Failed to create conda environment",
                    error=env_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Clone repository
            self.logger.info("Cloning repository...")
            repo_result = self.environment_manager.clone_repository(
                "https://github.com/ashzansoc/Zansoc-v5.git",
                str(Path.home() / ".zansoc" / "Zansoc-v5")
            )
            if not repo_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="Failed to clone repository",
                    error=repo_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Install requirements
            self.logger.info("Installing requirements...")
            requirements_path = Path.home() / ".zansoc" / "Zansoc-v5" / "cli" / "requirements.txt"
            if requirements_path.exists():
                req_result = self.environment_manager.install_requirements(
                    str(requirements_path),
                    "zansoc"
                )
                if not req_result.success:
                    return StepResult(
                        success=False,
                        step=OnboardingStep.ENVIRONMENT_SETUP,
                        message="Failed to install requirements",
                        error=req_result.error,
                        execution_time=time.time() - start_time,
                        retry_suggested=True
                    )
            else:
                self.logger.info("No requirements.txt found, skipping requirements installation")
            
            # Install Ray
            self.logger.info("Installing Ray...")
            ray_result = self.environment_manager.install_ray("zansoc")
            if not ray_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.ENVIRONMENT_SETUP,
                    message="Failed to install Ray",
                    error=ray_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            return StepResult(
                success=True,
                step=OnboardingStep.ENVIRONMENT_SETUP,
                message="Environment setup completed successfully",
                data={
                    'miniconda_path': miniconda_result.data.get('installation_path'),
                    'conda_env': 'zansoc',
                    'python_version': '3.13.7',
                    'ray_installed': True
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
        """Execute Tailscale setup step."""
        try:
            # Install Tailscale
            self.logger.info("Installing Tailscale...")
            install_result = self.tailscale_manager.install_tailscale()
            if not install_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.TAILSCALE_SETUP,
                    message="Failed to install Tailscale",
                    error=install_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Authenticate with Tailscale
            self.logger.info("Authenticating with Tailscale...")
            auth_result = self.tailscale_manager.authenticate_with_key(self.tailscale_auth_key)
            if not auth_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.TAILSCALE_SETUP,
                    message="Failed to authenticate with Tailscale",
                    error=auth_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Get Tailscale IP
            tailscale_ip = self.tailscale_manager.get_tailscale_ip()
            if not tailscale_ip:
                return StepResult(
                    success=False,
                    step=OnboardingStep.TAILSCALE_SETUP,
                    message="Failed to get Tailscale IP address",
                    error="Tailscale IP not available",
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Update provider with Tailscale IP
            if self.progress.provider_id:
                self.provider_manager.update_provider_tailscale_ip(
                    self.progress.provider_id, 
                    tailscale_ip
                )
            
            return StepResult(
                success=True,
                step=OnboardingStep.TAILSCALE_SETUP,
                message=f"Tailscale setup completed successfully. IP: {tailscale_ip}",
                data={
                    'tailscale_ip': tailscale_ip,
                    'installation_method': install_result.data.get('method', 'unknown')
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                step=OnboardingStep.TAILSCALE_SETUP,
                message="Tailscale setup failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )
    
    async def _step_ray_connection(self, start_time: float) -> StepResult:
        """Execute Ray cluster connection step."""
        try:
            # Connect to Ray cluster
            self.logger.info(f"Connecting to Ray cluster at {self.cluster_address}...")
            connection_result = self.ray_manager.connect_to_cluster(
                self.cluster_address,
                self.cluster_password,
                "zansoc"
            )
            
            if not connection_result.success:
                return StepResult(
                    success=False,
                    step=OnboardingStep.RAY_CONNECTION,
                    message="Failed to connect to Ray cluster",
                    error=connection_result.error,
                    execution_time=time.time() - start_time,
                    retry_suggested=True
                )
            
            # Update provider with Ray node ID
            if self.progress.provider_id and connection_result.node_id:
                self.provider_manager.update_provider_ray_node_id(
                    self.progress.provider_id,
                    connection_result.node_id
                )
            
            return StepResult(
                success=True,
                step=OnboardingStep.RAY_CONNECTION,
                message=f"Connected to Ray cluster successfully. Node ID: {connection_result.node_id}",
                data={
                    'node_id': connection_result.node_id,
                    'cluster_address': self.cluster_address,
                    'cluster_info': connection_result.cluster_info.__dict__ if connection_result.cluster_info else None
                },
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                step=OnboardingStep.RAY_CONNECTION,
                message="Ray connection failed with exception",
                error=str(e),
                execution_time=time.time() - start_time,
                retry_suggested=True
            )
    
    async def _step_verification(self, start_time: float) -> StepResult:
        """Execute verification step."""
        try:
            verification_results = {}
            
            # Verify Ray connection
            self.logger.info("Verifying Ray connection...")
            ray_verified = self.ray_manager.verify_node_registration("zansoc")
            verification_results['ray_connected'] = ray_verified
            
            # Verify Tailscale connection
            self.logger.info("Verifying Tailscale connection...")
            tailscale_ip = self.tailscale_manager.get_tailscale_ip()
            verification_results['tailscale_connected'] = tailscale_ip is not None
            verification_results['tailscale_ip'] = tailscale_ip
            
            # Test cluster connectivity
            self.logger.info("Testing cluster connectivity...")
            cluster_reachable = self.ray_manager.test_cluster_connectivity(self.cluster_address)
            verification_results['cluster_reachable'] = cluster_reachable
            
            # Get connection health
            health = self.ray_manager.get_connection_health("zansoc")
            verification_results['connection_health'] = health
            
            # Check if all verifications passed
            all_verified = (
                ray_verified and 
                tailscale_ip is not None and 
                cluster_reachable and
                health.get('connected', False)
            )
            
            if not all_verified:
                failed_checks = []
                if not ray_verified:
                    failed_checks.append("Ray node registration")
                if tailscale_ip is None:
                    failed_checks.append("Tailscale connection")
                if not cluster_reachable:
                    failed_checks.append("Cluster connectivity")
                if not health.get('connected', False):
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