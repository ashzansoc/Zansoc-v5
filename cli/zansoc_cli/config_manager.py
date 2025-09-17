"""Configuration management for ZanSoc CLI."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration and settings."""
    
    DEFAULT_CONFIG = {
        "cluster": {
            "master_address": "100.101.84.71:6379",
            "password": "zansoc_secure_password_change_me",
        },
        "tailscale": {
            "auth_key": "tskey-auth-kd32Q6XdHS11CNTRL-X13DpHNm9ygqbdavCzngxgEJg91Rgie6",
        },
        "environment": {
            "python_version": "3.13.7",
            "repository_url": "https://github.com/zansoc/zansoc-beta.git",
        },
        "database": {
            "path": "data/providers.db",
        },
        "logging": {
            "level": "INFO",
            "file": "logs/onboarding.log",
        },
        "auth": {
            "username": "admin",
            "password": "admin",
            "max_attempts": 3,
        },
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Optional path to custom configuration file
        """
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> None:
        """Load configuration from file if provided."""
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        self._merge_config(self.config, file_config)
            except Exception as e:
                print(f"Warning: Failed to load config file {self.config_path}: {e}")
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        env_mappings = {
            "ZANSOC_CLUSTER_ADDRESS": ["cluster", "master_address"],
            "ZANSOC_CLUSTER_PASSWORD": ["cluster", "password"],
            "ZANSOC_TAILSCALE_KEY": ["tailscale", "auth_key"],
            "ZANSOC_PYTHON_VERSION": ["environment", "python_version"],
            "ZANSOC_REPO_URL": ["environment", "repository_url"],
            "ZANSOC_DB_PATH": ["database", "path"],
            "ZANSOC_LOG_LEVEL": ["logging", "level"],
            "ZANSOC_LOG_FILE": ["logging", "file"],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(self.config, config_path, value)
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _set_nested_value(self, config: Dict[str, Any], path: list, value: str) -> None:
        """Set a nested configuration value."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key.
        
        Args:
            key: Dot-separated configuration key (e.g., 'cluster.master_address')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        current = self.config
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-separated key.
        
        Args:
            key: Dot-separated configuration key
            value: Value to set
        """
        keys = key.split('.')
        current = self.config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_data_dir(self) -> Path:
        """Get data directory path, creating if necessary."""
        data_dir = Path(os.getenv("ZANSOC_DATA_DIR", "data"))
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    def get_log_dir(self) -> Path:
        """Get log directory path, creating if necessary."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        return log_dir
    
    def get_database_path(self) -> Path:
        """Get database file path."""
        db_path = self.get("database.path", "data/providers.db")
        return Path(db_path)
    
    def validate(self) -> bool:
        """Validate configuration completeness.
        
        Returns:
            True if configuration is valid
        """
        required_keys = [
            "cluster.master_address",
            "cluster.password",
            "tailscale.auth_key",
            "environment.python_version",
            "environment.repository_url",
        ]
        
        for key in required_keys:
            if not self.get(key):
                print(f"Error: Missing required configuration: {key}")
                return False
        
        return True