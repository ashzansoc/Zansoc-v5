# Requirements Document

## Introduction

The Provider Onboarding CLI is a command-line tool that enables users to easily join the ZanSoc distributed compute network as resource providers. The tool handles authentication, role selection, provider registration, and complete automated setup of their device as a compute node in the Ray cluster network. It provides a streamlined onboarding experience that automates all technical setup steps including Tailscale VPN enrollment, environment configuration, and Ray cluster connection.

## Requirements

### Requirement 1: User Authentication

**User Story:** As a new user, I want to authenticate with the ZanSoc platform using simple credentials, so that I can access the onboarding dashboard.

#### Acceptance Criteria

1. WHEN the CLI starts THEN the system SHALL prompt for username and password
2. WHEN user enters "admin" as username and "admin" as password THEN the system SHALL authenticate successfully
3. WHEN authentication is successful THEN the system SHALL display "Welcome to ZanSoc Dashboard" message
4. WHEN authentication fails THEN the system SHALL display error message and prompt again
5. WHEN user enters invalid credentials 3 times THEN the system SHALL exit with appropriate message

### Requirement 2: Role Selection

**User Story:** As an authenticated user, I want to choose my role in the ZanSoc network, so that I can access the appropriate features and workflows.

#### Acceptance Criteria

1. WHEN authentication succeeds THEN the system SHALL present role selection options: "Provider", "User", or "Both"
2. WHEN user selects "Provider" THEN the system SHALL initiate provider onboarding workflow
3. WHEN user selects "User" THEN the system SHALL display message about future user features
4. WHEN user selects "Both" THEN the system SHALL initiate provider onboarding workflow first
5. WHEN invalid selection is made THEN the system SHALL prompt again with valid options

### Requirement 3: Provider Registration

**User Story:** As a user choosing to be a provider, I want the system to create a unique provider ID and register me in the network, so that I can be identified and tracked as a resource provider.

#### Acceptance Criteria

1. WHEN user selects provider role THEN the system SHALL generate a unique provider ID
2. WHEN provider ID is generated THEN the system SHALL store provider information in database table
3. WHEN provider registration completes THEN the system SHALL display the assigned provider ID
4. WHEN database storage fails THEN the system SHALL display error and allow retry
5. WHEN provider ID already exists THEN the system SHALL handle duplicate gracefully

### Requirement 4: Environment Setup

**User Story:** As a provider, I want the system to automatically set up my development environment, so that my device can run Ray cluster workloads.

#### Acceptance Criteria

1. WHEN provider registration completes THEN the system SHALL download and install miniconda
2. WHEN miniconda installation completes THEN the system SHALL create conda environment with Python 3.13.7
3. WHEN conda environment is ready THEN the system SHALL clone the zansoc-beta repository
4. WHEN repository is cloned THEN the system SHALL install requirements from requirements.txt
5. WHEN requirements installation completes THEN the system SHALL install Ray with all components
6. WHEN any installation step fails THEN the system SHALL display error and provide retry option

### Requirement 5: Tailscale Network Integration

**User Story:** As a provider, I want my device to be automatically connected to the ZanSoc private network via Tailscale, so that it can securely communicate with other nodes in the cluster.

#### Acceptance Criteria

1. WHEN environment setup completes THEN the system SHALL install Tailscale using the official installation script
2. WHEN Tailscale installation completes THEN the system SHALL authenticate using the provided auth key
3. WHEN Tailscale authentication succeeds THEN the system SHALL enable Tailscale service
4. WHEN Tailscale is enabled THEN the system SHALL verify network connectivity to the cluster
5. WHEN Tailscale setup fails THEN the system SHALL attempt alternative installation method for ARM64 devices
6. WHEN alternative installation is used THEN the system SHALL manually extract and configure Tailscale binaries

### Requirement 6: Ray Cluster Connection

**User Story:** As a provider, I want my device to automatically join the Ray cluster as a worker node, so that it can receive and process distributed compute tasks.

#### Acceptance Criteria

1. WHEN Tailscale setup completes THEN the system SHALL set RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER environment variable
2. WHEN environment variable is set THEN the system SHALL connect to Ray cluster at address '100.101.84.71:6379'
3. WHEN connecting to cluster THEN the system SHALL use password 'zansoc_secure_password_change_me'
4. WHEN Ray connection succeeds THEN the system SHALL verify node is registered in cluster
5. WHEN Ray connection fails THEN the system SHALL display error and provide troubleshooting steps

### Requirement 7: Progress Tracking and Feedback

**User Story:** As a provider going through onboarding, I want to see clear progress indicators and status updates, so that I understand what's happening and can identify any issues.

#### Acceptance Criteria

1. WHEN each setup step begins THEN the system SHALL display step name and progress indicator
2. WHEN step is in progress THEN the system SHALL show loading animation or progress bar
3. WHEN step completes successfully THEN the system SHALL display success message with checkmark
4. WHEN step fails THEN the system SHALL display error message with details
5. WHEN all steps complete THEN the system SHALL display overall progress summary

### Requirement 8: Success Confirmation

**User Story:** As a provider who has completed onboarding, I want to see a congratulations screen with confirmation details, so that I know my device is successfully enrolled and ready to earn rewards.

#### Acceptance Criteria

1. WHEN all onboarding steps complete successfully THEN the system SHALL display congratulations screen
2. WHEN congratulations screen shows THEN the system SHALL display provider ID and node status
3. WHEN congratulations screen shows THEN the system SHALL display Tailscale IP address
4. WHEN congratulations screen shows THEN the system SHALL display Ray cluster connection status
5. WHEN congratulations screen shows THEN the system SHALL provide next steps information

### Requirement 9: Error Handling and Recovery

**User Story:** As a provider experiencing setup issues, I want clear error messages and recovery options, so that I can successfully complete the onboarding process.

#### Acceptance Criteria

1. WHEN any step fails THEN the system SHALL display specific error message with cause
2. WHEN error occurs THEN the system SHALL provide retry option for failed step
3. WHEN multiple retries fail THEN the system SHALL provide manual troubleshooting instructions
4. WHEN network connectivity issues occur THEN the system SHALL detect and report network problems
5. WHEN system requirements are not met THEN the system SHALL display compatibility requirements

### Requirement 10: Cross-Platform Compatibility

**User Story:** As a provider using different types of devices, I want the CLI tool to work on various platforms, so that I can contribute resources regardless of my hardware setup.

#### Acceptance Criteria

1. WHEN running on Linux systems THEN the system SHALL use standard installation methods
2. WHEN running on ARM64 devices THEN the system SHALL use ARM64-specific Tailscale installation
3. WHEN running on Raspberry Pi THEN the system SHALL optimize installation for limited resources
4. WHEN running on macOS/Windows THEN the system SHALL set appropriate Ray cluster environment variables
5. WHEN platform detection fails THEN the system SHALL prompt user for manual platform selection