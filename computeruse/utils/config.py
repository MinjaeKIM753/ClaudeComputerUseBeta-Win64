# computeruse/utils/config.py
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ConfigDefaults:
    DOWNSCALE_FACTOR: float = 0.5
    MIN_ACTION_DELAY: float = 0.5
    MAX_ITERATIONS: int = 20
    DEFAULT_WAIT_TIME: float = 3.0
    SCREENSHOT_QUALITY: int = 60
    MOUSE_MOVE_DURATION: float = 0.5

class Config:
    def __init__(self):
        self.settings = {
            'downscale_factor': 1.0,  # Default to native resolution
            'min_action_delay': 0.5,
            'max_iterations': 20,
            'wait_time': 3.0,
            'screenshot_quality': 60,
            'teleport_mouse': False,
            'show_screenshots': False
        }
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
    
    def update_setting(self, key: str, value: Any) -> None:
        """Update setting and validate specific values"""
        if key == 'downscale_factor':
            # Ensure downscale is exactly what we set
            value = float(value)
            if value > 1.0:
                value = 1.0
            elif value < 0.1:
                value = 0.1
        self.settings[key] = value
    
    def get_api_key(self) -> str:
        """Get the API key from environment"""
        return os.getenv('ANTHROPIC_API_KEY', '')