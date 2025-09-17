"""Tests for DatabaseManager class."""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from zansoc_cli.database import DatabaseManager
from zansoc_cli.models import Provider, ProviderStatus


class TestDatabaseManager:
    """Test cases for DatabaseManager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.db = DatabaseManager(self.temp_db.name)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization creates required tables."""
        # Check that tables exist
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check providers table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='providers'
            """)
            assert cursor.fetchone() is not None
            
            # Check onboarding_sessions table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='onboarding_sessions'
            """)
            assert cursor.fetchone() is not None
    
    def test_insert_and_get_provider(self):
        """Test inserting and retrieving provider."""
        provider_data = {
            'id': 'test-provider-123',
            'username': 'testuser',
            'status': 'registering',
            'created_at': datetime.now().isoformat(),
            'tailscale_ip': None,
            'ray_node_id': None,
            'platform': None,
            'last_seen': None,
        }
        
        # Insert provider
        success = self.db.insert_provider(provider_data)
        assert success is True
        
        # Retrieve by ID
        retrieved = self.db.get_provider_by_id('test-provider-123')
        assert retrieved is not None
        assert retrieved['id'] == 'test-provider-123'
        assert retrieved['username'] == 'testuser'
        assert retrieved['status'] == 'registering'
        
        # Retrieve by username
        retrieved = self.db.get_provider_by_username('testuser')
        assert retrieved is not None
        assert retrieved['id'] == 'test-provider-123'
    
    def test_update_provider(self):
        """Test updating provider information."""
        # Insert initial provider
        provider_data = {
            'id': 'test-provider-456',
            'username': 'testuser2',
            'status': 'registering',
            'created_at': datetime.now().isoformat(),
            'tailscale_ip': None,
            'ray_node_id': None,
            'platform': None,
            'last_seen': None,
        }
        
        self.db.insert_provider(provider_data)
        
        # Update provider
        updates = {
            'status': 'active',
            'tailscale_ip': '100.64.0.1',
            'platform': 'linux-x86_64'
        }
        
        success = self.db.update_provider('test-provider-456', updates)
        assert success is True
        
        # Verify updates
        retrieved = self.db.get_provider_by_id('test-provider-456')
        assert retrieved['status'] == 'active'
        assert retrieved['tailscale_ip'] == '100.64.0.1'
        assert retrieved['platform'] == 'linux-x86_64'
    
    def test_insert_and_get_session(self):
        """Test inserting and retrieving onboarding session."""
        # First insert a provider
        provider_data = {
            'id': 'test-provider-789',
            'username': 'testuser3',
            'status': 'registering',
            'created_at': datetime.now().isoformat(),
            'tailscale_ip': None,
            'ray_node_id': None,
            'platform': None,
            'last_seen': None,
        }
        self.db.insert_provider(provider_data)
        
        # Insert session
        session_data = {
            'session_id': 'session-123',
            'provider_id': 'test-provider-789',
            'current_step': 'registration',
            'completed_steps': 'step1,step2',
            'failed_steps': '',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        
        success = self.db.insert_session(session_data)
        assert success is True
        
        # Retrieve session
        retrieved = self.db.get_session_by_provider('test-provider-789')
        assert retrieved is not None
        assert retrieved['session_id'] == 'session-123'
        assert retrieved['provider_id'] == 'test-provider-789'
        assert retrieved['current_step'] == 'registration'
        assert retrieved['completed_steps'] == 'step1,step2'
    
    def test_update_session(self):
        """Test updating onboarding session."""
        # Insert provider and session
        provider_data = {
            'id': 'test-provider-999',
            'username': 'testuser4',
            'status': 'registering',
            'created_at': datetime.now().isoformat(),
            'tailscale_ip': None,
            'ray_node_id': None,
            'platform': None,
            'last_seen': None,
        }
        self.db.insert_provider(provider_data)
        
        session_data = {
            'session_id': 'session-456',
            'provider_id': 'test-provider-999',
            'current_step': 'registration',
            'completed_steps': '',
            'failed_steps': '',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        self.db.insert_session(session_data)
        
        # Update session
        updates = {
            'current_step': 'environment_setup',
            'completed_steps': 'registration,provider_setup',
            'updated_at': datetime.now().isoformat()
        }
        
        success = self.db.update_session('session-456', updates)
        assert success is True
        
        # Verify updates
        retrieved = self.db.get_session_by_provider('test-provider-999')
        assert retrieved['current_step'] == 'environment_setup'
        assert retrieved['completed_steps'] == 'registration,provider_setup'
    
    def test_get_providers_by_status(self):
        """Test filtering providers by status."""
        # Insert providers with different statuses
        providers = [
            {
                'id': 'provider-active-1',
                'username': 'active1',
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'tailscale_ip': None,
                'ray_node_id': None,
                'platform': None,
                'last_seen': None,
            },
            {
                'id': 'provider-active-2',
                'username': 'active2',
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'tailscale_ip': None,
                'ray_node_id': None,
                'platform': None,
                'last_seen': None,
            },
            {
                'id': 'provider-registering-1',
                'username': 'registering1',
                'status': 'registering',
                'created_at': datetime.now().isoformat(),
                'tailscale_ip': None,
                'ray_node_id': None,
                'platform': None,
                'last_seen': None,
            }
        ]
        
        for provider in providers:
            self.db.insert_provider(provider)
        
        # Get active providers
        active_providers = self.db.get_providers_by_status('active')
        assert len(active_providers) == 2
        
        # Get registering providers
        registering_providers = self.db.get_providers_by_status('registering')
        assert len(registering_providers) == 1
        
        # Get all providers
        all_providers = self.db.get_all_providers()
        assert len(all_providers) == 3
    
    def test_nonexistent_provider(self):
        """Test retrieving non-existent provider."""
        result = self.db.get_provider_by_id('nonexistent-id')
        assert result is None
        
        result = self.db.get_provider_by_username('nonexistent-user')
        assert result is None
    
    def test_duplicate_provider_id(self):
        """Test handling duplicate provider ID."""
        provider_data = {
            'id': 'duplicate-id',
            'username': 'user1',
            'status': 'registering',
            'created_at': datetime.now().isoformat(),
            'tailscale_ip': None,
            'ray_node_id': None,
            'platform': None,
            'last_seen': None,
        }
        
        # Insert first provider
        success1 = self.db.insert_provider(provider_data)
        assert success1 is True
        
        # Try to insert duplicate
        provider_data['username'] = 'user2'  # Different username, same ID
        success2 = self.db.insert_provider(provider_data)
        assert success2 is False  # Should fail due to primary key constraint