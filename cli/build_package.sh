#!/bin/bash
# Build distribution package for ZanSoc CLI

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Building ZanSoc CLI Distribution Package${NC}"
echo

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf build/ dist/ *.egg-info/

# Build wheel package
echo -e "${YELLOW}Building wheel package...${NC}"
python -m build

# Create standalone executable with PyInstaller
echo -e "${YELLOW}Creating standalone executable...${NC}"
pip install pyinstaller

# Create PyInstaller spec
cat > zansoc.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['zansoc_cli/seamless_cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('zansoc_cli/config', 'zansoc_cli/config'),
        ('zansoc_cli/scripts', 'zansoc_cli/scripts'),
    ],
    hiddenimports=[
        'zansoc_cli.seamless_cli',
        'zansoc_cli.onboarding_orchestrator',
        'zansoc_cli.ray_manager',
        'zansoc_cli.tailscale_manager',
        'zansoc_cli.environment_manager',
        'zansoc_cli.platform_utils',
        'zansoc_cli.provider_manager',
        'zansoc_cli.database',
        'zansoc_cli.models',
        'zansoc_cli.config_manager',
        'zansoc_cli.utils.logger',
        'rich',
        'click',
        'requests',
        'yaml',
        'psutil',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='zansoc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
EOF

# Build executable
pyinstaller zansoc.spec --clean

# Create distribution directory
echo -e "${YELLOW}Creating distribution directory...${NC}"
mkdir -p dist/zansoc-cli-linux

# Copy files
cp dist/zansoc dist/zansoc-cli-linux/
cp install.sh dist/zansoc-cli-linux/
cp README.md dist/zansoc-cli-linux/
cp -r dist/zansoc_cli-*.whl dist/zansoc-cli-linux/ 2>/dev/null || true

# Create final installer script
cat > dist/zansoc-cli-linux/quick-install.sh << 'EOF'
#!/bin/bash
# ZanSoc Quick Installer

set -e

echo "🚀 ZanSoc Provider Quick Install"
echo "================================"
echo

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ Please don't run this script as root"
   exit 1
fi

# Check OS
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "❌ This installer is for Linux systems only"
    exit 1
fi

# Make executable
chmod +x zansoc
chmod +x install.sh

echo "Choose installation method:"
echo "1. Quick install (standalone executable)"
echo "2. Full install (with Python environment)"
echo

read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo "📦 Installing standalone executable..."
        
        # Create directory
        mkdir -p ~/.local/bin
        
        # Copy executable
        cp zansoc ~/.local/bin/
        
        echo "✅ Installation complete!"
        echo
        echo "To run ZanSoc:"
        echo "  ~/.local/bin/zansoc"
        echo
        echo "Or add ~/.local/bin to your PATH and run:"
        echo "  zansoc"
        ;;
    2)
        echo "🔧 Running full installation..."
        ./install.sh
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo
echo "🎉 Ready to join the ZanSoc network!"
echo "Run 'zansoc' to start provider onboarding."
EOF

chmod +x dist/zansoc-cli-linux/quick-install.sh

# Create archive
echo -e "${YELLOW}Creating distribution archive...${NC}"
cd dist
tar -czf zansoc-cli-linux.tar.gz zansoc-cli-linux/
cd ..

# Create checksums
echo -e "${YELLOW}Creating checksums...${NC}"
cd dist
sha256sum zansoc-cli-linux.tar.gz > zansoc-cli-linux.tar.gz.sha256
cd ..

echo
echo -e "${GREEN}✅ Distribution package created successfully!${NC}"
echo
echo "📦 Files created:"
echo "  • dist/zansoc-cli-linux.tar.gz (Distribution archive)"
echo "  • dist/zansoc-cli-linux.tar.gz.sha256 (Checksum)"
echo "  • dist/zansoc-cli-linux/ (Extracted files)"
echo
echo "🚀 For users to install:"
echo "  1. Download: zansoc-cli-linux.tar.gz"
echo "  2. Extract: tar -xzf zansoc-cli-linux.tar.gz"
echo "  3. Install: cd zansoc-cli-linux && ./quick-install.sh"
echo
echo "🌐 Or one-line install:"
echo "  curl -fsSL https://github.com/zansoc/releases/install.sh | bash"