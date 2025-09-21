#!/bin/bash
# Manual onboarding script that replicates your working steps exactly

set -e

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

# Generate fresh auth key via Tailscale API
echo "🔑 Generating fresh Tailscale auth key..."
TAILSCALE_API_KEY="tskey-api-kUiNJcs8B411CNTRL-2MMcK5h1hxJcfJQ8CyHRyJL8yoKv5QCc"
TAILNET="ashzansoc@gmail.com"

# Create ephemeral auth key that expires in 1 hour
AUTH_KEY_RESPONSE=$(curl -s -X POST \
  "https://api.tailscale.com/api/v2/tailnet/${TAILNET}/keys" \
  -H "Authorization: Bearer ${TAILSCALE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "capabilities": {
      "devices": {
        "create": {
          "reusable": false,
          "ephemeral": true,
          "preauthorized": true,
          "tags": ["tag:zansoc-worker"]
        }
      }
    },
    "expirySeconds": 3600,
    "description": "ZanSoc worker - '$(hostname)' - '$(date)'"
  }')

# Extract the auth key from the response
EPHEMERAL_AUTH_KEY=$(echo "$AUTH_KEY_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['key'])" 2>/dev/null)

if [ -z "$EPHEMERAL_AUTH_KEY" ]; then
    echo "❌ Failed to generate ephemeral auth key. Response:"
    echo "$AUTH_KEY_RESPONSE"
    echo ""
    echo "🔄 Falling back to manual authentication..."
    echo "Please run: sudo tailscale up"
    echo "Then follow the authentication URL in your browser"
    read -p "Press Enter after completing Tailscale authentication..."
else
    echo "✅ Generated fresh auth key successfully!"
    echo "🔗 Connecting to Tailscale with ephemeral key..."
    sudo tailscale up --auth-key="$EPHEMERAL_AUTH_KEY"
    echo "✅ Connected to Tailscale successfully!"
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
$HOME/.local/bin/ray start --address='100.101.84.71:6379'

# Step 9: Verify connection
echo "✅ Step 9: Verifying Ray connection..."
sleep 3
$HOME/.local/bin/ray status

echo ""
echo "🎉 Manual onboarding complete!"
echo "Your device should now be connected to the ZanSoc Ray cluster."
echo ""
echo "To check status later:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "  \$HOME/.local/bin/ray status"