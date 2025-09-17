"""Provider management for ZanSoc CLI."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import Provider, ProviderStatus, OnboardingSession
from .database import DatabaseManager
from .utils.logger import get_logger


class ProviderManager:
    """Manages provider registration and lifecycle."""
    
    def __init__(self, database: DatabaseManager):
        """Initialize provider manager.
        
        Args:
            database: Database manager instance
        """
        self.db = database
        self.logger = get_logger(__name__)
    
    def generate_provider_id(self) -> str:
        """Generate a unique provider ID.
        
        Returns:
            Unique provider ID string
        """
        # Generate UUID-based provider ID with prefix
        provider_uuid = str(uuid.uuid4())
        provider_id = f"zansoc-{provider_uuid[:8]}"
        
        # Ensure uniqueness (very unlikely collision, but good practice)
        while self.get_provider_by_id(provider_id) is not None:
            provider_uuid = str(uuid.uuid4())
            provider_id = f"zansoc-{provider_uuid[:8]}"
        
        return provider_id
    
    def register_provider(self, username: str) -> Optional[Provider]:
        """Register a new provider.
        
        Args:
            username: Username for the provider
            
        Returns:
            Provider instance if successful, None otherwise
        """
        try:
            # Check if username already exists
            existing = self.get_provider_by_username(username)
            if existing:
                self.logger.warning(f"Provider with username '{username}' already exists")
                return existing
            
            # Generate unique provider ID
            provider_id = self.generate_provider_id()
            
            # Create provider instance
            provider = Provider(
                id=provider_id,
                username=username,
                status=ProviderStatus.REGISTERING,
                created_at=datetime.now()
            )
            
            # Store in database
            if self.store_provider_info(provider):
                self.logger.info(f"Successfully registered provider {provider_id} for user {username}")
                return provider
            else:
                self.logger.error(f"Failed to store provider {provider_id} in database")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to register provider for {username}: {e}")
            return None
    
    def store_provider_info(self, provider: Provider) -> bool:
        """Store provider information in database.
        
        Args:
            provider: Provider instance to store
            
        Returns:
            True if successful
        """
        try:
            provider_data = provider.to_dict()
            success = self.db.insert_provider(provider_data)
            
            if success:
                self.logger.info(f"Stored provider info for {provider.id}")
            else:
                self.logger.error(f"Failed to store provider info for {provider.id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error storing provider {provider.id}: {e}")
            return False
    
    def get_provider_by_id(self, provider_id: str) -> Optional[Provider]:
        """Get provider by ID.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Provider instance or None if not found
        """
        try:
            provider_data = self.db.get_provider_by_id(provider_id)
            if provider_data:
                return Provider.from_dict(provider_data)
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving provider {provider_id}: {e}")
            return None
    
    def get_provider_by_username(self, username: str) -> Optional[Provider]:
        """Get provider by username.
        
        Args:
            username: Username
            
        Returns:
            Provider instance or None if not found
        """
        try:
            provider_data = self.db.get_provider_by_username(username)
            if provider_data:
                return Provider.from_dict(provider_data)
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving provider for username {username}: {e}")
            return None
    
    def update_provider_status(self, provider_id: str, status: ProviderStatus) -> bool:
        """Update provider status.
        
        Args:
            provider_id: Provider ID
            status: New status
            
        Returns:
            True if successful
        """
        try:
            updates = {
                'status': status.value,
                'last_seen': datetime.now().isoformat()
            }
            
            success = self.db.update_provider(provider_id, updates)
            
            if success:
                self.logger.info(f"Updated provider {provider_id} status to {status.value}")
            else:
                self.logger.error(f"Failed to update provider {provider_id} status")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating provider {provider_id} status: {e}")
            return False
    
    def update_provider_info(self, provider_id: str, **kwargs) -> bool:
        """Update provider information.
        
        Args:
            provider_id: Provider ID
            **kwargs: Fields to update
            
        Returns:
            True if successful
        """
        try:
            # Add last_seen timestamp
            kwargs['last_seen'] = datetime.now().isoformat()
            
            success = self.db.update_provider(provider_id, kwargs)
            
            if success:
                self.logger.info(f"Updated provider {provider_id} info: {list(kwargs.keys())}")
            else:
                self.logger.error(f"Failed to update provider {provider_id} info")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating provider {provider_id} info: {e}")
            return False
    
    def get_provider_status(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get provider status and information.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Dictionary with provider status information
        """
        try:
            provider = self.get_provider_by_id(provider_id)
            if not provider:
                return None
            
            # Get onboarding session if exists
            session_data = self.db.get_session_by_provider(provider_id)
            session = None
            if session_data:
                session = OnboardingSession.from_dict(session_data)
            
            return {
                'provider': provider,
                'session': session,
                'status_summary': {
                    'id': provider.id,
                    'username': provider.username,
                    'status': provider.status.value,
                    'created_at': provider.created_at,
                    'last_seen': provider.last_seen,
                    'tailscale_ip': provider.tailscale_ip,
                    'ray_node_id': provider.ray_node_id,
                    'platform': provider.platform,
                    'current_step': session.current_step if session else None,
                    'completed_steps': len(session.completed_steps) if session else 0,
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting provider {provider_id} status: {e}")
            return None
    
    def list_providers(self, status: Optional[ProviderStatus] = None) -> List[Provider]:
        """List providers, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of Provider instances
        """
        try:
            if status:
                provider_data_list = self.db.get_providers_by_status(status.value)
            else:
                provider_data_list = self.db.get_all_providers()
            
            providers = []
            for provider_data in provider_data_list:
                try:
                    provider = Provider.from_dict(provider_data)
                    providers.append(provider)
                except Exception as e:
                    self.logger.warning(f"Failed to parse provider data: {e}")
                    continue
            
            return providers
            
        except Exception as e:
            self.logger.error(f"Error listing providers: {e}")
            return []
    
    def create_onboarding_session(self, provider_id: str, initial_step: str = "registration") -> Optional[OnboardingSession]:
        """Create a new onboarding session.
        
        Args:
            provider_id: Provider ID
            initial_step: Initial step name
            
        Returns:
            OnboardingSession instance if successful
        """
        try:
            session_id = f"session-{uuid.uuid4()}"
            
            session = OnboardingSession(
                session_id=session_id,
                provider_id=provider_id,
                current_step=initial_step,
                completed_steps=[],
                failed_steps=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session_data = session.to_dict()
            if self.db.insert_session(session_data):
                self.logger.info(f"Created onboarding session {session_id} for provider {provider_id}")
                return session
            else:
                self.logger.error(f"Failed to create session for provider {provider_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating session for provider {provider_id}: {e}")
            return None
    
    def update_session_step(self, session_id: str, current_step: str, completed_step: Optional[str] = None) -> bool:
        """Update onboarding session step.
        
        Args:
            session_id: Session ID
            current_step: New current step
            completed_step: Step that was just completed
            
        Returns:
            True if successful
        """
        try:
            # Get current session
            session_data = self.db.execute_query(
                "SELECT * FROM onboarding_sessions WHERE session_id = ?",
                (session_id,)
            )
            
            if not session_data:
                self.logger.error(f"Session {session_id} not found")
                return False
            
            session = OnboardingSession.from_dict(session_data[0])
            
            # Update completed steps if provided
            if completed_step and completed_step not in session.completed_steps:
                session.completed_steps.append(completed_step)
            
            # Update current step
            session.current_step = current_step
            session.updated_at = datetime.now()
            
            # Update in database
            updates = {
                'current_step': current_step,
                'completed_steps': ','.join(session.completed_steps),
                'updated_at': session.updated_at.isoformat()
            }
            
            success = self.db.update_session(session_id, updates)
            
            if success:
                self.logger.info(f"Updated session {session_id} to step {current_step}")
            else:
                self.logger.error(f"Failed to update session {session_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    def mark_step_failed(self, session_id: str, failed_step: str) -> bool:
        """Mark a step as failed in the onboarding session.
        
        Args:
            session_id: Session ID
            failed_step: Step that failed
            
        Returns:
            True if successful
        """
        try:
            # Get current session
            session_data = self.db.execute_query(
                "SELECT * FROM onboarding_sessions WHERE session_id = ?",
                (session_id,)
            )
            
            if not session_data:
                self.logger.error(f"Session {session_id} not found")
                return False
            
            session = OnboardingSession.from_dict(session_data[0])
            
            # Add to failed steps if not already there
            if failed_step not in session.failed_steps:
                session.failed_steps.append(failed_step)
            
            session.updated_at = datetime.now()
            
            # Update in database
            updates = {
                'failed_steps': ','.join(session.failed_steps),
                'updated_at': session.updated_at.isoformat()
            }
            
            success = self.db.update_session(session_id, updates)
            
            if success:
                self.logger.info(f"Marked step {failed_step} as failed in session {session_id}")
            else:
                self.logger.error(f"Failed to mark step {failed_step} as failed")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error marking step failed in session {session_id}: {e}")
            return False