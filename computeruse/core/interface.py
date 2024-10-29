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
        self.client: Optional[Anthropic] = None
        self.screenshot_manager = ScreenshotManager(config, logger)
        self.action_handler = ActionHandler(config, logger)
        
        # Control flags
        self.is_processing = False
        self.should_stop = False
        self.task_complete = False
        
        # Task state
        self.current_task: Optional[str] = None
        self.current_iteration = 0
        self.max_iterations = config.get_setting('max_iterations', 20)  # Default to 20 if not set
        self.conversation_history: List[Dict] = []
        
        # Screen properties
        self.native_width = pyautogui.size()[0]
        self.native_height = pyautogui.size()[1]
        self.target_width = self.native_width
        self.target_height = self.native_height
        
        # Wait times and delays
        self.min_action_delay = config.get_setting('min_action_delay', 0.5)
        self.default_wait_time = config.get_setting('wait_time', 3.0)
        
        self.initialize_interface()
    
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
        """Send a message to Claude"""
        if not self.client:
            raise Exception("Anthropic client not initialized")
        
        return self.client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0,
            messages=messages,
            tools=[{
                "type": "computer_20241022",
                "name": "computer",
                "display_width_px": self.target_width,
                "display_height_px": self.target_height,
                "display_number": 1
            }],
            betas=["computer-use-2024-10-22"]
        )
    
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
    
    def process_response(self, response) -> None:
        try:
            if self.should_stop:
                self.logger.add_entry("System", "Task stopped by user")
                return
                
            if self.current_iteration >= self.max_iterations:
                self.logger.add_entry("System", 
                    f"Maximum iterations ({self.max_iterations}) reached.")
                self.task_complete = True
                return

            self.current_iteration += 1
            self.logger.add_entry("Debug", f"Iteration {self.current_iteration}/{self.max_iterations}")
            
            for content in response.content:
                if self.should_stop:
                    self.logger.add_entry("System", "Task stopped by user")
                    return
                    
                if hasattr(content, 'text'):
                    # Process text response
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": [{
                            "type": "text",
                            "text": content.text
                        }]
                    })
                    self.logger.add_entry("Claude", content.text)
                    
                    # Check for task completion indicators
                    text_lower = content.text.lower()
                    if any(phrase in text_lower for phrase in [
                        "task completed", "successfully completed", "finished the task",
                        "task is done", "completed successfully", "mission accomplished",
                        "we have completed", "i have completed", "task has been completed"
                    ]):
                        self.task_complete = True
                        self.logger.add_entry("System", "✓ Task completed successfully!")
                        return
                    
                elif hasattr(content, 'type') and content.type == 'tool_use':
                    # Extract tool input carefully
                    tool_input = {}
                    if hasattr(content, 'input') and isinstance(content.input, dict):
                        tool_input = content.input
                    
                    # Get action from tool input
                    action = tool_input.get('action', '')
                    if not action:
                        self.logger.add_entry("Warning", "No action specified in tool use, defaulting to screenshot")
                        action = 'screenshot'
                        tool_input = {}
                    
                    self.logger.add_entry("Tool", f"Executing: {action}")
                    
                    # Execute the action
                    result = self.action_handler.execute_action(action, tool_input)
                    
                    if result:
                        if result.get("type") == "error":
                            self.logger.add_entry("Error", 
                                f"Action failed: {result.get('error', 'Unknown error')}")
                            continue
                        
                        # Handle successful action
                        next_message = self.create_message_with_screenshot(
                            f"Your current task is: {self.current_task}\n"
                            f"Action completed: {action} with result: {json.dumps(result)}. "
                            f"Please verify if the task is completed. If not, continue with the necessary actions."
                        )
                        
                        self.conversation_history.append(next_message)
                        
                        try:
                            if not self.should_stop:
                                new_response = self.send_message([next_message])
                                self.process_response(new_response)
                                
                        except Exception as api_error:
                            if "safety reasons" in str(api_error):
                                if not self.should_stop:
                                    self.logger.add_entry("System", "Retrying without screenshot...")
                                    # Create message without screenshot
                                    text_message = {
                                        "role": "user",
                                        "content": [{
                                            "type": "text",
                                            "text": (
                                                f"Your current task is: {self.current_task}\n"
                                                f"Action completed: {action} with result: {json.dumps(result)}. "
                                                f"Please verify if the task is completed. "
                                                f"If not, continue with the necessary actions."
                                            )
                                        }]
                                    }
                                    retry_response = self.send_message([text_message])
                                    self.process_response(retry_response)
                            else:
                                raise api_error

        except Exception as e:
            self.logger.add_entry("Error", f"Error processing response: {str(e)}")
            self.task_complete = True

    def create_message_with_screenshot(self, text: str) -> dict:
        """Create a message with the current screenshot"""
        try:
            # Take a new screenshot
            screenshot_result = self.action_handler.execute_action('screenshot', {})
            if screenshot_result.get("type") == "error":
                raise Exception(f"Failed to take screenshot: {screenshot_result.get('error')}")
            
            # Get the screenshot data
            current_screenshot = self.action_handler.get_current_screenshot()
            if not current_screenshot:
                raise Exception("No screenshot available")
            
            # Create message with screenshot
            return {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text
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
            # Return text-only message as fallback
            return {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": text
                }]
            }