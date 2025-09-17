# 🚀 ZanSoc Provider CLI

**One-click provider onboarding for the ZanSoc distributed compute network**

Join the ZanSoc network and start earning rewards by contributing your compute resources to distributed AI and machine learning workloads.

## ⚡ Quick Start (Ubuntu/Linux)

### Option 1: One-Line Install (Recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/zansoc/zansoc-beta/main/cli/install.sh | bash
```

### Option 2: Manual Download and Install
```bash
wget https://raw.githubusercontent.com/zansoc/zansoc-beta/main/cli/install.sh
chmod +x install.sh
./install.sh
```

### Option 3: Git Clone and Install
```bash
git clone https://github.com/zansoc/zansoc-beta.git
cd zansoc-beta/cli
./install.sh
```

## 🎯 What It Does

The ZanSoc Provider CLI automatically:

1. **📝 Registers** your device as a provider
2. **🔧 Installs** miniconda and Python 3.13.7 environment
3. **📦 Clones** ZanSoc repository and installs dependencies
4. **🌐 Configures** Tailscale VPN for secure networking
5. **⚡ Connects** to Ray distributed compute cluster
6. **✅ Verifies** all connections and completes setup

**Total setup time: 5-10 minutes**

## 🖥️ System Requirements

- **OS**: Ubuntu 18.04+ (other Linux distributions may work)
- **RAM**: 2GB minimum, 4GB+ recommended
- **Storage**: 5GB free space
- **Network**: Stable internet connection
- **Privileges**: Sudo access for system installations
- **Python**: 3.9+ (will be installed if missing)

## 🚀 Usage

After installation, start the onboarding process:

```bash
# If ~/.local/bin is in your PATH
zansoc

# Or use the full path
~/.zansoc/zansoc
```

### Default Credentials (Demo)
- **Username**: `admin`
- **Password**: `admin`

## 📋 What Happens During Onboarding

### Step 1: Provider Registration
- Creates unique provider ID
- Registers in ZanSoc database
- Initializes onboarding session

### Step 2: Environment Setup
- Downloads and installs miniconda
- Creates `zansoc` conda environment with Python 3.13.7
- Clones ZanSoc repository
- Installs Python dependencies
- Installs Ray distributed computing framework

### Step 3: Network Configuration
- Installs Tailscale VPN client
- Authenticates with ZanSoc network
- Establishes secure connection
- Obtains Tailscale IP address

### Step 4: Cluster Connection
- Connects to Ray cluster at `100.101.84.71:6379`
- Registers as worker node
- Verifies cluster connectivity
- Enables cross-platform compatibility

### Step 5: System Verification
- Verifies Ray node registration
- Tests Tailscale connectivity
- Confirms cluster reachability
- Validates connection health

### Step 6: Completion
- Updates provider status to ACTIVE
- Displays success confirmation
- Shows provider details and next steps

## 🎮 Advanced Usage

### Manual CLI (Full Interface)
```bash
# Access full CLI with menus
python -m zansoc_cli.main

# With options
python -m zansoc_cli.main --verbose    # Verbose logging
python -m zansoc_cli.main --debug      # Debug mode
python -m zansoc_cli.main --config custom.yml  # Custom config
```

### Component Demos
```bash
cd ~/.zansoc/zansoc-beta/cli

# Test individual components
python demo_platform.py      # Platform detection
python demo_environment.py   # Environment setup
python demo_tailscale.py     # Tailscale integration
python demo_ray.py          # Ray cluster connection
```

### Run Tests
```bash
cd ~/.zansoc/zansoc-beta/cli
python -m pytest tests/ -v
```

## 📁 File Locations

```
~/.zansoc/
├── zansoc                    # Main launcher script
├── venv/                     # Python virtual environment
├── zansoc-beta/             # Cloned repository
├── logs/                    # Application logs
├── data/                    # SQLite database
└── config/                  # Configuration files
```

## 🔧 Configuration

### Environment Variables
```bash
export ZANSOC_CONFIG_PATH=/path/to/config.yml
export ZANSOC_DATA_DIR=/path/to/data
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1  # For cross-platform
```

### Custom Configuration
Create `~/.zansoc/config/config.yml`:
```yaml
cluster:
  master_address: "100.101.84.71:6379"
  password: "your_cluster_password"

tailscale:
  auth_key: "your_tailscale_key"

database:
  path: "~/.zansoc/data/providers.db"

logging:
  level: "INFO"
  file: "~/.zansoc/logs/zansoc.log"
```

## 🐛 Troubleshooting

### Common Issues

**Installation fails with permission errors:**
```bash
# Ensure you have sudo privileges
sudo -v

# Or install to user directory only
pip install --user -e .
```

**Python version too old:**
```bash
# Install Python 3.9+ on Ubuntu
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-pip
```

**Network connectivity issues:**
```bash
# Test internet connection
curl -I https://github.com

# Check DNS resolution
nslookup github.com
```

**Ray cluster connection fails:**
- Verify Tailscale is connected: `tailscale status`
- Check cluster reachability: `telnet 100.101.84.71 6379`
- Review logs: `~/.zansoc/logs/zansoc.log`

### Getting Help

1. **Check Logs**: `~/.zansoc/logs/zansoc.log`
2. **Run Diagnostics**: `python demo_platform.py`
3. **Test Components**: Run individual demo scripts
4. **Contact Support**: Include your provider ID and error logs

## 🔄 Updating

To update to the latest version:
```bash
cd ~/.zansoc/zansoc-beta
git pull origin main
source ~/.zansoc/venv/bin/activate
pip install -e cli/
```

## 🗑️ Uninstalling

To completely remove ZanSoc:
```bash
# Stop services
~/.zansoc/zansoc --stop  # If implemented

# Remove installation
rm -rf ~/.zansoc

# Remove desktop entry
rm -f ~/.local/share/applications/zansoc.desktop

# Remove symlink
rm -f ~/.local/bin/zansoc
```

## 🏗️ Development

### Building from Source
```bash
git clone https://github.com/zansoc/zansoc-beta.git
cd zansoc-beta/cli

# Create development environment
python -m venv venv
source venv/bin/activate
pip install -e .

# Run tests
python -m pytest tests/ -v

# Run CLI
python -m zansoc_cli.seamless_cli
```

### Project Structure
```
cli/
├── zansoc_cli/              # Main package
│   ├── seamless_cli.py      # One-click interface
│   ├── onboarding_orchestrator.py  # Workflow engine
│   ├── ray_manager.py       # Ray cluster integration
│   ├── tailscale_manager.py # Tailscale VPN integration
│   ├── environment_manager.py  # Environment setup
│   ├── platform_utils.py    # Cross-platform utilities
│   └── utils/               # Utilities
├── tests/                   # Test suite
├── demo_*.py               # Component demos
├── install.sh              # Installation script
└── README.md               # This file
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

- **Documentation**: https://docs.zansoc.com
- **Issues**: https://github.com/zansoc/zansoc-beta/issues
- **Email**: support@zansoc.com
- **Discord**: https://discord.gg/zansoc

---

**🚀 Ready to join the ZanSoc network? Run the installer and start earning rewards!**