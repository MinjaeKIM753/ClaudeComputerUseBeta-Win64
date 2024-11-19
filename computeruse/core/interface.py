# computeruse/core/interface.py
import time
import json
import platform as pf
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
        self.screenshot_manager = ScreenshotManager(config, logger)
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
        
        # Action timing
        self.default_wait_time = config.get_setting('wait_time', 3.0)
        
       # Screen properties
        self.native_width, self.native_height = pyautogui.size()
        self.target_width = self.native_width
        self.target_height = self.native_height
        self.current_scale_x = 1.0
        self.current_scale_y = 1.0
        
        self.action_sequence = []

        # Initialize with default scale
        self.update_scaling_factors()

    def create_system_prompt(self) -> str: # FOR FUTURE USE
        """
        Create a system prompt to structure Claude's responses
        """
        os_name = pf.system()
        if os_name == "Windows":
            os_version = pf.win32_ver()[0]
            platform_name = f"{os_name} {os_version}"
        elif os_name == "Darwin":
            os_version = pf.mac_ver()[0]
            platform_name = f"MacOS {os_version}"
        else:
            os_version = pf.freedesktop_os_release()["VERSION_ID"]
            platform_name = f"{os_name} {os_version}"
        
        return f"""With the provided current latest screenshot on the {platform_name} platform, please provide responses in the following format only.
Requirement:
- No unnecessary explanations or words other than the actions and parameters below.
- If you observe from the current latest screenshot that the task is **completed**, you must respond with the following:
   [completed] : indicator for the completion of the task. Presence of this will terminate immediately.
- If the task is **not completed**, List actions needed based on the latest screenshot in order using numbers. You must stop at where you are not certain of the situation (for example, absence of software). unfinished task will be continued in next request.:
   1. Action description
   <Indicate purpose of the action above here, in 1 sentence>
   2. Next action
   <Indicate purpose of the action above here, in 1 sentence>
   3. ...
- If there are actions that require "waiting for ~ result", you should skip those actions and any subsequent actions. These should be evaluated in the next conversation with an updated screenshot to properly verify the results.

Here are the action formats for you to reference if the task is **not completed**:
Specify exact action type in [brackets] at start of each line, '< >' indicates the parameter required.:
   [move]<X-Coord,Y-Coord> : coordinates for mouse movement. Please be very sensitive and exact to the coordinate and resolution. Beware of the mouse coordinate located at intended and correct location.
   [click] : for single left-clicking at current mouse coordinate. **Beware of the mouse coordinate located at intended and correct location**.
   [double_click] : for double left-clicking at current mouse coordinate. Beware of the mouse coordinate located at intended and correct location.
   [right_click] : for right-clicking at current mouse coordinate. Beware of the mouse coordinate located at intended and correct location.
   [mouse_scroll]<amount> : for mouse scrolling at current mouse coordinate, specify with unit amount of scroll. 
   [screenshot] : for taking screenshot of the current window. The latest screenshot before actions is already given to you.
   [type]"<text>" : for typing text.
   [key_press]<key> :  for keyboard shortcuts and special keys. This includes return key and special keys for corresponding operating system.
   [drag]<X-Coord,Y-Coord> : for drag operations, specify with destination coordinate
   [wait]<time> : for stopping operation, specify with number of seconds to wait.

Reminder: 
**Your Utmost important part is to accurately provide coordinates for the actions that requires it.**
You should adequately place [wait]<time> in between actions to wait for the actions to complete. For example: 
    - After [click] to open up a software or webpage, you may need some seconds to wait for it to open successfully.
You should be screenshot-resolution sensitive for [move] and [drag]. Please check screenshot resolution every time. 
To click on target, you must [move] to the coordinate and then [click].
   """

    def get_wait_time(self) -> float:
        """Get the current wait time between actions"""
        return self.config.get_setting('wait_time', self.default_wait_time)
    
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
            self.client.beta.messages.create(
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
        try:
            screenshot_result = self.screenshot_manager.take_screenshot()
            if screenshot_result.get("type") == "error":
                raise Exception(f"Failed to take screenshot: {screenshot_result.get('error')}")
                
            current_screenshot = self.screenshot_manager.get_current_screenshot()
            if not current_screenshot:
                raise Exception("No screenshot available")
                
            # Get current scale factor and dimensions
            downscale = float(self.config.get_setting('downscale_factor'))
            target_width = int(self.native_width * downscale)
            target_height = int(self.native_height * downscale)
                
            screen_info = (
                f"Working with resolution: {target_width}x{target_height}\n"
                f"Native screen resolution: {self.native_width}x{self.native_height}\n"
                f"Scale factor: {downscale:.2f}\n"
            )
            
            self.logger.add_entry("Debug", 
                f"Creating message with resolution info:\n{screen_info}"
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
        except Exception as e:
            self.logger.add_entry("Error", f"Error creating message with screenshot: {str(e)}")
            return {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": text
                }]
            }
    
    def send_message(self, messages: List[Dict]) -> Any:
        """Send a message to Claude with the scaled screenshot"""
        if not self.client:
            raise Exception("Anthropic client not initialized")
        
        # Calculate Claude's resolution based on scale
        scale = float(self.config.get_setting('downscale_factor'))
        target_width = int(self.native_width * scale)
        target_height = int(self.native_height * scale)
        
        self.logger.add_entry("Debug", 
            f"Sending to Claude with resolution: {target_width}x{target_height} "
            f"(scaled from {self.native_width}x{self.native_height} "
            f"by {scale:.1f})"
        )
        
        response = self.client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            temperature=0,
            messages=messages,
            tools=[{
                "type": "computer_20241022",
                "name": "computer",
                "display_width_px": target_width,  # Send scaled dimensions to Claude
                "display_height_px": target_height,
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
    
    def update_scaling_factors(self) -> None:
        """Update coordinate scaling factors based on current resolution"""
        downscale = self.config.get_setting('downscale_factor', 1.0)
        self.current_scale_x = self.native_width / (self.native_width * downscale) if downscale != 0 else 1.0
        self.current_scale_y = self.native_height / (self.native_height * downscale) if downscale != 0 else 1.0
        
        self.logger.add_entry("Debug", 
            f"Updated scaling factors:\n"
            f"Downscale: {downscale}\n"
            f"Scale X: {self.current_scale_x:.2f}\n"
            f"Scale Y: {self.current_scale_y:.2f}"
        )
    
    def update_target_resolution(self, downscale_factor: float) -> None:
        """Update target resolution and scaling factors"""
        self.target_width = int(self.native_width * downscale_factor)
        self.target_height = int(self.native_height * downscale_factor)
        
        # Update scaling factors
        self.update_scaling_factors()
        
        self.logger.add_entry("System", 
            f"Resolution updated:\n"
            f"Native: {self.native_width}x{self.native_height}\n"
            f"Target: {self.target_width}x{self.target_height}\n"
            f"Scale: {downscale_factor}"
        )
    
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

    def process_response(self, response):
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
            
            task_progress = []
            pending_actions = []

            # First pass: Analyze text responses and build action context
            for content in response.content:
                if hasattr(content, 'text'):
                    text = content.text.lower()
                    
                    # Update conversation history (do this only once)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": [{"type": "text", "text": content.text}]
                    })
                    self.logger.add_entry("Claude", content.text)

                    print(text)

                    if '[completed]' in text:
                        self.logger.add_entry("System", f"Claude terminated conversation due to task completion.")
                        self.task_complete = True
                    
                    # Identifying the Tasks in order
                    line_number = 1
                    for line in text.split('\n'):
                        if str(line_number) + '.' in line:
                            line = line.replace(str(line_number) + '.', '').strip()
                        else:
                            continue; # Wrong Format (Does not start with Number. ~)
                        
                        if '[screenshot]' in line:
                            pending_actions.append(('screenshot', {}))
                        elif '[move]' in line:
                            coordinates = line.replace('[move]', '').strip().replace('<', '').replace('>', '')
                            x, y = map(float, coordinates.split(','))
                            pending_actions.append(('mouse_move', {'coordinate': [x, y]}))
                        elif '[click]' in line:
                            pending_actions.append(('left_click', {}))
                        elif '[double_click]' in line:
                            pending_actions.append(('double_click', {}))
                        elif '[right_click]' in line:
                            pending_actions.append(('right_click', {}))
                        elif '[mouse_scroll]' in line:
                            scroll_amount = line.replace('[mouse_scroll]', '').strip().replace('<', '').replace('>', '')
                            pending_actions.append(('mouse_scroll', {'amount': scroll_amount}))
                        elif '[type]' in line:
                            text_to_type = line.replace('[type]', '').strip().replace('"', '')
                            pending_actions.append(('type', {'text': text_to_type}))
                        elif '[key_press]' in line:
                            key_to_press = line.replace('[key_press]', '').strip().replace('<', '').replace('>', '')
                            pending_actions.append(('key_press', {'text': key_to_press}))
                        elif '[drag]' in line:
                            drag_coordinates = line.replace('[drag]', '').strip().replace('<', '').replace('>', '')
                            x, y = map(float, drag_coordinates.split(','))
                            pending_actions.append(('drag', {'coordinate': [x, y]}))
                        elif '[wait]' in line:
                            wait_time = line.replace('[wait]', '').strip().replace('<', '').replace('>', '')
                            pending_actions.append(('wait', {'duration': wait_time}))
                        line_number += 1
                    
                    
                    # Process the tasks
                    result = None
                    if pending_actions:
                        wait_time = self.get_wait_time()
                        combined_results = []

                        for pending_action, pending_input in pending_actions:
                            if self.should_stop:
                                break
                            next_result = self.execute_tool_action(pending_action, pending_input)
                            if next_result and next_result.get("type") != "error":
                                combined_results.append(next_result)
                        
                        result = {
                            "type": "combined_action",
                            "actions": combined_results
                        }
                        pending_actions.clear()
                    
                    # Take a new screenshot after actions if there were no screenshots taken
                    if pending_actions and pending_actions[-1][0] != 'screenshot':
                        time.sleep(self.get_wait_time())
                        self.execute_tool_action('screenshot', {})

                    if not self.should_stop:
                        # Prepare next message with current state
                        next_message = {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Your current task is: {self.current_task}\n"
                                        f"Your previous response is: {text}"
                                        f"Your previous action result is: {json.dumps(result)}. "
                                        "Please verify if the task is completed. If not, continue with the necessary actions. The screenshot is the latest environment."
                                    )
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": self.screenshot_manager.get_current_screenshot()["image_data"]
                                    }
                                }
                            ]
                        }
                        # Continue conversation
                        try:
                            new_response = self.client.beta.messages.create(
                                model="claude-3-5-sonnet-20241022",
                                max_tokens=512,
                                temperature=0,
                                messages=self.conversation_history + [next_message],
                                tools=[{
                                    "type": "computer_20241022",
                                    "name": "computer",
                                    "display_width_px": self.target_width,
                                    "display_height_px": self.target_height,
                                    "display_number": 1
                                }],
                                betas=["computer-use-2024-10-22"]
                            )
                            self.process_response(new_response) #LOOP
                            
                        except Exception as api_error:
                            if "safety reasons" in str(api_error):
                                if not self.should_stop:
                                    self.logger.add_entry("System", "Retrying without screenshot...")
                                    # Remove screenshot content
                                    filtered_messages = [
                                        {
                                            "role": msg["role"],
                                            "content": [
                                                c for c in msg["content"]
                                                if c["type"] == "text"
                                            ]
                                        }
                                        for msg in self.conversation_history + [next_message]
                                    ]
                                    retry_response = self.client.beta.messages.create(
                                        model="claude-3-5-sonnet-20241022",
                                        max_tokens=1024,
                                        temperature=0,
                                        messages=filtered_messages,
                                        tools=[{
                                            "type": "computer_20241022",
                                            "name": "computer",
                                            "display_width_px": self.target_width,
                                            "display_height_px": self.target_height,
                                            "display_number": 1
                                        }],
                                        betas=["computer-use-2024-10-22"]
                                    )
                                    self.process_response(retry_response)
                            else:
                                raise api_error

        except Exception as e:
            self.logger.add_entry("Error", f"Error processing response: {str(e)}")
            self.task_complete = True

    def execute_tool_action(self, action: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool action using the action handler"""
        try:
            # Log the incoming action request
            self.logger.add_entry("Debug", f"Action request - Action: {action}, Input: {json.dumps(tool_input)}")
            
            # Execute the action using the handler
            result = self.action_handler.execute_action(action, tool_input)
            
            # Update conversation state based on action result
            if action == 'screenshot':
                # Get latest screenshot data after taking it
                current_screenshot = self.screenshot_manager.get_current_screenshot()
                if current_screenshot:
                    # Store the latest screenshot data
                    self.current_screenshot = current_screenshot
            
            # Log the result
            if result.get("type") == "error":
                self.logger.add_entry("Error", f"Action failed: {result.get('error', 'Unknown error')}")
            else:
                self.logger.add_entry("Debug", f"Action result: {json.dumps(result)}")
            
            return result
            
        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            self.logger.add_entry("Error", error_msg)
            return {"type": "error", "error": error_msg}