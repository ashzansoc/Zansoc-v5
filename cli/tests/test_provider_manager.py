"""Tests for ProviderManager class."""

import pytest
import tempfile
import os
from datetime import datetime

from zansoc_cli.database import DatabaseManager
from zansoc_cli.provider_manager import ProviderManager
from zansoc_cli.models import Provider, ProviderStatus


class TestProviderManager:
    """Test cases for ProviderManager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.db = DatabaseManager(self.temp_db.name)
        self.provider_manager = ProviderManager(self.db)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_generate_provider_id(self):
        """Test provider ID generation."""
        provider_id = self.provider_manager.generate_provider_id()
        
        assert provider_id.startswith('zansoc-')
        assert len(provider_id) == 15  # 'zansoc-' + 8 chars
        
        # Generate another ID and ensure uniqueness
        provider_id2 = self.provider_manager.generate_provider_id()
        assert provider_id != provider_id2
    
    def test_register_provider(self):
        """Test provider registration."""
        provider = self.provider_manager.register_provider('testuser')
        
        assert provider is not None
        assert provider.username == 'testuser'
        assert provider.status == ProviderStatus.REGISTERING
        assert provider.id.startswith('zansoc-')
        assert isinstance(provider.created_at, datetime)
    
    def test_register_duplicate_username(self):
        """Test registering provider with duplicate username."""
        # Register first provider
        provider1 = self.provider_manager.register_provider('duplicate_user')
        assert provider1 is not None
        
        # Try to register with same username
        provider2 = self.provider_manager.register_provider('duplicate_user')
        assert provider2 is not None
        assert provider2.id == provider1.id  # Should return existing provider
    
    def test_get_provider_by_id(self):
        """Test retrieving provider by ID."""
        # Register a provider
        original_provider = self.provider_manager.register_provider('testuser2')
        assert original_provider is not None
        
        # Retrieve by ID
        retrieved_provider = self.provider_manager.get_provider_by_id(original_provider.id)
        assert retrieved_provider is not None
        assert retrieved_provider.id == original_provider.id
        assert retrieved_provider.username == original_provider.username
        assert retrieved_provider.status == original_provider.status
    
    def test_get_provider_by_username(self):
        """Test retrieving provider by username."""
        # Register a provider
        original_provider = self.provider_manager.register_provider('testuser3')
        assert original_provider is not None
        
        # Retrieve by username
        retrieved_provider = self.provider_manager.get_provider_by_username('testuser3')
        assert retrieved_provider is not None
        assert retrieved_provider.id == original_provider.id
        assert retrieved_provider.username == 'testuser3'
    
    def test_update_provider_status(self):
        """Test updating provider status."""
        # Register a provider
        provider = self.provider_manager.register_provider('testuser4')
        assert provider is not None
        assert provider.status == ProviderStatus.REGISTERING
        
        # Update status
        success = self.provider_manager.update_provider_status(provider.id, ProviderStatus.ACTIVE)
        assert success is True
        
        # Verify update
        updated_provider = self.provider_manager.get_provider_by_id(provider.id)
        assert updated_provider.status == ProviderStatus.ACTIVE
        assert updated_provider.last_seen is not None
    
    def test_update_provider_info(self):
        """Test updating provider information."""
        # Register a provider
        provider = self.provider_manager.register_provider('testuser5')
        assert provider is not None
        
        # Update info
        success = self.provider_manager.update_provider_info(
            provider.id,
            tailscale_ip='100.64.0.1',
            platform='linux-x86_64',
            ray_node_id='ray-node-123'
        )
        assert success is True
        
        # Verify updates
        updated_provider = self.provider_manager.get_provider_by_id(provider.id)
        assert updated_provider.tailscale_ip == '100.64.0.1'
        assert updated_provider.platform == 'linux-x86_64'
        assert updated_provider.ray_node_id == 'ray-node-123'
        assert updated_provider.last_seen is not None
    
    def test_get_provider_status(self):
        """Test getting provider status information."""
        # Register a provider
        provider = self.provider_manager.register_provider('testuser6')
        assert provider is not None
        
        # Create onboarding session
        session = self.provider_manager.create_onboarding_session(provider.id, 'registration')
        assert session is not None
        
        # Get status
        status_info = self.provider_manager.get_provider_status(provider.id)
        assert status_info is not None
        assert status_info['provider'].id == provider.id
        assert status_info['session'].session_id == session.session_id
        assert status_info['status_summary']['id'] == provider.id
        assert status_info['status_summary']['current_step'] == 'registration'
    
    def test_list_providers(self):
        """Test listing providers."""
        # Register providers with different statuses
        provider1 = self.provider_manager.register_provider('user1')
        provider2 = self.provider_manager.register_provider('user2')
        provider3 = self.provider_manager.register_provider('user3')
        
        # Update some statuses
        self.provider_manager.update_provider_status(provider1.id, ProviderStatus.ACTIVE)
        self.provider_manager.update_provider_status(provider2.id, ProviderStatus.ACTIVE)
        # provider3 remains REGISTERING
        
        # List all providers
        all_providers = self.provider_manager.list_providers()
        assert len(all_providers) == 3
        
        # List active providers
        active_providers = self.provider_manager.list_providers(ProviderStatus.ACTIVE)
        assert len(active_providers) == 2
        
        # List registering providers
        registering_providers = self.provider_manager.list_providers(ProviderStatus.REGISTERING)
        assert len(registering_providers) == 1
    
    def test_create_onboarding_session(self):
        """Test creating onboarding session."""
        # Register a provider
        provider = self.provider_manager.register_provider('testuser7')
        assert provider is not None
        
        # Create session
        session = self.provider_manager.create_onboarding_session(provider.id, 'initial_step')
        assert session is not None
        assert session.provider_id == provider.id
        assert session.current_step == 'initial_step'
        assert len(session.completed_steps) == 0
        assert len(session.failed_steps) == 0
        assert session.session_id.startswith('session-')
    
    def test_update_session_step(self):
        """Test updating session step."""
        # Register provider and create session
        provider = self.provider_manager.register_provider('testuser8')
        session = self.provider_manager.create_onboarding_session(provider.id, 'step1')
        
        # Update session step
        success = self.provider_manager.update_session_step(
            session.session_id, 
            'step2', 
            completed_step='step1'
        )
        assert success is True
        
        # Verify update
        status_info = self.provider_manager.get_provider_status(provider.id)
        updated_session = status_info['session']
        assert updated_session.current_step == 'step2'
        assert 'step1' in updated_session.completed_steps
    
    def test_mark_step_failed(self):
        """Test marking step as failed."""
        # Register provider and create session
        provider = self.provider_manager.register_provider('testuser9')
        session = self.provider_manager.create_onboarding_session(provider.id, 'step1')
        
        # Mark step as failed
        success = self.provider_manager.mark_step_failed(session.session_id, 'step1')
        assert success is True
        
        # Verify failure
        status_info = self.provider_manager.get_provider_status(provider.id)
        updated_session = status_info['session']
        assert 'step1' in updated_session.failed_steps
    
    def test_nonexistent_provider_operations(self):
        """Test operations on non-existent providers."""
        # Test getting non-existent provider
        provider = self.provider_manager.get_provider_by_id('nonexistent-id')
        assert provider is None
        
        provider = self.provider_manager.get_provider_by_username('nonexistent-user')
        assert provider is None
        
        # Test updating non-existent provider
        success = self.provider_manager.update_provider_status('nonexistent-id', ProviderStatus.ACTIVE)
        assert success is False
        
        # Test getting status of non-existent provider
        status = self.provider_manager.get_provider_status('nonexistent-id')
        assert status is None