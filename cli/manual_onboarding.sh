#!/bin/bash
# Manual onboarding script that replicates your working steps exactly

set -e

echo "🚀 ZanSoc Manual Onboarding (ARM64 Optimized)"
echo "=============================================="

# Step 1: Clone repository
echo "📦 Step 1: Cloning ZanSoc repository..."
cd ~
rm -rf zansoc-beta
git clone https://github.com/ashzansoc/Zansoc-v5.git zansoc-beta
cd zansoc-beta

# Step 2: Install build dependencies (skip if dependency conflicts)
echo "🔧 Step 2: Installing build dependencies..."
sudo apt update
echo "Trying to install build dependencies..."
sudo apt install -y build-essential || echo "⚠️ Build-essential installation failed, continuing..."
# Try to install Python 3.13 specific dev packages
sudo apt install -y python3.13-dev python3.13-venv || echo "⚠️ Python 3.13 dev packages not available, using pip fallback..."
# Install setuptools via pip instead of apt
python3 -m pip install --user setuptools wheel --break-system-packages || echo "⚠️ Setuptools installation failed, continuing..."

# Step 3: Install Python packages (skip problematic netifaces)
echo "📋 Step 3: Installing Python packages (skipping problematic packages)..."
# Use python3 -m pip instead of just pip
echo "Installing Ray with full components..."
python3 -m pip install "ray[default,data,train,tune,rllib]>=2.45.0" --break-system-packages

echo "Installing core dependencies..."
python3 -m pip install pyarrow>=14.0.1 protobuf>=4.25.1 requests>=2.31.0 --break-system-packages

echo "Installing additional utilities..."
python3 -m pip install numpy pandas tqdm Flask Flask-SocketIO gevent loguru --break-system-packages

# Skip netifaces and heavy ML packages that cause build issues
echo "⚠️ Skipping netifaces (build conflicts) and heavy ML packages for faster setup"

# Step 5: Install and configure Tailscale
echo "🌐 Step 5: Setting up Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=tskey-auth-kd32Q6XdHS11CNTRL-X13DpHNm9ygqbdavCzngxgEJg91Rgie6

# Step 5: Get Tailscale IP
echo "📍 Step 5: Getting Tailscale IP..."
TAILSCALE_IP=$(tailscale ip -4)
echo "Your Tailscale IP: $TAILSCALE_IP"

# Step 6: Add Ray CLI to PATH
echo "🔧 Step 6: Setting up Ray CLI..."
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Step 7: Connect to Ray cluster
echo "🚀 Step 7: Connecting to Ray cluster..."
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
$HOME/.local/bin/ray start --address='100.101.84.71:6379' --redis-password='zansoc_secure_password_change_me'

# Step 8: Verify connection
echo "✅ Step 8: Verifying Ray connection..."
sleep 3
$HOME/.local/bin/ray status

echo ""
echo "🎉 Manual onboarding complete!"
echo "Your device should now be connected to the ZanSoc Ray cluster."
echo ""
echo "To check status later:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "  \$HOME/.local/bin/ray status"