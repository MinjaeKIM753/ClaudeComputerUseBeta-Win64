# computeruse/gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
import threading
import json
import time
from PIL import Image, ImageTk
import base64
from io import BytesIO
from .components import (
    APIFrame, OptionsFrame, HistoryFrame, 
    InputFrame, PreviewFrame, StatusBar,
    CoordinateDebugFrame
)
from .styles import create_style
from ..core.interface import Interface
from ..utils.config import Config
from ..utils.logger import Logger

class ComputerInterface:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.setup_window()
        
        # Initialize core components
        self.config = Config()
        self.logger = Logger()
        self.interface = Interface(self.config, self.logger)
        
        # Create style
        self.style = create_style()
        
        # Debug mode
        self.debug_mode = tk.BooleanVar(value=False)
        
        # Create GUI
        self.create_gui()
        
    def setup_window(self) -> None:
        self.root.title("Claude Computer Use Interface")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate window size
        window_width = min(1400, screen_width - 100)  # Increased for debug panel
        window_height = min(900, screen_height - 100)
        
        # Set window size and position
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def create_gui(self) -> None:
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10", style="MainFrame.TFrame")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Left panel for controls
        left_panel = ttk.Frame(self.main_frame)
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Create frames
        self.api_frame = APIFrame(left_panel, self)
        self.api_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.options_frame = OptionsFrame(left_panel, self)
        self.options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Add coordinate debug frame
        self.coord_debug_frame = CoordinateDebugFrame(left_panel, self)
        self.coord_debug_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.history_frame = HistoryFrame(left_panel, self)
        self.history_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.input_frame = InputFrame(left_panel, self)
        self.input_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_bar = StatusBar(left_panel, self)
        self.status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E))
        
        # Right panel for preview
        self.preview_frame = PreviewFrame(self.main_frame, self)
        self.preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Configure weights
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(3, weight=1)  # History frame expands
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Initialize with welcome message
        self.logger.add_entry("System", "Welcome! Please initialize the client with your API key to begin.")
        
        # Start coordinate tracking if in debug mode
        self.update_coordinate_display()
    
    def update_coordinate_display(self) -> None:
        """Update coordinate display in debug frame"""
        if self.debug_mode.get():
            try:
                x, y = self.root.winfo_pointerxy()
                screen_x = x - self.root.winfo_rootx()
                screen_y = y - self.root.winfo_rooty()
                
                downscale = self.options_frame.downscale_var.get()
                scaled_x = int(screen_x * downscale)
                scaled_y = int(screen_y * downscale)
                
                self.coord_debug_frame.update_coordinates(
                    screen_x, screen_y,
                    scaled_x, scaled_y,
                    downscale
                )
            except Exception as e:
                self.logger.add_entry("Debug", f"Coordinate update error: {str(e)}")
        
        # Schedule next update
        self.root.after(100, self.update_coordinate_display)
    
    def save_and_initialize(self) -> None:
        api_key = self.api_frame.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter an API key")
            return
            
        try:
            self.interface.initialize_anthropic(api_key)
            self.config.update_setting('api_key', api_key)
            
            self.logger.add_entry("System", "API key saved and client initialized successfully")
            self.api_frame.status_label.config(text="✓ Client Initialized")
            self.input_frame.submit_btn.config(state='normal')
            self.status_bar.status_var.set("Ready")
            self.api_frame.init_btn.config(text="Reinitialize Client")
            
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize client: {str(e)}")
            self.logger.add_entry("Error", f"Client initialization failed: {str(e)}")
            self.api_frame.status_label.config(text="✗ Client Failed")
    
    def handle_submit(self) -> None:
        if not self.interface.client:
            messagebox.showerror("Error", "Please initialize the client first")
            return
            
        if self.interface.is_processing:
            messagebox.showwarning("Processing", "Please wait for the current request to complete.")
            return
        
        self.interface.is_processing = True
        self.input_frame.submit_btn.configure(state='disabled')
        self.input_frame.stop_btn.configure(state='normal')
        self.status_bar.status_var.set("Processing request...")
        
        threading.Thread(target=self.process_task, daemon=True).start()
    
    def process_task(self) -> None:
        """Process the submitted task"""
        try:
            prompt = self.input_frame.input_text.get(1.0, tk.END).strip()
            if not prompt:
                return
            
            # Reset interface state
            self.interface.reset_state()
            self.interface.current_task = prompt
            self.interface.is_processing = True
            
            # Update UI state
            self.status_bar.progress_var.set(0)
            
            # Update interface resolution
            self.interface.update_target_resolution(
                self.options_frame.downscale_var.get()
            )
            
            self.logger.add_entry("User", prompt)
            self.input_frame.clear_input()
            
            # Create and send initial message
            initial_message = self.interface.create_message_with_screenshot(
                f"Task to complete: {prompt}\n"
                f"Please proceed with the necessary actions to complete this task."
            )
            
            self.interface.conversation_history.append(initial_message)
            response = self.interface.send_message([initial_message])
            self.interface.process_response(response)
            
        except Exception as e:
            self.logger.add_entry("Error", f"Error: {str(e)}")
        
        finally:
            self.interface.is_processing = False
            self.root.after(0, self.reset_submit_button)
            
    def process_response(self, response) -> None:
        try:
            if self.should_stop:
                self.logger.add_entry("System", "Task stopped by user")
                return
                
            if self.current_iteration >= self.config.get_setting('max_iterations'):
                self.logger.add_entry("System", 
                    f"Maximum iterations ({self.config.get_setting('max_iterations')}) reached.")
                self.task_complete = True
                return

            self.current_iteration += 1
            
            # Track goal indicators
            goal_indicators = [
                "completed", "finished", "done", "accomplished",
                "success", "achieved", "ready", "set up"
            ]
            
            task_progress = []
            
            for content in response.content:
                if self.should_stop:
                    self.logger.add_entry("System", "Task stopped by user")
                    return
                    
                if hasattr(content, 'text'):
                    text = content.text.lower()
                    if any(indicator in text for indicator in goal_indicators):
                        task_progress.append({
                            'timestamp': time.time(),
                            'indicators': [i for i in goal_indicators if i in text],
                            'text': text
                        })
                    
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": [{
                            "type": "text",
                            "text": content.text
                        }]
                    })
                    self.logger.add_entry("Claude", content.text)
                    
                elif hasattr(content, 'type') and content.type == 'tool_use':
                    try:
                        # Extract action information
                        tool_input = content.input if hasattr(content, 'input') else {}
                        
                        if not isinstance(tool_input, dict):
                            tool_input = {}
                        
                        action = tool_input.get('action', '')
                        
                        if not action:
                            self.logger.add_entry("Error", "No action specified in tool use request")
                            continue
                        
                        self.logger.add_entry("Tool", f"Executing: {action}")
                        
                        # Execute the action
                        result = self.action_handler.execute_action(action, tool_input)
                        
                        wait_time = self.config.get_setting('wait_time')
                        time.sleep(wait_time)
                        
                        if result:
                            if result.get("type") == "error":
                                self.logger.add_entry("Error", f"Action failed: {result.get('error', 'Unknown error')}")
                            else:
                                # Create next message with current state
                                next_message = self.create_message_with_screenshot(
                                    f"Your current task is: {self.current_task}\n"
                                    f"Action completed: {action} with result: {json.dumps(result)}. "
                                    f"Please verify if the task is completed. If not, continue with the necessary actions."
                                )
                                
                                self.conversation_history.append(next_message)
                                
                                # Send next message if not stopped
                                if not self.should_stop:
                                    new_response = self.send_message(
                                        self.conversation_history
                                    )
                                    self.process_response(new_response)
                        
                    except Exception as action_error:
                        self.logger.add_entry("Error", f"Action execution failed: {str(action_error)}")
                        return

            # Check for task completion
            if len(task_progress) >= 2:
                time_diff = task_progress[-1]['timestamp'] - task_progress[0]['timestamp']
                if time_diff > 5.0:
                    common_indicators = set.intersection(
                        *[set(p['indicators']) for p in task_progress]
                    )
                    if common_indicators:
                        self.task_complete = True
                        self.logger.add_entry("System", 
                            f"Task completion detected with indicators: {', '.join(common_indicators)}")
                        return

        except Exception as e:
            self.logger.add_entry("Error", f"Error processing response: {str(e)}")
            self.task_complete = True
    
    def process_action_result(self, result: dict) -> None:
        """Process the result of an action"""
        try:
            if result.get("type") == "screenshot_taken":
                screenshot_data = self.interface.screenshot_manager.get_current_screenshot()
                if screenshot_data and self.options_frame.show_screenshots_var.get():
                    self.root.after(0, lambda: self.preview_frame.update_preview(
                        screenshot_data["image_data"]
                    ))
            
            # Create next message with current state
            next_message = self.interface.create_message_with_screenshot(
                f"Your current task is: {self.interface.current_task}\n"
                f"Action completed: {json.dumps(result)}. "
                f"Please verify if the task is completed. If not, continue with the necessary actions."
            )
            
            self.interface.conversation_history.append(next_message)
            
            # Send next message if not stopped
            if not self.interface.should_stop:
                new_response = self.interface.send_message(
                    self.interface.conversation_history
                )
                self.process_response(new_response)
                
        except Exception as api_error:
            if "safety reasons" in str(api_error):
                if not self.interface.should_stop:
                    self.logger.add_entry("System", "Retrying without screenshot...")
                    # Remove screenshot content from messages
                    filtered_messages = [
                        {
                            "role": msg["role"],
                            "content": [
                                content for content in msg["content"]
                                if content["type"] == "text"
                            ]
                        }
                        for msg in self.interface.conversation_history
                    ]
                    retry_response = self.interface.send_message(filtered_messages)
                    self.process_response(retry_response)
            else:
                raise api_error
    

    def stop_processing(self) -> None:
        """Stop current task processing"""
        if self.interface.is_processing:
            self.interface.stop_processing()
            self.reset_submit_button()
    
    def reset_submit_button(self) -> None:
        self.input_frame.submit_btn.configure(state='normal')
        self.input_frame.stop_btn.configure(state='disabled')
        self.status_bar.status_var.set("Ready")
    
    def update_target_resolution(self, *args) -> None:
        self.options_frame.snap_to_nearest_tenth(None)
        self.config.update_setting('downscale_factor', self.options_frame.downscale_var.get())
        
        if self.interface.screenshot_manager.current_screenshot:
            self.preview_frame.update_preview(
                self.interface.screenshot_manager.current_screenshot["image_data"]
            )
    
    def update_screenshot_preview(self) -> None:
        if (self.interface.screenshot_manager.current_screenshot and 
                self.options_frame.show_screenshots_var.get()):
            self.preview_frame.update_preview(
                self.interface.screenshot_manager.current_screenshot["image_data"]
            )