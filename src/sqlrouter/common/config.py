"""Configuration loading utilities."""
import yaml
from pathlib import Path


def load_config(config_name: str = "qlora") -> dict:
    """Load a YAML configuration file.
    
    Args:
        config_name: Name of config file (without .yaml extension)
        
    Returns:
        Dictionary of configuration values
    """
    config_path = Path(__file__).parent.parent.parent.parent / "configs" / f"{config_name}.yaml"
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_costs() -> dict:
    """Load cost configuration.
    
    Returns:
        Dictionary with gpu_usd_per_hour and api pricing
    """
    return load_config("costs")
