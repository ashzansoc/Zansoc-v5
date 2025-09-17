"""Data models for ZanSoc CLI."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ProviderStatus(Enum):
    """Provider status enumeration."""
    REGISTERING = "registering"
    SETTING_UP = "setting_up"
    ACTIVE = "active"
    ERROR = "error"
    OFFLINE = "offline"


class OnboardingStepStatus(Enum):
    """Onboarding step status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Provider:
    """Provider data model."""
    id: str
    username: str
    status: ProviderStatus = ProviderStatus.REGISTERING
    created_at: datetime = field(default_factory=datetime.now)
    tailscale_ip: Optional[str] = None
    ray_node_id: Optional[str] = None
    platform: Optional[str] = None
    last_seen: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert provider to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'tailscale_ip': self.tailscale_ip,
            'ray_node_id': self.ray_node_id,
            'platform': self.platform,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Provider':
        """Create provider from dictionary."""
        return cls(
            id=data['id'],
            username=data['username'],
            status=ProviderStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            tailscale_ip=data.get('tailscale_ip'),
            ray_node_id=data.get('ray_node_id'),
            platform=data.get('platform'),
            last_seen=datetime.fromisoformat(data['last_seen']) if data.get('last_seen') else None,
        )


@dataclass
class OnboardingSession:
    """Onboarding session data model."""
    session_id: str
    provider_id: str
    current_step: str
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            'session_id': self.session_id,
            'provider_id': self.provider_id,
            'current_step': self.current_step,
            'completed_steps': ','.join(self.completed_steps),
            'failed_steps': ','.join(self.failed_steps),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OnboardingSession':
        """Create session from dictionary."""
        return cls(
            session_id=data['session_id'],
            provider_id=data['provider_id'],
            current_step=data['current_step'],
            completed_steps=data['completed_steps'].split(',') if data['completed_steps'] else [],
            failed_steps=data['failed_steps'].split(',') if data['failed_steps'] else [],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
        )


@dataclass
class OnboardingStep:
    """Onboarding step definition."""
    name: str
    description: str
    function: callable
    retry_count: int = 3
    timeout: int = 300
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result of an onboarding step execution."""
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[Exception] = None
    retry_suggested: bool = False