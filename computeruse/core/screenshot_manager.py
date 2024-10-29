# computeruse/core/screenshot_manager.py
import pyautogui
from PIL import Image
import base64
from io import BytesIO
from typing import Dict, Tuple, Optional
import time

class ScreenshotManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.current_screenshot = None
        self.last_screenshot_time = 0
        self.min_screenshot_interval = 0.5
        
        # Get native resolution
        self.native_width, self.native_height = pyautogui.size()
        
    def take_screenshot(self) -> Dict:
        try:
            current_time = time.time()
            if current_time - self.last_screenshot_time < self.min_screenshot_interval:
                time.sleep(self.min_screenshot_interval - (current_time - self.last_screenshot_time))
            
            # Take full resolution screenshot
            screenshot = pyautogui.screenshot()
            
            # Only resize if downscale factor is not 1.0
            downscale_factor = self.config.get_setting('downscale_factor')
            if downscale_factor != 1.0:
                target_width = int(self.native_width * downscale_factor)
                target_height = int(self.native_height * downscale_factor)
                screenshot = screenshot.resize(
                    (target_width, target_height), 
                    Image.Resampling.LANCZOS
                )
            
            buffered = BytesIO()
            screenshot.save(
                buffered,
                format="JPEG",
                quality=self.config.get_setting('screenshot_quality'),
                optimize=True
            )
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            size_kb = len(buffered.getvalue()) / 1024
            resolution = f"{screenshot.width}x{screenshot.height}"
            
            self.current_screenshot = {
                "image_data": img_str,
                "size": size_kb,
                "resolution": resolution,
                "width": screenshot.width,
                "height": screenshot.height,
                "timestamp": time.time()
            }
            
            self.last_screenshot_time = time.time()
            self.logger.add_entry("System", 
                f"Screenshot captured (size: {size_kb:.2f}KB, resolution: {resolution})")
            
            return {
                "type": "screenshot_taken",
                "resolution": resolution,
                "size_kb": size_kb
            }
            
        except Exception as e:
            self.logger.add_entry("Error", f"Screenshot failed: {str(e)}")
            return {"type": "error", "error": str(e)}
    
    def get_current_screenshot(self) -> Optional[Dict]:
        return self.current_screenshot
    
    def get_dimensions(self) -> Tuple[int, int]:
        if self.current_screenshot:
            return (
                self.current_screenshot["width"],
                self.current_screenshot["height"]
            )
        return self.native_width, self.native_height