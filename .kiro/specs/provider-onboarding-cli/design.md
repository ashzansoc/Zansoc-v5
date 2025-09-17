# Design Document

## Overview

The Provider Onboarding CLI is a Python-based command-line application that automates the complete setup process for new ZanSoc compute providers. The tool uses a step-by-step wizard approach with clear progress indicators, robust error handling, and platform-specific optimizations. It integrates with Tailscale for secure networking, Ray for distributed computing, and maintains a local database for provider registration.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Onboarding      │────│  External APIs  │
│   - Auth        │    │  Orchestrator    │    │  - Tailscale    │
│   - Menus       │    │  - Step Manager  │    │  - GitHub       │
│   - Progress    │    │  - Error Handler │    │  - Ray Cluster  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │    │  System Utils    │    │  Config Manager │
│   - Providers   │    │  - Platform Det. │    │  - Environment  │
│   - Sessions    │    │  - Process Exec. │    │  - Credentials  │
│   - Logs        │    │  - File Ops      │    │  - Settings     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Component Breakdown

1. **CLI Interface Layer**: Handles user interaction, authentication, and menu navigation
2. **Onboarding Orchestrator**: Manages the step-by-step onboarding workflow
3. **System Utilities**: Platform detection, process execution, and file operations
4. **Database Layer**: SQLite database for provider registration and session management
5. **Configuration Manager**: Handles environment variables, credentials, and settings

## Components and Interfaces

### 1. CLI Interface (`cli_interface.py`)

```python
class CLIInterface:
    def authenticate(self) -> bool
    def show_welcome(self) -> None
    def select_role(self) -> str
    def show_progress(self, step: str, status: str) -> None
    def show_congratulations(self, provider_info: dict) -> None
    def handle_error(self, error: Exception, step: str) -> bool
```

**Responsibilities:**
- User authentication with retry logic
- Role selection menu (Provider/User/Both)
- Progress visualization with loading animations
- Error display and user prompts
- Success confirmation screen

### 2. Onboarding Orchestrator (`onboarding_orchestrator.py`)

```python
class OnboardingOrchestrator:
    def start_provider_onboarding(self, user_id: str) -> bool
    def execute_step(self, step: OnboardingStep) -> StepResult
    def handle_step_failure(self, step: OnboardingStep, error: Exception) -> bool
    def validate_prerequisites(self) -> bool
    def cleanup_on_failure(self) -> None
```

**Workflow Steps:**
1. Provider Registration
2. Environment Setup (Miniconda, Python 3.13.7)
3. Repository Cloning
4. Dependencies Installation
5. Tailscale Installation & Configuration
6. Ray Cluster Connection
7. Verification & Confirmation

### 3. Provider Manager (`provider_manager.py`)

```python
class ProviderManager:
    def generate_provider_id(self) -> str
    def register_provider(self, provider_data: dict) -> str
    def store_provider_info(self, provider_id: str, info: dict) -> bool
    def get_provider_status(self, provider_id: str) -> dict
    def update_provider_status(self, provider_id: str, status: str) -> bool
```

**Database Schema:**
```sql
CREATE TABLE providers (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'registering',
    tailscale_ip TEXT,
    ray_node_id TEXT,
    platform TEXT,
    last_seen TIMESTAMP
);

CREATE TABLE onboarding_sessions (
    session_id TEXT PRIMARY KEY,
    provider_id TEXT,
    current_step TEXT,
    completed_steps TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES providers (id)
);
```

### 4. Environment Setup Manager (`environment_manager.py`)

```python
class EnvironmentManager:
    def install_miniconda(self) -> bool
    def create_conda_environment(self, python_version: str) -> bool
    def clone_repository(self, repo_url: str, target_dir: str) -> bool
    def install_requirements(self, requirements_file: str) -> bool
    def install_ray(self) -> bool
    def verify_installation(self) -> dict
```

**Installation Strategy:**
- Detect platform (Linux/macOS/Windows, x86_64/ARM64)
- Download appropriate Miniconda installer
- Create isolated conda environment
- Clone zansoc-beta repository
- Install Python dependencies with error handling
- Verify all installations

### 5. Tailscale Manager (`tailscale_manager.py`)

```python
class TailscaleManager:
    def install_tailscale(self) -> bool
    def authenticate_with_key(self, auth_key: str) -> bool
    def get_tailscale_ip(self) -> str
    def verify_connectivity(self, target_ip: str) -> bool
    def get_device_info(self) -> dict
```

**Installation Methods:**
- Primary: Official installation script
- Fallback: Manual binary installation for ARM64
- Verification: Network connectivity test
- Integration: Tailscale API for device management

### 6. Ray Cluster Manager (`ray_manager.py`)

```python
class RayManager:
    def connect_to_cluster(self, address: str, password: str) -> bool
    def verify_node_registration(self) -> bool
    def get_cluster_info(self) -> dict
    def disconnect_from_cluster(self) -> bool
    def get_node_status(self) -> dict
```

**Connection Process:**
- Set environment variables for cross-platform compatibility
- Connect to master node at specified address
- Authenticate with cluster password
- Verify successful registration
- Monitor connection health

### 7. Platform Utilities (`platform_utils.py`)

```python
class PlatformUtils:
    def detect_platform(self) -> dict
    def get_system_info(self) -> dict
    def check_prerequisites(self) -> list
    def execute_command(self, command: str, shell: bool = False) -> CommandResult
    def download_file(self, url: str, destination: str) -> bool
```

## Data Models

### Provider Data Model
```python
@dataclass
class Provider:
    id: str
    username: str
    status: str  # 'registering', 'setting_up', 'active', 'error'
    created_at: datetime
    tailscale_ip: Optional[str] = None
    ray_node_id: Optional[str] = None
    platform: Optional[str] = None
    last_seen: Optional[datetime] = None
```

### Onboarding Step Model
```python
@dataclass
class OnboardingStep:
    name: str
    description: str
    function: callable
    retry_count: int = 3
    timeout: int = 300
    prerequisites: List[str] = field(default_factory=list)
```

### Step Result Model
```python
@dataclass
class StepResult:
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[Exception] = None
    retry_suggested: bool = False
```

## Error Handling

### Error Categories
1. **Network Errors**: Connectivity issues, download failures
2. **Permission Errors**: Sudo access, file permissions
3. **Installation Errors**: Package installation failures
4. **Configuration Errors**: Invalid settings, missing files
5. **Platform Errors**: Unsupported OS, missing dependencies

### Error Handling Strategy
```python
class ErrorHandler:
    def handle_error(self, error: Exception, context: str) -> ErrorResponse
    def suggest_recovery(self, error_type: str) -> List[str]
    def log_error(self, error: Exception, context: str) -> None
    def should_retry(self, error: Exception, attempt: int) -> bool
```

### Recovery Mechanisms
- Automatic retry with exponential backoff
- Alternative installation methods
- Manual troubleshooting instructions
- Rollback capabilities for failed steps

## Testing Strategy

### Unit Tests
- Individual component functionality
- Error handling scenarios
- Platform-specific logic
- Database operations

### Integration Tests
- End-to-end onboarding workflow
- External service integration (Tailscale, Ray)
- Cross-platform compatibility
- Network connectivity scenarios

### Mock Testing
- Tailscale API responses
- Ray cluster connections
- File system operations
- Network requests

### Test Environment Setup
```python
class TestEnvironment:
    def setup_mock_cluster(self) -> None
    def create_test_database(self) -> None
    def mock_external_services(self) -> None
    def cleanup_test_environment(self) -> None
```

## Configuration Management

### Configuration Files
```yaml
# config/default.yaml
cluster:
  master_address: "100.101.84.71:6379"
  password: "zansoc_secure_password_change_me"
  
tailscale:
  auth_key: "tskey-auth-kd32Q6XdHS11CNTRL-X13DpHNm9ygqbdavCzngxgEJg91Rgie6"
  
environment:
  python_version: "3.13.7"
  repository_url: "https://github.com/zansoc/zansoc-beta.git"
  
database:
  path: "data/providers.db"
  
logging:
  level: "INFO"
  file: "logs/onboarding.log"
```

### Environment Variables
- `ZANSOC_CONFIG_PATH`: Custom configuration file path
- `ZANSOC_DATA_DIR`: Data directory for database and logs
- `RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER`: Ray cross-platform support

## Security Considerations

### Credential Management
- Secure storage of Tailscale auth keys
- Encrypted database for sensitive information
- No hardcoded passwords in source code
- Environment variable injection for secrets

### Network Security
- Tailscale VPN for all cluster communication
- Certificate validation for downloads
- Secure authentication with Ray cluster
- Network connectivity verification

### System Security
- Minimal privilege requirements
- Sandboxed installation processes
- Secure temporary file handling
- Clean cleanup on failure or exit

## Performance Considerations

### Installation Optimization
- Parallel downloads where possible
- Cached installations for repeated runs
- Minimal resource usage during setup
- Progress indicators for long-running operations

### Resource Management
- Memory-efficient operations
- Disk space verification before installation
- Network bandwidth consideration
- CPU usage monitoring during setup

## Deployment Strategy

### Distribution
- Single executable using PyInstaller
- Cross-platform compatibility
- Minimal external dependencies
- Self-contained installation package

### Installation Methods
1. Direct download from GitHub releases
2. Package manager integration (pip, homebrew)
3. Docker container for isolated execution
4. Web-based installer for guided setup