"""Tests for data models."""

import pytest
from datetime import datetime

from zansoc_cli.models import Provider, ProviderStatus, OnboardingSession, OnboardingStep, StepResult


class TestProvider:
    """Test cases for Provider model."""
    
    def test_provider_creation(self):
        """Test creating a provider instance."""
        provider = Provider(
            id='test-provider-123',
            username='testuser',
            status=ProviderStatus.REGISTERING
        )
        
        assert provider.id == 'test-provider-123'
        assert provider.username == 'testuser'
        assert provider.status == ProviderStatus.REGISTERING
        assert isinstance(provider.created_at, datetime)
        assert provider.tailscale_ip is None
        assert provider.ray_node_id is None
        assert provider.platform is None
        assert provider.last_seen is None
    
    def test_provider_to_dict(self):
        """Test converting provider to dictionary."""
        created_at = datetime.now()
        last_seen = datetime.now()
        
        provider = Provider(
            id='test-provider-456',
            username='testuser2',
            status=ProviderStatus.ACTIVE,
            created_at=created_at,
            tailscale_ip='100.64.0.1',
            ray_node_id='ray-node-123',
            platform='linux-x86_64',
            last_seen=last_seen
        )
        
        provider_dict = provider.to_dict()
        
        assert provider_dict['id'] == 'test-provider-456'
        assert provider_dict['username'] == 'testuser2'
        assert provider_dict['status'] == 'active'
        assert provider_dict['created_at'] == created_at.isoformat()
        assert provider_dict['tailscale_ip'] == '100.64.0.1'
        assert provider_dict['ray_node_id'] == 'ray-node-123'
        assert provider_dict['platform'] == 'linux-x86_64'
        assert provider_dict['last_seen'] == last_seen.isoformat()
    
    def test_provider_from_dict(self):
        """Test creating provider from dictionary."""
        created_at = datetime.now()
        last_seen = datetime.now()
        
        provider_dict = {
            'id': 'test-provider-789',
            'username': 'testuser3',
            'status': 'setting_up',
            'created_at': created_at.isoformat(),
            'tailscale_ip': '100.64.0.2',
            'ray_node_id': 'ray-node-456',
            'platform': 'darwin-arm64',
            'last_seen': last_seen.isoformat()
        }
        
        provider = Provider.from_dict(provider_dict)
        
        assert provider.id == 'test-provider-789'
        assert provider.username == 'testuser3'
        assert provider.status == ProviderStatus.SETTING_UP
        assert provider.created_at == created_at
        assert provider.tailscale_ip == '100.64.0.2'
        assert provider.ray_node_id == 'ray-node-456'
        assert provider.platform == 'darwin-arm64'
        assert provider.last_seen == last_seen
    
    def test_provider_from_dict_with_none_values(self):
        """Test creating provider from dictionary with None values."""
        created_at = datetime.now()
        
        provider_dict = {
            'id': 'test-provider-999',
            'username': 'testuser4',
            'status': 'registering',
            'created_at': created_at.isoformat(),
            'tailscale_ip': None,
            'ray_node_id': None,
            'platform': None,
            'last_seen': None
        }
        
        provider = Provider.from_dict(provider_dict)
        
        assert provider.id == 'test-provider-999'
        assert provider.username == 'testuser4'
        assert provider.status == ProviderStatus.REGISTERING
        assert provider.created_at == created_at
        assert provider.tailscale_ip is None
        assert provider.ray_node_id is None
        assert provider.platform is None
        assert provider.last_seen is None


class TestOnboardingSession:
    """Test cases for OnboardingSession model."""
    
    def test_session_creation(self):
        """Test creating an onboarding session."""
        session = OnboardingSession(
            session_id='session-123',
            provider_id='provider-456',
            current_step='registration'
        )
        
        assert session.session_id == 'session-123'
        assert session.provider_id == 'provider-456'
        assert session.current_step == 'registration'
        assert len(session.completed_steps) == 0
        assert len(session.failed_steps) == 0
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        created_at = datetime.now()
        updated_at = datetime.now()
        
        session = OnboardingSession(
            session_id='session-789',
            provider_id='provider-123',
            current_step='environment_setup',
            completed_steps=['registration', 'provider_setup'],
            failed_steps=['network_test'],
            created_at=created_at,
            updated_at=updated_at
        )
        
        session_dict = session.to_dict()
        
        assert session_dict['session_id'] == 'session-789'
        assert session_dict['provider_id'] == 'provider-123'
        assert session_dict['current_step'] == 'environment_setup'
        assert session_dict['completed_steps'] == 'registration,provider_setup'
        assert session_dict['failed_steps'] == 'network_test'
        assert session_dict['created_at'] == created_at.isoformat()
        assert session_dict['updated_at'] == updated_at.isoformat()
    
    def test_session_from_dict(self):
        """Test creating session from dictionary."""
        created_at = datetime.now()
        updated_at = datetime.now()
        
        session_dict = {
            'session_id': 'session-999',
            'provider_id': 'provider-888',
            'current_step': 'ray_connection',
            'completed_steps': 'registration,provider_setup,environment_setup',
            'failed_steps': '',
            'created_at': created_at.isoformat(),
            'updated_at': updated_at.isoformat()
        }
        
        session = OnboardingSession.from_dict(session_dict)
        
        assert session.session_id == 'session-999'
        assert session.provider_id == 'provider-888'
        assert session.current_step == 'ray_connection'
        assert session.completed_steps == ['registration', 'provider_setup', 'environment_setup']
        assert session.failed_steps == []
        assert session.created_at == created_at
        assert session.updated_at == updated_at
    
    def test_session_empty_steps(self):
        """Test session with empty completed/failed steps."""
        session_dict = {
            'session_id': 'session-empty',
            'provider_id': 'provider-empty',
            'current_step': 'initial',
            'completed_steps': '',
            'failed_steps': '',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        session = OnboardingSession.from_dict(session_dict)
        
        assert session.completed_steps == []
        assert session.failed_steps == []


class TestOnboardingStep:
    """Test cases for OnboardingStep model."""
    
    def test_step_creation(self):
        """Test creating an onboarding step."""
        def dummy_function():
            pass
        
        step = OnboardingStep(
            name='test_step',
            description='Test step description',
            function=dummy_function
        )
        
        assert step.name == 'test_step'
        assert step.description == 'Test step description'
        assert step.function == dummy_function
        assert step.retry_count == 3  # default
        assert step.timeout == 300  # default
        assert step.prerequisites == []  # default
    
    def test_step_with_custom_values(self):
        """Test creating step with custom values."""
        def custom_function():
            pass
        
        step = OnboardingStep(
            name='custom_step',
            description='Custom step',
            function=custom_function,
            retry_count=5,
            timeout=600,
            prerequisites=['step1', 'step2']
        )
        
        assert step.name == 'custom_step'
        assert step.description == 'Custom step'
        assert step.function == custom_function
        assert step.retry_count == 5
        assert step.timeout == 600
        assert step.prerequisites == ['step1', 'step2']


class TestStepResult:
    """Test cases for StepResult model."""
    
    def test_successful_result(self):
        """Test creating successful step result."""
        result = StepResult(
            success=True,
            message='Step completed successfully',
            data={'key': 'value'}
        )
        
        assert result.success is True
        assert result.message == 'Step completed successfully'
        assert result.data == {'key': 'value'}
        assert result.error is None
        assert result.retry_suggested is False
    
    def test_failed_result(self):
        """Test creating failed step result."""
        error = Exception('Test error')
        
        result = StepResult(
            success=False,
            message='Step failed',
            error=error,
            retry_suggested=True
        )
        
        assert result.success is False
        assert result.message == 'Step failed'
        assert result.data is None
        assert result.error == error
        assert result.retry_suggested is True


class TestProviderStatus:
    """Test cases for ProviderStatus enum."""
    
    def test_status_values(self):
        """Test provider status enum values."""
        assert ProviderStatus.REGISTERING.value == 'registering'
        assert ProviderStatus.SETTING_UP.value == 'setting_up'
        assert ProviderStatus.ACTIVE.value == 'active'
        assert ProviderStatus.ERROR.value == 'error'
        assert ProviderStatus.OFFLINE.value == 'offline'
    
    def test_status_from_string(self):
        """Test creating status from string."""
        status = ProviderStatus('active')
        assert status == ProviderStatus.ACTIVE
        
        status = ProviderStatus('registering')
        assert status == ProviderStatus.REGISTERING