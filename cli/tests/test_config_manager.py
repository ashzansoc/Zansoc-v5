"""Tests for ConfigManager class."""

import pytest
import tempfile
import os
from pathlib import Path

from zansoc_cli.config_manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_default_config_loading(self):
        """Test that default configuration is loaded correctly."""
        config = ConfigManager()
        
        assert config.get("cluster.master_address") == "100.101.84.71:6379"
        assert config.get("auth.username") == "admin"
        assert config.get("auth.password") == "admin"
        assert config.get("environment.python_version") == "3.13.7"
    
    def test_get_with_default(self):
        """Test getting configuration values with defaults."""
        config = ConfigManager()
        
        # Existing key
        assert config.get("auth.username") == "admin"
        
        # Non-existing key with default
        assert config.get("nonexistent.key", "default_value") == "default_value"
        
        # Non-existing key without default
        assert config.get("nonexistent.key") is None
    
    def test_set_configuration(self):
        """Test setting configuration values."""
        config = ConfigManager()
        
        config.set("test.key", "test_value")
        assert config.get("test.key") == "test_value"
        
        config.set("nested.deep.key", "deep_value")
        assert config.get("nested.deep.key") == "deep_value"
    
    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        # Set environment variable
        os.environ["ZANSOC_CLUSTER_ADDRESS"] = "test.address:1234"
        
        try:
            config = ConfigManager()
            assert config.get("cluster.master_address") == "test.address:1234"
        finally:
            # Clean up
            del os.environ["ZANSOC_CLUSTER_ADDRESS"]
    
    def test_config_file_loading(self):
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
cluster:
  master_address: "custom.address:5678"
auth:
  username: "custom_user"
            """)
            config_path = f.name
        
        try:
            config = ConfigManager(config_path=config_path)
            assert config.get("cluster.master_address") == "custom.address:5678"
            assert config.get("auth.username") == "custom_user"
            # Default values should still be present
            assert config.get("auth.password") == "admin"
        finally:
            os.unlink(config_path)
    
    def test_data_directory_creation(self):
        """Test data directory creation."""
        config = ConfigManager()
        data_dir = config.get_data_dir()
        
        assert isinstance(data_dir, Path)
        assert data_dir.exists()
        assert data_dir.is_dir()
    
    def test_validation(self):
        """Test configuration validation."""
        config = ConfigManager()
        assert config.validate() is True
        
        # Test with missing required key
        config.set("cluster.master_address", "")
        assert config.validate() is False