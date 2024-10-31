# computeruse/core/action_handler.py
import pyautogui
from typing import Dict, Any, Tuple, Optional
import time
import json
from PIL import Image
from io import BytesIO
import base64

class ActionHandler:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.last_mouse_pos: Optional[Tuple[float, float]] = None
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[float, float]] = None
        self.last_action_time = time.time()
        self.current_screenshot = None
        
        # Store native resolution
        self.native_width, self.native_height = pyautogui.size()
        
        # Validate initial scale factor
        downscale = self.config.get_setting('downscale_factor', 1.0)
        self.config.update_setting('downscale_factor', downscale)

    def execute_action(self, action: str, tool_input: dict) -> dict:
        """Execute the specified action with given parameters"""
        try:
            print("ACTION : ", action)
            # Log incoming action request
            self.logger.add_entry("Debug", f"Action request - Action: {action}, Input: {json.dumps(tool_input)}")
            
            # Ensure minimum delay between actions
            elapsed = time.time() - self.last_action_time
            min_delay = self.config.get_setting('min_action_delay')
            if elapsed < min_delay:
                time.sleep(min_delay - elapsed)

            # Map of available actions
            action_map = {
                'screenshot': self._handle_screenshot,
                'mouse_move': self._handle_mouse_move,
                'left_click': self._handle_left_click,
                'right_click': self._handle_right_click,
                'double_click': self._handle_double_click,
                'drag': self._handle_drag,
                'type': self._handle_type,
                'key': self._handle_key,
                'scroll': self._handle_scroll,
                'wait': self._handle_wait
            }

            # Validate action
            if action not in action_map:
                error_msg = f"Unknown action: {action}. Available actions: {', '.join(action_map.keys())}"
                self.logger.add_entry("Error", error_msg)
                return {"type": "error", "error": error_msg}

            # Execute action
            handler = action_map[action]
            result = handler(tool_input)
            
            # Update last action time
            self.last_action_time = time.time()
            
            # Log result
            self.logger.add_entry("Debug", f"Action result: {json.dumps(result)}")
            
            return result
        
        except Exception as e:
            error_msg = f"Action execution error: {str(e)}"
            self.logger.add_entry("Error", error_msg)
            return {"type": "error", "error": error_msg}

    def _handle_screenshot(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Force scale check
            downscale = self.config.get_setting('downscale_factor', 1.0)
            
            # Calculate target resolution
            target_width = int(self.native_width * downscale)
            target_height = int(self.native_height * downscale)
            
            self.logger.add_entry("Debug", 
                f"Taking screenshot with scale {downscale} "
                f"({self.native_width}x{self.native_height} -> {target_width}x{target_height})")

            # Take native resolution screenshot
            screenshot = pyautogui.screenshot()
            current_width, current_height = screenshot.size
            
            self.logger.add_entry("Debug", 
                f"Original screenshot size: {current_width}x{current_height}")
            
            # Resize only if necessary
            if downscale != 1.0:
                screenshot = screenshot.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )
                self.logger.add_entry("Debug", f"Resized to: {target_width}x{target_height}")

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
            
            final_width, final_height = screenshot.size
            self.current_screenshot = {
                "image_data": img_str,
                "size": size_kb,
                "resolution": f"{final_width}x{final_height}",
                "timestamp": time.time(),
                "scale_factor": downscale
            }
            
            result = {
                "type": "screenshot_taken",
                "size_kb": size_kb,
                "resolution": f"{final_width}x{final_height}",
                "scale_factor": downscale
            }
            
            self.logger.add_entry(
                "System",
                f"Screenshot captured (size: {size_kb:.2f}KB, "
                f"resolution: {final_width}x{final_height}, "
                f"scale: {downscale})"
            )
            
            return result
            
        except Exception as e:
            self.logger.add_entry("Error", f"Screenshot failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def get_target_resolution(self) -> Tuple[int, int]:
        """Get target resolution based on downscale factor"""
        downscale = self.config.get_setting('downscale_factor')
        if downscale == 1.0:  # Use native resolution
            return self.native_width, self.native_height
        return (
            int(self.native_width * downscale), 
            int(self.native_height * downscale)
        )

    def get_current_screenshot(self) -> Optional[Dict[str, Any]]:
        """Get the most recent screenshot data"""
        return self.current_screenshot

    def _handle_mouse_move(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            coordinates = tool_input.get('coordinate', [0, 0])
            current_x, current_y = pyautogui.position()
            
            # Get scale factors
            downscale = self.config.get_setting('downscale_factor')
            if downscale == 1.0:
                real_x = float(coordinates[0])
                real_y = float(coordinates[1])
            else:
                # Transform coordinates based on scale
                scale_x = pyautogui.size()[0] / (pyautogui.size()[0] * downscale)
                scale_y = pyautogui.size()[1] / (pyautogui.size()[1] * downscale)
                real_x = float(coordinates[0]) * scale_x
                real_y = float(coordinates[1]) * scale_y
            
            self.logger.add_entry("Debug", 
                f"Coordinate transformation: ({coordinates[0]}, {coordinates[1]}) -> "
                f"({real_x:.2f}, {real_y:.2f}), Scale: {downscale}")
            
            duration = 0 if self.config.get_setting('teleport_mouse') else 0.5
            pyautogui.moveTo(real_x, real_y, duration=duration)
            
            self.last_mouse_pos = (real_x, real_y)
            
            return {
                "type": "mouse_moved",
                "from": [current_x, current_y],
                "to": [real_x, real_y],
                "original": coordinates,
                "scale_factor": downscale
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Mouse move failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_left_click(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.last_mouse_pos:
                return {"type": "error", "message": "No previous mouse position"}
            
            pyautogui.click(self.last_mouse_pos[0], self.last_mouse_pos[1])
            self.logger.add_entry("System", f"Clicked at {self.last_mouse_pos}")
            
            return {
                "type": "click",
                "position": self.last_mouse_pos
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
            pyautogui.write(text, interval=0.1)
            self.logger.add_entry("System", f"Typed: {text}")
            
            return {
                "type": "type",
                "text": text
            }
        except Exception as e:
            self.logger.add_entry("Error", f"Type failed: {str(e)}")
            return {"type": "error", "error": str(e)}

    def _handle_key(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_scroll(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
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