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

# Step 3: Install requirements
echo "📋 Step 3: Installing requirements.txt..."
pip install --no-cache-dir -r requirements.txt --break-system-packages

# Step 4: Install Ray with full components
echo "⚡ Step 4: Installing Ray with full components..."
pip install "ray[default,data,train,tune,rllib]" --break-system-packages

# Step 5: Install and configure Tailscale
echo "🌐 Step 5: Setting up Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=tskey-auth-kd32Q6XdHS11CNTRL-X13DpHNm9ygqbdavCzngxgEJg91Rgie6

# Step 6: Get Tailscale IP
echo "📍 Step 6: Getting Tailscale IP..."
TAILSCALE_IP=$(tailscale ip -4)
echo "Your Tailscale IP: $TAILSCALE_IP"

# Step 7: Add Ray CLI to PATH
echo "🔧 Step 7: Setting up Ray CLI..."
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Step 8: Connect to Ray cluster
echo "🚀 Step 8: Connecting to Ray cluster..."
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
ray start --address='100.101.84.71:6379' --redis-password='zansoc_secure_password_change_me'

# Step 9: Verify connection
echo "✅ Step 9: Verifying Ray connection..."
sleep 3
ray status

echo ""
echo "🎉 Manual onboarding complete!"
echo "Your device should now be connected to the ZanSoc Ray cluster."
echo ""
echo "To check status later:"
echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "  ray status"