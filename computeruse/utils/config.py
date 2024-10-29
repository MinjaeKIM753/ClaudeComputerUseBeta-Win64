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
            'downscale_factor': 0.5,
            'min_action_delay': 0.5,
            'max_iterations': 20,
            'wait_time': 3.0,
            'screenshot_quality': 60,
            'teleport_mouse': False,
            'show_screenshots': False
        }
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting with an optional default value"""
        return self.settings.get(key, default)
    
    def update_setting(self, key: str, value: Any) -> None:
        """Update a setting"""
        self.settings[key] = value
    
    def get_api_key(self) -> str:
        """Get the API key from environment"""
        return os.getenv('ANTHROPIC_API_KEY', '')