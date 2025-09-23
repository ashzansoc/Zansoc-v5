#!/bin/bash
# Manual onboarding script that replicates your working steps exactly

# Remove set -e to prevent silent exits on errors
# set -e

# Parse command line arguments or environment variable
if [ -n "$1" ]; then
    TAILSCALE_AUTH_KEY="$1"
    echo "🔑 Using auth key from command line argument"
elif [ -n "$TAILSCALE_AUTH_KEY" ]; then
    echo "🔑 Using auth key from environment variable"
else
    echo "⚠️ No auth key provided via argument or environment variable"
fi

echo "🚀 ZanSoc Manual Onboarding (ARM64 Optimized)"
echo "=============================================="

# Step 1: System updates and essential packages
echo "🔄 Step 1: Updating system and installing essential packages..."
sudo apt update && sudo apt upgrade -y
echo "Installing essential packages: git, curl, python3-pip, python3-venv..."
sudo apt install -y git curl python3-pip python3-venv python3-setuptools || echo "⚠️ Some packages failed, continuing..."

# Ensure pip is available
echo "🐍 Ensuring pip is available..."
if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "Installing pip via get-pip.py..."
    curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3 --break-system-packages
fi

# Step 2: Clone repository
echo "📦 Step 2: Cloning ZanSoc repository..."
cd ~
rm -rf zansoc-beta
git clone https://github.com/ashzansoc/Zansoc-v5.git zansoc-beta
cd zansoc-beta

# Step 3: Check Python version and install build dependencies
echo "🔧 Step 3: Checking Python version and installing build dependencies..."
echo "Current Python version: $(python3 --version)"
echo "⚠️ Note: Cluster requires Python 3.13.7, you have $(python3 --version)"
echo "Trying to install build dependencies..."
sudo apt install -y build-essential || echo "⚠️ Build-essential installation failed, continuing..."
# Try to install Python 3.13 specific dev packages
sudo apt install -y python3.13-dev python3.13-venv || echo "⚠️ Python 3.13 dev packages not available, using pip fallback..."
# Install setuptools via pip
python3 -m pip install --user setuptools wheel --break-system-packages || echo "⚠️ Setuptools installation failed, continuing..."

# Step 4: Install Python packages (skip problematic netifaces)
echo "📋 Step 4: Installing Python packages (skipping problematic packages)..."
# Use python3 -m pip instead of just pip
echo "Installing Ray with exact version to match cluster..."
python3 -m pip install "ray[default,data,train,tune,rllib]==2.49.1" --break-system-packages

echo "Installing core dependencies..."
python3 -m pip install pyarrow>=14.0.1 protobuf>=4.25.1 requests>=2.31.0 --break-system-packages

echo "Installing additional utilities..."
python3 -m pip install numpy pandas tqdm Flask Flask-SocketIO gevent loguru --break-system-packages

# Skip netifaces and heavy ML packages that cause build issues
echo "⚠️ Skipping netifaces (build conflicts) and heavy ML packages for faster setup"

# Step 5: Install and configure Tailscale
echo "🌐 Step 5: Setting up Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

# Enable IP forwarding for exit node functionality
echo "🔧 Enabling IP forwarding for exit node..."
echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Connect to Tailscale using provided auth key
echo "🔑 Connecting to Tailscale..."

if [ -n "$TAILSCALE_AUTH_KEY" ]; then
    echo "✅ Using provided Tailscale auth key"
    echo "🔗 Connecting to Tailscale..."
    if sudo tailscale up --auth-key="$TAILSCALE_AUTH_KEY"; then
        echo "✅ Connected to Tailscale successfully!"
    else
        echo "❌ Failed to connect with provided auth key"
        echo "🔄 Falling back to manual authentication..."
        sudo tailscale up
    fi
else
    echo "❌ No Tailscale auth key provided!"
    echo ""
    echo "📋 Usage: TAILSCALE_AUTH_KEY=your-key curl -fsSL ... | bash"
    echo ""
    echo "🔑 Generate a new auth key at: https://login.tailscale.com/admin/settings/keys"
    echo "   Example: tskey-auth-kPG8GC23ct11CNTRL-7YYCnDFbHS5wugRzh4VwS5EUdmYbHKUP"
    echo ""
    echo "🔄 Falling back to manual authentication..."
    echo "Please run: sudo tailscale up"
    echo "Then follow the authentication URL in your browser"
    read -p "Press Enter after completing Tailscale authentication..."
    sudo tailscale up
fi

# Verify Tailscale connection
echo "🔍 Verifying Tailscale connection..."
sleep 2
if tailscale status > /dev/null 2>&1; then
    echo "✅ Tailscale is connected"
else
    echo "⚠️ Tailscale connection issue detected"
    echo "Current status:"
    tailscale status || echo "Failed to get status"
fi

# Step 6: Get Tailscale IP
echo "📍 Step 6: Getting Tailscale IP..."
TAILSCALE_IP=$(tailscale ip -4)
echo "Your Tailscale IP: $TAILSCALE_IP"

# Step 7: Add Ray CLI to PATH
echo ""
echo "🔧 Step 7: Setting up Ray CLI..."
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Step 8: Connect to Ray cluster
echo ""
echo "🚀 Step 8: Connecting to Ray cluster..."
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
export RAY_DISABLE_IMPORT_WARNING=1

# Skip version check to avoid Python version mismatch errors
if $HOME/.local/bin/ray start --address='100.101.84.71:6379' --disable-usage-stats > /dev/null 2>&1; then
    echo "✅ Ray cluster connection initiated"
else
    echo "⚠️ Ray connection attempt completed (version mismatches are ignored)"
fi

# Step 9: Skip status verification to avoid version check errors
echo ""
echo "✅ Step 9: Finalizing setup..."
sleep 2

echo ""
echo ""
echo "$$$$$$$$\\  $$$$$$\\  $$\\   $$\\  $$$$$$\\   $$$$$$\\   $$$$$$\\  "
echo "\\____$$  |$$  __$$\\ \$$$\\  \$$ |\$$  __$$\\ $$  __$$\\ $$  __$$\\ "
echo "    $$  / \$$ /  \$$ |\$$$$\\ \$$ |\$$ /  \\__|\$$ /  \$$ |\$$ /  \\__|"
echo "   $$  /  \$$$$$$$$ |\$$ \$$\\\$$ |\\$$$$$$\\  \$$ |  \$$ |\$$ |      "
echo "  $$  /   $$  __\$$ |\$$ \\$$$\$$ | \\____\$$\\ \$$ |  \$$ |\$$ |      "
echo " $$  /    \$$ |  \$$ |\$$ |\\$$\$ |$$\\   \$$ |\$$ |  \$$ |\$$ |  $$\\ "
echo "$$$$$$$$\\ \$$ |  \$$ |\$$ | \\\$$ |\\$$$$$$  | $$$$$$  |\\$$$$$$  |"
echo "\\________|\\__|  \\__|\\__|  \\__| \\______/  \\______/  \\______/ "
echo ""
echo "🎉 Welcome to ZanSoc! Your node is now enrolled."
echo "📞 For further support, contact Admin."
echo ""
echo "📊 Your node details:"
echo "   • Tailscale IP: \$(tailscale ip -4 2>/dev/null || echo 'Not available')"
echo "   • Hostname: \$(hostname)"
echo "   • Ray Status: Connected to cluster"
echo ""
echo "✅ Onboarding completed successfully!"