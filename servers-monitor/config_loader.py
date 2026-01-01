"""Configuration loader and validator for the server monitoring application."""
import json
import os
from typing import Dict, List, Any


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load and validate configuration from JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing validated configuration
        
    Raises:
        ConfigError: If configuration is invalid or file cannot be read
    """
    if not os.path.exists(config_path):
        raise ConfigError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise ConfigError(f"Error reading configuration file: {e}")
    
    # Validate required fields
    required_fields = ['servers', 'ssh_key_path', 'refresh_interval', 'port']
    for field in required_fields:
        if field not in config:
            raise ConfigError(f"Missing required configuration field: {field}")
    
    # Validate servers list
    if not isinstance(config['servers'], list) or len(config['servers']) == 0:
        raise ConfigError("'servers' must be a non-empty list")
    
    for i, server in enumerate(config['servers']):
        if not isinstance(server, dict):
            raise ConfigError(f"Server at index {i} must be a dictionary")
        
        required_server_fields = ['name', 'host', 'user']
        for field in required_server_fields:
            if field not in server:
                raise ConfigError(f"Server at index {i} missing required field: {field}")
    
    # Validate SSH key path
    if not os.path.exists(config['ssh_key_path']):
        raise ConfigError(f"SSH key file not found: {config['ssh_key_path']}")
    
    # Validate refresh interval
    if not isinstance(config['refresh_interval'], int) or config['refresh_interval'] < 1:
        raise ConfigError("'refresh_interval' must be a positive integer")
    
    # Validate port
    if not isinstance(config['port'], int) or not (1 <= config['port'] <= 65535):
        raise ConfigError("'port' must be an integer between 1 and 65535")
    
    return config

