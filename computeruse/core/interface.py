# computeruse/core/interface.py
import time
import json
from anthropic import Anthropic
import pyautogui
from typing import Optional, Dict, List, Any
from .screenshot_manager import ScreenshotManager
from .action_handler import ActionHandler

class Interface:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.action_handler = ActionHandler(config, logger)
        self.client = None
        
        # Control flags
        self.is_processing = False
        self.should_stop = False
        self.task_complete = False
        
        # Task state
        self.current_task = None
        self.current_iteration = 0
        self.max_iterations = config.get_setting('max_iterations', 20)
        self.conversation_history = []
        
        # Screen properties
        self.native_width, self.native_height = pyautogui.size()
    
    def initialize_interface(self) -> None:
        """Initialize interface settings"""
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.5
        self.reset_state()
    
    def initialize_anthropic(self, api_key: str) -> bool:
        """Initialize the Anthropic client with the provided API key"""
        try:
            self.client = Anthropic(api_key=api_key)
            self.test_connection()
            self.logger.add_entry("System", "Anthropic client initialized successfully")
            return True
        except Exception as e:
            self.client = None
            error_msg = f"Failed to initialize Anthropic client: {str(e)}"
            self.logger.add_entry("Error", error_msg)
            raise Exception(error_msg)
    
    def test_connection(self) -> bool:
        """Test the connection to Anthropic API"""
        if not self.client:
            return False
            
        try:
            test_response = self.client.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": "test"
                    }]
                }],
                betas=["computer-use-2024-10-22"]
            )
            return True
        except Exception as e:
            self.client = None
            raise Exception(f"Failed to validate API key: {str(e)}")
    
    def create_message_with_screenshot(self, text: str) -> Dict:
        """Create a message with screenshot for Claude"""
        screenshot_result = self.screenshot_manager.take_screenshot()
        if screenshot_result.get("type") == "error":
            raise Exception(f"Failed to take screenshot: {screenshot_result.get('error')}")
            
        current_screenshot = self.screenshot_manager.get_current_screenshot()
        if not current_screenshot:
            raise Exception("No screenshot available")
            
        screen_info = (
            f"Working with resolution: {self.target_width}x{self.target_height}\n"
            f"Native screen resolution: {self.native_width}x{self.native_height}\n"
            f"Scale factor: {self.target_width/self.native_width:.2f}\n"
        )
            
        return {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"{text}\n{screen_info}"
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": current_screenshot["image_data"]
                    }
                }
            ]
        }
    
    def send_message(self, messages: List[Dict]) -> Any:
        """Send a message to Claude with the current screenshot"""
        if not self.client:
            raise Exception("Anthropic client not initialized")
        
        self.logger.add_entry("Debug", f"Sending message to Claude with {len(messages)} message(s)")
        
        # Log the content being sent (excluding image data for brevity)
        for msg in messages:
            content_preview = [
                c for c in msg["content"] 
                if c["type"] == "text"
            ]
            self.logger.add_entry("Debug", f"Message content: {json.dumps(content_preview)}")
        
        response = self.client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0,
            messages=messages,
            tools=[{
                "type": "computer_20241022",
                "name": "computer",
                "display_width_px": self.action_handler.native_width,
                "display_height_px": self.action_handler.native_height,
                "display_number": 1
            }],
            betas=["computer-use-2024-10-22"]
        )
        
        self.logger.add_entry("Debug", "Received response from Claude")
        return response
    
    def reset_state(self) -> None:
        """Reset all state variables"""
        self.conversation_history = []
        self.current_task = None
        self.is_processing = False
        self.should_stop = False
        self.task_complete = False
        self.current_iteration = 0
    
    def stop_processing(self) -> None:
        """Stop current processing"""
        self.should_stop = True
        self.task_complete = True
        self.is_processing = False
        self.logger.add_entry("System", "Processing stopped")
    
    def update_target_resolution(self, downscale_factor: float) -> None:
        """Update target resolution based on downscale factor"""
        self.target_width = int(self.native_width * downscale_factor)
        self.target_height = int(self.native_height * downscale_factor)
        
        self.logger.add_entry("System", 
            f"Resolution updated - Native: {self.native_width}x{self.native_height}, "
            f"Target: {self.target_width}x{self.target_height}, "
            f"Scale: {downscale_factor}")
    
    def update_resolution(self, downscale_factor: float) -> None:
        """Update resolution settings"""
        self.config.update_setting('downscale_factor', downscale_factor)
        target_width = int(self.native_width * downscale_factor)
        target_height = int(self.native_height * downscale_factor)
        self.logger.add_entry(
            "System", 
            f"Resolution updated - Native: {self.native_width}x{self.native_height}, "
            f"Target: {target_width}x{target_height}, "
            f"Scale: {downscale_factor}"
        )

    def process_response(self, response) -> None:
        try:
            if self.should_stop:
                self.logger.add_entry("System", "Task stopped by user")
                return
                
            if self.current_iteration >= self.max_iterations:
                self.logger.add_entry("System", f"Maximum iterations ({self.max_iterations}) reached.")
                self.task_complete = True
                return

            self.current_iteration += 1
            self.logger.add_entry("Debug", f"Iteration {self.current_iteration}/{self.max_iterations}")

            # Take initial screenshot
            screenshot_result = self.action_handler.execute_action('screenshot', {})
            if screenshot_result.get("type") == "error":
                raise Exception(f"Failed to take screenshot: {screenshot_result.get('error')}")

            # Get current screenshot data
            current_screenshot = self.action_handler.get_current_screenshot()
            if not current_screenshot or "image_data" not in current_screenshot:
                raise Exception("Failed to get screenshot data")

            # Log the message we're about to send to Claude
            self.logger.add_entry("Debug", "Sending message to Claude with screenshot...")

            # First, collect any tool use actions from Claude's response
            actions_to_perform = []
            for content in response.content:
                if hasattr(content, 'type') and content.type == 'tool_use':
                    tool_input = getattr(content, 'input', {})
                    if isinstance(tool_input, dict):
                        action = tool_input.get('action', '')
                        if action and action != 'screenshot':
                            actions_to_perform.append((action, tool_input))
                            self.logger.add_entry("Debug", f"Queued action: {action}")

            # Perform the actions
            results = []
            for action, tool_input in actions_to_perform:
                self.logger.add_entry("Tool", f"Executing: {action}")
                result = self.action_handler.execute_action(action, tool_input)
                if result.get("type") != "error":
                    results.append(result)
                    time.sleep(self.config.get_setting('wait_time', 1.0))

            # Take a new screenshot if actions were performed
            if results:
                screenshot_result = self.action_handler.execute_action('screenshot', {})
                current_screenshot = self.action_handler.get_current_screenshot()

            # Construct message for Claude
            message_text = (
                f"Task: {self.current_task}\n"
                f"Current screen resolution: {current_screenshot['resolution']}\n"
            )

            if results:
                message_text += f"Actions just performed: {json.dumps(results)}\n"
            
            message_text += "Please provide the next specific actions needed (use tool calls for clicking, typing, etc.)."

            next_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message_text
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": current_screenshot["image_data"]
                        }
                    }
                ]
            }

            self.logger.add_entry("Debug", f"Sending message to Claude:\n{message_text}")
            
            # Send to Claude and continue
            if not self.should_stop:
                new_response = self.send_message([next_message])
                self.logger.add_entry("Debug", "Received response from Claude")
                self.process_response(new_response)

        except Exception as e:
            self.logger.add_entry("Error", f"Error processing response: {str(e)}")
            self.task_complete = True


    def create_message_with_screenshot(self, text: str) -> dict:
        """Create a message with the current screenshot and resolution info"""
        try:
            # Take a new screenshot
            screenshot_result = self.action_handler.execute_action('screenshot', {})
            if screenshot_result.get("type") == "error":
                raise Exception(f"Failed to take screenshot: {screenshot_result.get('error')}")
            
            # Get the screenshot data
            current_screenshot = self.action_handler.get_current_screenshot()
            if not current_screenshot:
                raise Exception("No screenshot available")
            
            # Get current resolution info
            target_width, target_height = self.action_handler.get_target_resolution()
            resolution_info = (
                f"Current resolution: {target_width}x{target_height}\n"
                f"Native resolution: {self.native_width}x{self.native_height}\n"
                f"Scale factor: {self.config.get_setting('downscale_factor', 1.0):.1f}"
            )
            
            # Create message with screenshot and resolution info
            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{text}\n{resolution_info}"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": current_screenshot["image_data"]
                        }
                    }
                ]
            }
            
        except Exception as e:
            self.logger.add_entry("Error", f"Error creating message with screenshot: {str(e)}")
            return {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": text
                }]
            }