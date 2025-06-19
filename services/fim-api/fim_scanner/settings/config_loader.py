"""
Configuration Loader for FIM System
Handles loading and parsing of YAML configuration files
"""

import yaml
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Configuration loader and manager for FIM system"""
    
    def __init__(self):
        """Initialize the config loader"""
        self.config = None
        self.config_path = None
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load YAML configuration file
        
        Args:
            config_path: Path to configuration file. Uses default if None.
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if config_path is None:
            config_path = "/app/config/config.yaml"
        
        self.config_path = config_path
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with config_file.open('r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"Configuration loaded successfully: {config_path}")
            
            # Validate basic structure
            self._validate_config()
            
            return self.config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Configuration loading error: {e}")
            raise
    
    def _validate_config(self):
        """Validate the loaded configuration structure"""
        if not self.config:
            raise ValueError("Configuration is empty")
        
        # Check for required sections
        fim_config = self.config.get('fim')
        if not fim_config:
            logger.warning("No 'fim' section found in configuration")
            return
        
        # Extract paths to monitor from the configuration
        self._extract_monitoring_paths()
    
    def _extract_monitoring_paths(self):
        """Extract and set paths to monitor from configuration"""
        try:
            paths_to_monitor = []
            
            # Get monitoring configuration
            monitoring = self.config.get('fim', {}).get('monitoring', {})
            
            # Add base paths
            base_paths = monitoring.get('paths', [])
            if isinstance(base_paths, list):
                paths_to_monitor.extend(base_paths)
            elif isinstance(base_paths, str):
                paths_to_monitor.append(base_paths)
            
            # Add additional paths from profiles if available
            active_profile = self.get_active_profile()
            if active_profile:
                platform = self._get_platform_key()
                profile_paths = self.get_profile_monitoring_paths(active_profile, platform)
                paths_to_monitor.extend(profile_paths)
            
            # If no paths specified, use default
            if not paths_to_monitor:
                paths_to_monitor = ["/app/test_monitoring"]
                logger.info("No monitoring paths specified, using default: /app/test_monitoring")
            
            # Store in config for easy access
            if 'paths_to_monitor' not in self.config:
                self.config['paths_to_monitor'] = paths_to_monitor
            
            logger.info(f"Monitoring paths configured: {paths_to_monitor}")
            
        except Exception as e:
            logger.error(f"Failed to extract monitoring paths: {e}")
            # Set default path as fallback
            self.config['paths_to_monitor'] = ["/app/test_monitoring"]
    
    def _get_platform_key(self) -> str:
        """Get platform key for current operating system"""
        if sys.platform.startswith('linux'):
            return "linux"
        elif sys.platform == 'win32':
            return "windows"
        elif sys.platform == 'darwin':
            return "macos"
        else:
            return "linux"  # Default to linux
    
    def get_active_profile(self) -> Optional[str]:
        """
        Get active profile name
        
        Returns:
            Active profile name or None
        """
        if not self.config:
            return None
        
        try:
            return self.config.get('fim', {}).get('active_profile')
        except Exception as e:
            logger.error(f"Failed to get active profile: {e}")
            return None
    
    def get_profile_rules(self, profile_name: str, platform: str) -> List[Dict[str, Any]]:
        """
        Get rules for specific profile and platform
        
        Args:
            profile_name: Profile name
            platform: Platform name (linux, windows, etc.)
            
        Returns:
            List of rules
        """
        if not self.config:
            return []
        
        try:
            profiles = self.config.get('fim', {}).get('profiles', {})
            profile = profiles.get(profile_name, {})
            platform_config = profile.get('platforms', {}).get(platform, {})
            return platform_config.get('rules', [])
        except Exception as e:
            logger.error(f"Failed to get profile rules: {e}")
            return []
    
    def get_profile_monitoring_paths(self, profile_name: str, platform: str) -> List[str]:
        """
        Get monitoring paths from profile rules
        
        Args:
            profile_name: Profile name
            platform: Platform name
            
        Returns:
            List of paths to monitor
        """
        rules = self.get_profile_rules(profile_name, platform)
        paths = []
        
        for rule in rules:
            path = rule.get('path')
            if path:
                paths.append(path)
        
        return paths
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """
        Get monitoring configuration
        
        Returns:
            Monitoring configuration dictionary
        """
        if not self.config:
            return {}
        
        return self.config.get('fim', {}).get('monitoring', {})
    
    def get_paths_to_monitor(self) -> List[str]:
        """
        Get list of paths to monitor
        
        Returns:
            List of paths to monitor
        """
        if not self.config:
            return ["/app/test_monitoring"]
        
        return self.config.get('paths_to_monitor', ["/app/test_monitoring"])
    
    def get_excluded_patterns(self) -> List[str]:
        """
        Get list of excluded file patterns
        
        Returns:
            List of patterns to exclude from monitoring
        """
        if not self.config:
            return []
        
        monitoring_config = self.get_monitoring_config()
        return monitoring_config.get('excluded_patterns', [])
    
    def get_scanning_config(self) -> Dict[str, Any]:
        """
        Get scanning configuration
        
        Returns:
            Scanning configuration dictionary
        """
        if not self.config:
            return {}
        
        return self.config.get('fim', {}).get('scanning', {})


# Legacy functions for backward compatibility
def load_config(config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Legacy function to load configuration
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary or None if failed
    """
    try:
        loader = ConfigLoader()
        return loader.load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None

def get_active_profile(config: Dict[str, Any]) -> Optional[str]:
    """
    Legacy function to get active profile
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Active profile name or None
    """
    try:
        return config.get('fim', {}).get('active_profile')
    except Exception as e:
        logger.error(f"Failed to get active profile: {e}")
        return None

def get_profile_rules(config: Dict[str, Any], profile_name: str, platform: str) -> list:
    """
    Legacy function to get profile rules
    
    Args:
        config: Configuration dictionary
        profile_name: Profile name
        platform: Platform name
        
    Returns:
        List of rules
    """
    try:
        profiles = config.get('fim', {}).get('profiles', {})
        profile = profiles.get(profile_name, {})
        platform_config = profile.get('platforms', {}).get(platform, {})
        return platform_config.get('rules', [])
    except Exception as e:
        logger.error(f"Failed to get profile rules: {e}")
        return []
