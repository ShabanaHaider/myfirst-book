"""
Environment configuration loader.
"""
import os
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path
import yaml
from src.config.settings import settings


class ConfigLoader:
    """
    A configuration loader that can read from multiple sources including environment variables,
    configuration files, and default values.
    """

    def __init__(self):
        """Initialize the configuration loader."""
        self.config_data = {}
        self._load_from_settings()

    def _load_from_settings(self):
        """Load configuration from the main settings module."""
        # Get all attributes from the settings object that don't start with underscore
        for attr_name in dir(settings):
            if not attr_name.startswith('_'):
                attr_value = getattr(settings, attr_name)
                if not callable(attr_value):  # Skip methods
                    self.config_data[attr_name] = attr_value

    def load_from_file(self, config_path: str) -> bool:
        """
        Load configuration from a file (JSON or YAML).

        Args:
            config_path: Path to the configuration file

        Returns:
            True if successful, False otherwise
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                return False

            with open(config_path, 'r', encoding='utf-8') as file:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(file)
                elif config_path.suffix.lower() == '.json':
                    config = json.load(file)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")

            if config:
                self.config_data.update(config)
                return True
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
            return False

        return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: The configuration key
            default: Default value if key is not found

        Returns:
            The configuration value or default
        """
        return self.config_data.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get a configuration value as integer.

        Args:
            key: The configuration key
            default: Default value if key is not found

        Returns:
            The configuration value as integer or default
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a configuration value as float.

        Args:
            key: The configuration key
            default: Default value if key is not found

        Returns:
            The configuration value as float or default
        """
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a configuration value as boolean.

        Args:
            key: The configuration key
            default: Default value if key is not found

        Returns:
            The configuration value as boolean or default
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def get_list(self, key: str, default: list = None) -> list:
        """
        Get a configuration value as list.

        Args:
            key: The configuration key
            default: Default value if key is not found

        Returns:
            The configuration value as list or default
        """
        if default is None:
            default = []
        value = self.get(key, default)
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Assume comma-separated values
            return [item.strip() for item in value.split(',') if item.strip()]
        return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: The configuration key
            value: The value to set
        """
        self.config_data[key] = value

    def reload(self) -> None:
        """Reload configuration from all sources."""
        self.config_data = {}
        self._load_from_settings()

    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as a dictionary.

        Returns:
            Dictionary containing all configuration
        """
        return self.config_data.copy()

    def validate_required(self, required_keys: list) -> Dict[str, bool]:
        """
        Validate that required configuration keys are present and not empty.

        Args:
            required_keys: List of required configuration keys

        Returns:
            Dictionary with validation results for each key
        """
        results = {}
        for key in required_keys:
            value = self.get(key)
            results[key] = value is not None and value != ""
        return results

    def get_nested(self, key_path: str, separator: str = '.', default: Any = None) -> Any:
        """
        Get a nested configuration value using dot notation.

        Args:
            key_path: Path to the nested key using separator (e.g., 'database.host')
            separator: Separator for nested keys (default: '.')
            default: Default value if path is not found

        Returns:
            The nested configuration value or default
        """
        keys = key_path.split(separator)
        value = self.config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from a dictionary.

        Args:
            config_dict: Dictionary with configuration values to update
        """
        self.config_data.update(config_dict)

    def get_config_subset(self, prefix: str) -> Dict[str, Any]:
        """
        Get a subset of configuration with keys starting with a prefix.

        Args:
            prefix: Prefix to filter configuration keys

        Returns:
            Dictionary with filtered configuration
        """
        subset = {}
        for key, value in self.config_data.items():
            if key.startswith(prefix):
                # Remove prefix from the key in the result
                new_key = key[len(prefix):].lstrip('_')
                if new_key:  # Only add if there's something left after prefix removal
                    subset[new_key] = value
        return subset


# Global configuration loader instance
config_loader = ConfigLoader()


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value from the global loader.

    Args:
        key: The configuration key
        default: Default value if key is not found

    Returns:
        The configuration value or default
    """
    return config_loader.get(key, default)


def get_global_config() -> Dict[str, Any]:
    """
    Get all configuration from the global loader.

    Returns:
        Dictionary containing all configuration
    """
    return config_loader.to_dict()


def load_config_from_file(config_path: str) -> bool:
    """
    Load configuration from file using the global loader.

    Args:
        config_path: Path to the configuration file

    Returns:
        True if successful, False otherwise
    """
    return config_loader.load_from_file(config_path)