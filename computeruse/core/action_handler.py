# computeruse/core/action_handler.py
import pyautogui
from typing import Dict, Any, Optional
import time
from PIL import Image
from io import BytesIO
import base64

class ActionHandler:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        # Get current scale from config
        self.current_scale = float(config.get_setting('downscale_factor'))
        
        # Store initial screen properties
        self.native_width, self.native_height = pyautogui.size()
        self.target_width = int(self.native_width * self.current_scale)
        self.target_height = int(self.native_height * self.current_scale)
        
        # Log initial state
        self.logger.add_entry("Debug",
            f"ActionHandler initialized with scale: {self.current_scale:.1f}\n"
            f"Target resolution: {self.target_width}x{self.target_height}"
        )
        
        # Mouse state
        self.last_mouse_pos = None
        self.is_dragging = False
        
        # Action timing
        self.last_action_time = time.time()
        self.min_action_delay = config.get_setting('min_action_delay', 0.5)

    def update_resolution_settings(self) -> None:
        """Update internal resolution settings from config"""
        downscale = float(self.config.get_setting('downscale_factor', 1.0))
        native_width, native_height = pyautogui.size()
        
        self.target_width = int(native_width * downscale)
        self.target_height = int(native_height * downscale)
        
        self.logger.add_entry("Debug",
            f"Resolution settings updated:\n"
            f"Downscale factor: {downscale}\n"
            f"Native resolution: {native_width}x{native_height}\n"
            f"Target resolution: {self.target_width}x{self.target_height}\n"
            f"Scale factors: ({1.0/downscale:.2f}, {1.0/downscale:.2f})"
        )

    def execute_action(self, action: str, tool_input: dict) -> dict:
        """Execute the specified action with given parameters"""
        try:
            # Ensure minimum delay between actions
            elapsed = time.time() - self.last_action_time
            if elapsed < self.min_action_delay:
                time.sleep(self.min_action_delay - elapsed)

            # Map of available actions
            action_map = {
                'screenshot': self._handle_screenshot,
                'mouse_move': self._handle_mouse_move,
                'left_click': self._handle_left_click,
                'right_click': self._handle_right_click,
                'double_click': self._handle_double_click,
                'drag': self._handle_drag,
                'type': self._handle_type,
                'key_press': self._handle_key_press,
                'mouse_scroll': self._handle_mouse_scroll,
                'wait': self._handle_wait
            }

            # Validate action
            if action not in action_map:
                error_msg = f"Unknown action: {action}"
                self.logger.add_entry("Error", error_msg)
                return {"type": "error", "error": error_msg}

            # Execute action (only once)
            result = action_map[action](tool_input)
            
            # Update last action time
            self.last_action_time = time.time()
            return result
            
        except Exception as e:
            error_msg = f"Action execution error: {str(e)}"
            self.logger.add_entry("Error", error_msg)
            return {"type": "error", "error": error_msg}

    def _handle_screenshot(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Get current scale
            self.current_scale = float(self.config.get_setting('downscale_factor'))
            
            # Take screenshot at native resolution
            screenshot = pyautogui.screenshot()
            original_width, original_height = screenshot.size
            
            # ALWAYS resize for Claude according to scale
            # (e.g., 2560x1440 -> 1280x720 when scale is 0.5)
            target_width = int(original_width * self.current_scale)
            target_height = int(original_height * self.current_scale)

            screenshot = screenshot.resize(
                (target_width, target_height),
                Image.Resampling.LANCZOS
            )
            
            # Save with quality settings
            buffered = BytesIO()
            screenshot.save(
                buffered,
                format="JPEG",
                quality=self.config.get_setting('screenshot_quality', 90),
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
                f"Screenshot for Claude: {target_width}x{target_height} "
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

    def _handle_mouse_move(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            coordinates = tool_input.get('coordinate', [0, 0])
            current_x, current_y = pyautogui.position()
            # Get scale from config
            scale = float(self.config.get_setting('downscale_factor'))
            
            # Calculate scaled coordinates based on scale factor
            # Claude always provides coordinates for scaled resolution
            target_x = float(coordinates[0]) * (1.0 / scale)  # Scale up
            target_y = float(coordinates[1]) * (1.0 / scale)  # Scale up
            
            self.logger.add_entry("Debug", 
                f"Mouse move: Claude({coordinates[0]}, {coordinates[1]}) -> "
                f"Native({target_x:.0f}, {target_y:.0f}) "
                f"[scale: {scale:.1f}, upscale: {1.0/scale:.1f}x]"
            )

            # Validate bounds
            target_x = max(0, min(target_x, self.native_width - 1))
            target_y = max(0, min(target_y, self.native_height - 1))
            
            # Move mouse
            duration = 0 if self.config.get_setting('teleport_mouse', False) else 0.5
            pyautogui.moveTo(target_x, target_y, duration=duration)
            self.last_mouse_pos = (target_x, target_y)
            
            return {
                "type": "mouse_moved",
                "from": [current_x, current_y],
                "to": [target_x, target_y],
                "claude_coords": coordinates,
                "scale": scale,
                "upscale": 1.0/scale
            }
            
        except Exception as e:
            self.logger.add_entry("Error", f"Mouse move failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_left_click(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Get current mouse position
            current_x, current_y = pyautogui.position()
            
            # Click at current position
            pyautogui.click(current_x, current_y)
            self.logger.add_entry("System", f"Clicked at ({current_x}, {current_y})")
            
            return {
                "type": "click",
                "position": [current_x, current_y]
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Click failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_right_click(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.last_mouse_pos:
                return {"type": "error", "message": "No previous mouse position"}
            
            pyautogui.rightClick(self.last_mouse_pos[0], self.last_mouse_pos[1])
            self.logger.add_entry("System", f"Right clicked at {self.last_mouse_pos}")
            
            return {
                "type": "right_click",
                "position": self.last_mouse_pos
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Right click failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_double_click(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.last_mouse_pos:
                return {"type": "error", "message": "No previous mouse position"}
            
            pyautogui.doubleClick(self.last_mouse_pos[0], self.last_mouse_pos[1])
            self.logger.add_entry("System", f"Double clicked at {self.last_mouse_pos}")
            
            return {
                "type": "double_click",
                "position": self.last_mouse_pos
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Double click failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_drag(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.is_dragging:
                if not self.last_mouse_pos:
                    return {"type": "error", "message": "No mouse position for drag start"}
                
                self.drag_start_pos = self.last_mouse_pos
                pyautogui.mouseDown(self.drag_start_pos[0], self.drag_start_pos[1])
                self.is_dragging = True
                
                return {
                    "type": "drag_start",
                    "position": self.drag_start_pos
                }
            else:
                if not self.last_mouse_pos:
                    return {"type": "error", "message": "No mouse position for drag end"}
                
                pyautogui.mouseUp(self.last_mouse_pos[0], self.last_mouse_pos[1])
                self.is_dragging = False
                
                result = {
                    "type": "drag_end",
                    "from": self.drag_start_pos,
                    "to": self.last_mouse_pos
                }
                self.drag_start_pos = None
                return result
                
        except Exception as e:
            self.logger.add_entry("Error", f"Drag operation failed: {str(e)}")
            if self.is_dragging:
                try:
                    pyautogui.mouseUp()
                    self.is_dragging = False
                except:
                    pass
            return {"type": "error", "error": str(e)}

    def _handle_type(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text = tool_input.get('text', '')
            # Change keyboard layout to English before typing
            if any(ord(c) < 128 for c in text):  # Check if text contains English characters
                pyautogui.hotkey('alt', 'shift')  # Toggle to English keyboard
                time.sleep(0.2)  # Wait for keyboard switch
            
            pyautogui.write(text, interval=0.1)
            
            # Reset keyboard layout if needed
            if any(ord(c) < 128 for c in text):
                pyautogui.hotkey('alt', 'shift')  # Toggle back to original keyboard
                time.sleep(0.2)
            self.logger.add_entry("System", f"Typed: {text}")
            
            return {
                "type": "type",
                "text": text
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Type failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_key_press(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            key = tool_input.get('text', '')
            pyautogui.press(key)
            self.logger.add_entry("System", f"Pressed key: {key}")
            
            return {
                "type": "key",
                "key": key
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Key press failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_mouse_scroll(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            amount = int(tool_input.get('amount', 0))
            pyautogui.scroll(amount)
            self.logger.add_entry("System", f"Scrolled {amount} units")
            
            return {
                "type": "scroll",
                "amount": amount
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Scroll failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_wait(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            duration = float(tool_input.get('duration', 1.0))
            self.logger.add_entry("System", f"Waiting for {duration} seconds")
            time.sleep(duration)
            
            return {
                "type": "wait",
                "duration": duration
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Wait failed: {str(e)}")
            return {"type": "error", "error": str(e)}