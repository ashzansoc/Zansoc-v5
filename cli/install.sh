#!/bin/bash
# ZanSoc Provider Onboarding Installer for Ubuntu/Linux
# This script downloads and installs the ZanSoc CLI for seamless provider onboarding

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
ZANSOC_DIR="$HOME/.zansoc"
VENV_DIR="$ZANSOC_DIR/venv"
ARCHIVE_URL="https://github.com/ashzansoc/Zansoc-v5/archive/refs/heads/main.zip"
PYTHON_MIN_VERSION="3.9"
PYTHON_TARGET_VERSION="3.13.7"

# Logging
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🚀 ZanSoc Provider Setup                  ║"
    echo "║                                                              ║"
    echo "║  Welcome to the ZanSoc distributed compute network!         ║"
    echo "║  This installer will set up your device as a provider.      ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
}

# Check if running on supported OS
check_os() {
    log_info "Checking operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v lsb_release >/dev/null 2>&1; then
            OS_NAME=$(lsb_release -si)
            OS_VERSION=$(lsb_release -sr)
            log_info "Detected: $OS_NAME $OS_VERSION"
            
            if [[ "$OS_NAME" == "Ubuntu" ]]; then
                log_success "Ubuntu detected - fully supported!"
            else
                log_warning "Non-Ubuntu Linux detected - should work but not fully tested"
            fi
        else
            log_info "Linux detected (distribution unknown)"
        fi
    else
        log_error "Unsupported operating system: $OSTYPE"
        log_error "This installer is designed for Ubuntu/Linux systems"
        exit 1
    fi
}

# Check Python version and ensure pip is available
check_python() {
    log_info "Checking Python installation..."
    
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        log_info "Found Python $PYTHON_VERSION"
        
        # Check if version is sufficient
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
            log_success "Python version is compatible"
            if [[ "$PYTHON_VERSION" == "3.13"* ]]; then
                log_success "Python 3.13 detected - optimal for ZanSoc"
            fi
        else
            log_error "Python $PYTHON_MIN_VERSION or higher is required"
            log_error "Please install a newer version of Python"
            exit 1
        fi
    else
        log_error "Python 3 is not installed"
        log_info "Installing Python 3..."
        sudo apt update
        sudo apt install -y python3
    fi
    
    # Ensure pip is available
    log_info "Checking pip availability..."
    if ! python3 -m pip --version >/dev/null 2>&1; then
        log_info "Pip not found, installing..."
        install_pip_manually
    else
        log_success "Pip is available"
    fi
}

# Check required system packages
check_dependencies() {
    log_info "Checking system dependencies..."
    
    MISSING_DEPS=()
    
    # Check for curl or wget (at least one is needed for download)
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        MISSING_DEPS+=("curl")
    fi
    
    # Check for unzip (needed for archive extraction)
    if ! command -v unzip >/dev/null 2>&1; then
        MISSING_DEPS+=("unzip")
    fi
    
    # Check for python3-venv (needed for virtual environments)
    if ! python3 -m venv --help >/dev/null 2>&1; then
        # Try generic python3-venv first, then version-specific
        MISSING_DEPS+=("python3-venv")
    fi
    
    # Note: We'll handle pip installation separately since package manager might not work
    
    if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
        log_warning "Missing dependencies: ${MISSING_DEPS[*]}"
        log_info "Installing missing dependencies..."
        sudo apt update
        sudo apt install -y "${MISSING_DEPS[@]}"
        log_success "Dependencies installed"
    else
        log_success "All dependencies are available"
    fi
}

# Install pip manually when package manager fails
install_pip_manually() {
    log_info "Installing pip manually..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Download get-pip.py
    if command -v curl >/dev/null 2>&1; then
        curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    elif command -v wget >/dev/null 2>&1; then
        wget -q https://bootstrap.pypa.io/get-pip.py -O get-pip.py
    else
        log_error "Neither curl nor wget available for downloading pip"
        return 1
    fi
    
    # Install pip in user mode (handle PEP 668 externally-managed-environment)
    if python3 get-pip.py --user --quiet --break-system-packages 2>/dev/null || python3 get-pip.py --user --quiet; then
        log_success "Pip installed successfully"
        
        # Add ~/.local/bin to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            export PATH="$HOME/.local/bin:$PATH"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
            log_info "Added ~/.local/bin to PATH"
        fi
        
        # Verify pip installation
        if python3 -m pip --version >/dev/null 2>&1; then
            log_success "Pip verification successful"
        else
            log_warning "Pip installed but not immediately available"
        fi
    else
        log_error "Failed to install pip manually"
        return 1
    fi
    
    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"
}

# Create ZanSoc directory structure
create_directories() {
    log_info "Creating ZanSoc directories..."
    
    mkdir -p "$ZANSOC_DIR"
    mkdir -p "$ZANSOC_DIR/logs"
    mkdir -p "$ZANSOC_DIR/data"
    mkdir -p "$ZANSOC_DIR/config"
    
    log_success "Directories created at $ZANSOC_DIR"
}

# Download repository as ZIP archive (no authentication required)
setup_repository() {
    log_info "Setting up ZanSoc repository..."
    
    cd "$ZANSOC_DIR"
    
    # Remove existing directories if they exist (clean up old installations)
    if [ -d "Zansoc-v5" ]; then
        log_info "Removing existing Zansoc-v5 installation..."
        rm -rf "Zansoc-v5"
    fi
    
    if [ -d "zansoc-beta" ]; then
        log_info "Removing old zansoc-beta installation..."
        rm -rf "zansoc-beta"
    fi
    
    # Download the latest version as ZIP archive
    log_info "Downloading latest version from GitHub..."
    
    if command -v wget >/dev/null 2>&1; then
        if ! wget -O zansoc-main.zip "$ARCHIVE_URL" 2>/dev/null; then
            log_error "Failed to download repository with wget"
            exit 1
        fi
    elif command -v curl >/dev/null 2>&1; then
        if ! curl -L -o zansoc-main.zip "$ARCHIVE_URL" 2>/dev/null; then
            log_error "Failed to download repository with curl"
            exit 1
        fi
    else
        log_error "Neither wget nor curl available for download"
        exit 1
    fi
    
    # Extract archive
    log_info "Extracting archive..."
    if ! unzip -q zansoc-main.zip 2>/dev/null; then
        log_error "Failed to extract archive"
        rm -f zansoc-main.zip
        exit 1
    fi
    
    # Rename extracted directory
    mv Zansoc-v5-main Zansoc-v5
    rm zansoc-main.zip
    
    log_success "Repository downloaded and extracted successfully"
}

# Create Python virtual environment (with fallback to user install)
create_venv() {
    log_info "Setting up Python environment..."
    
    # Try to create virtual environment
    if python3 -m venv --help >/dev/null 2>&1; then
        if [ -d "$VENV_DIR" ]; then
            log_info "Virtual environment exists, recreating..."
            rm -rf "$VENV_DIR"
        fi
        
        if python3 -m venv "$VENV_DIR" 2>/dev/null; then
            source "$VENV_DIR/bin/activate"
            pip install --upgrade pip
            log_success "Virtual environment created"
            return 0
        else
            log_warning "Virtual environment creation failed, using user install mode"
        fi
    else
        log_warning "Virtual environment not available, using user install mode"
    fi
    
    # Fallback: ensure pip is available for user installs
    if ! python3 -m pip --version >/dev/null 2>&1; then
        log_info "Pip not found, installing pip manually..."
        install_pip_manually
    fi
    
    # Create a flag file to indicate we're using user mode
    touch "$ZANSOC_DIR/.user_mode"
    log_success "Python environment ready (user install mode)"
}

# Install ZanSoc CLI
install_cli() {
    log_info "Installing ZanSoc CLI..."
    
    cd "$ZANSOC_DIR/Zansoc-v5/cli"
    
    # Check if we're using virtual environment or user mode
    if [ -f "$ZANSOC_DIR/.user_mode" ]; then
        log_info "Installing in user mode..."
        # Handle PEP 668 externally-managed-environment
        python3 -m pip install --user -e . --break-system-packages 2>/dev/null || python3 -m pip install --user -e .
    else
        source "$VENV_DIR/bin/activate"
        pip install -e .
    fi
    
    log_success "ZanSoc CLI installed"
}

# Create launcher script
create_launcher() {
    log_info "Creating launcher script..."
    
    LAUNCHER_PATH="$ZANSOC_DIR/zansoc"
    
    # Create launcher based on installation mode
    if [ -f "$ZANSOC_DIR/.user_mode" ]; then
        cat > "$LAUNCHER_PATH" << 'EOF'
#!/bin/bash
# ZanSoc CLI Launcher (User Mode)

# Run ZanSoc CLI with user-installed packages
exec python3 -m zansoc_cli.seamless_cli "$@"
EOF
    else
        cat > "$LAUNCHER_PATH" << 'EOF'
#!/bin/bash
# ZanSoc CLI Launcher (Virtual Environment)

ZANSOC_DIR="$HOME/.zansoc"
VENV_DIR="$ZANSOC_DIR/venv"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run ZanSoc CLI
exec python -m zansoc_cli.seamless_cli "$@"
EOF
    fi
    
    chmod +x "$LAUNCHER_PATH"
    
    # Create symlink in user's local bin if it exists
    if [ -d "$HOME/.local/bin" ]; then
        ln -sf "$LAUNCHER_PATH" "$HOME/.local/bin/zansoc"
        log_success "Launcher created and linked to ~/.local/bin/zansoc"
    else
        log_success "Launcher created at $LAUNCHER_PATH"
        log_info "Add $ZANSOC_DIR to your PATH to use 'zansoc' command globally"
    fi
}

# Create desktop entry (optional)
create_desktop_entry() {
    log_info "Creating desktop entry..."
    
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    
    cat > "$DESKTOP_DIR/zansoc.desktop" << EOF
[Desktop Entry]
Name=ZanSoc Provider
Comment=Join the ZanSoc distributed compute network
Exec=$ZANSOC_DIR/zansoc
Icon=computer
Terminal=true
Type=Application
Categories=Network;System;
Keywords=zansoc;provider;distributed;computing;
EOF
    
    log_success "Desktop entry created"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    # Check if we're using virtual environment or user mode
    if [ -f "$ZANSOC_DIR/.user_mode" ]; then
        # User mode - test with system python
        if python3 -c "import zansoc_cli; print('ZanSoc CLI imported successfully')" 2>/dev/null; then
            log_success "Installation verified successfully (user mode)"
            return 0
        else
            log_error "Installation verification failed (user mode)"
            return 1
        fi
    else
        # Virtual environment mode
        source "$VENV_DIR/bin/activate"
        if python -c "import zansoc_cli; print('ZanSoc CLI imported successfully')" 2>/dev/null; then
            log_success "Installation verified successfully (virtual environment)"
            return 0
        else
            log_error "Installation verification failed (virtual environment)"
            return 1
        fi
    fi
}

# Show completion message
show_completion() {
    echo
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   ✅ Installation Complete!                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
    echo -e "${CYAN}🚀 ZanSoc Provider CLI is now installed!${NC}"
    echo
    echo -e "${YELLOW}To start onboarding as a provider:${NC}"
    echo -e "  ${GREEN}$ZANSOC_DIR/zansoc${NC}"
    echo
    if [ -d "$HOME/.local/bin" ]; then
        echo -e "${YELLOW}Or if ~/.local/bin is in your PATH:${NC}"
        echo -e "  ${GREEN}zansoc${NC}"
        echo
    fi
    echo -e "${YELLOW}What happens next:${NC}"
    echo -e "  • Enter your credentials (admin/admin for demo)"
    echo -e "  • Automatic environment setup"
    echo -e "  • Tailscale VPN configuration"
    echo -e "  • Ray cluster connection"
    echo -e "  • Start earning rewards!"
    echo
    echo -e "${CYAN}Installation location: $ZANSOC_DIR${NC}"
    echo -e "${CYAN}Logs will be saved to: $ZANSOC_DIR/logs${NC}"
    echo
}

# Cleanup on error
cleanup_on_error() {
    log_error "Installation failed. Cleaning up..."
    
    if [ -d "$ZANSOC_DIR" ]; then
        read -p "Remove partial installation at $ZANSOC_DIR? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$ZANSOC_DIR"
            log_info "Cleanup completed"
        fi
    fi
}

# Main installation function
main() {
    # Set up error handling
    trap cleanup_on_error ERR
    
    show_banner
    
    # Check system requirements
    check_os
    check_python
    check_dependencies
    
    # Install ZanSoc
    create_directories
    setup_repository
    create_venv
    install_cli
    create_launcher
    create_desktop_entry
    
    # Verify and complete
    if verify_installation; then
        show_completion
    else
        log_error "Installation completed but verification failed"
        exit 1
    fi
}

# Run main function
main "$@"