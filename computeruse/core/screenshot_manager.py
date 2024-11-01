# computeruse/core/screenshot_manager.py
import pyautogui
from PIL import Image
import base64
from io import BytesIO
from typing import Dict, Tuple, Optional
import time

# computeruse/core/screenshot_manager.py
class ScreenshotManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        # Get current scale from config
        self.current_scale = float(config.get_setting('downscale_factor'))
        
        # Initialize state
        self.current_screenshot = None
        self.last_screenshot_time = 0
        self.min_screenshot_interval = 0.5
        
        # Screen properties
        self.native_width, self.native_height = pyautogui.size()
        self.target_width = int(self.native_width * self.current_scale)
        self.target_height = int(self.native_height * self.current_scale)
        
        # Log initial state
        self.logger.add_entry("Debug",
            f"ScreenshotManager initialized with scale: {self.current_scale:.1f}\n"
            f"Target resolution: {self.target_width}x{self.target_height}"
        )
    

    def take_screenshot(self) -> Dict:
        try:
            # Double-check current scale
            self.current_scale = float(self.config.get_setting('downscale_factor'))
            
            # Take screenshot at native resolution
            screenshot = pyautogui.screenshot()
            
            # Calculate target dimensions
            target_width = int(self.native_width * self.current_scale)
            target_height = int(self.native_height * self.current_scale)
            
            # Resize to target resolution
            screenshot = screenshot.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS
            )
            
            # Save with quality settings
            buffered = BytesIO()
            screenshot.save(
                buffered,
                format="JPEG",
                quality=self.config.get_setting('screenshot_quality', 60),
                optimize=True
            )
            
            img_str = base64.b64encode(buffered.getvalue()).decode()
            size_kb = len(buffered.getvalue()) / 1024
            
            self.current_screenshot = {
                "image_data": img_str,
                "size": size_kb,
                "resolution": f"{target_width}x{target_height}",
                "scale_factor": self.current_scale,
                "timestamp": time.time()
            }
            
            self.logger.add_entry("System", 
                f"Screenshot: {target_width}x{target_height} "
                f"[scale: {self.current_scale:.1f}, size: {size_kb:.1f}KB]"
            )
            
            return {
                "type": "screenshot_taken",
                "resolution": f"{target_width}x{target_height}",
                "scale_factor": self.current_scale
            }
            
        except Exception as e:
            self.logger.add_entry("Error", f"Screenshot failed: {str(e)}")
            return {"type": "error", "error": str(e)}
    
    def get_current_screenshot(self) -> Optional[Dict]:
        return self.current_screenshot