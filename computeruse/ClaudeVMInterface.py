import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, PhotoImage
import json
from datetime import datetime
import os
import anthropic
from typing import Optional
import threading
import pyautogui
from PIL import Image, ImageTk
import base64
from io import BytesIO
import time

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.5

class ClaudeVMInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Claude Computer Use Interface - VM")
        
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()
        
        window_width = min(1200, self.screen_width - 100)
        window_height = min(800, self.screen_height - 100)
        self.root.geometry(f"{window_width}x{window_height}")
        
        self.client = None
        self.is_processing = False
        self.image_label = None

        self.should_stop = False
            
        self.max_iterations = 20
        self.current_iteration = 0
        self.task_complete = False
        self.current_task = None

        self.conversation_history = []
        self.current_screenshot = None
        self.last_mouse_pos = None
        
        self.target_width = int(self.screen_width / 1.5)
        self.target_height = int(self.screen_height / 1.5)

        self.scale_x = float(self.target_width) / float(self.screen_width)
        self.scale_y = float(self.target_height) / float(self.screen_height)
            
        self.create_gui()
        
        if os.getenv('ANTHROPIC_API_KEY'):
            self.initialize_anthropic(os.getenv('ANTHROPIC_API_KEY'))

    def create_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        right_panel = ttk.LabelFrame(main_frame, text="Screenshot Preview", padding="5")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        self.image_label = ttk.Label(right_panel)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        api_frame = ttk.LabelFrame(left_panel, text="API Configuration", padding="5")
        api_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(api_frame, text="API Key:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.api_key_var = tk.StringVar(value=os.getenv('ANTHROPIC_API_KEY', ''))
        self.api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50, show='*')
        self.api_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            api_frame,
            text="Show Key",
            variable=self.show_key_var,
            command=self.toggle_key_visibility
        ).pack(side=tk.LEFT)
        
        self.init_btn = ttk.Button(
            api_frame,
            text="Initialize Client",
            command=self.save_and_initialize
        )
        self.init_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(api_frame, text="⭕ Client Not Initialized")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        resolution_text = f"Screen: {self.screen_width}x{self.screen_height}"
        self.resolution_label = ttk.Label(api_frame, text=resolution_text)
        self.resolution_label.pack(side=tk.RIGHT, padx=5)
        
        options_frame = ttk.LabelFrame(left_panel, text="Options", padding="5")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.show_screenshots_var = tk.BooleanVar(value=False)
        self.show_screenshots_check = ttk.Checkbutton(
            options_frame,
            text="Show Screenshots in Conversation",
            variable=self.show_screenshots_var
        )
        self.show_screenshots_check.pack(side=tk.LEFT, padx=5)
        
        history_frame = ttk.LabelFrame(left_panel, text="Conversation History", padding="5")
        history_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.history_text = scrolledtext.ScrolledText(
            history_frame,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=('Courier', 10),
            bg='#1e1e1e',
            fg='#ffffff'
        )
        self.history_text.pack(fill=tk.BOTH, expand=True)
        
        input_frame = ttk.LabelFrame(left_panel, text="Input", padding="5")
        input_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            width=70,
            height=5,
            font=('Arial', 10)
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        button_frame = ttk.Frame(left_panel)
        button_frame.grid(row=4, column=0, sticky=tk.E)
        
        self.submit_btn = ttk.Button(
            button_frame,
            text="Submit",
            command=self.handle_submit,
            state='disabled'
        )
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            button_frame,
            text="Stop",
            command=self.stop_processing,
            state='disabled'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(
            button_frame,
            text="Clear Input",
            command=self.clear_input
        )
        clear_btn.pack(side=tk.LEFT)
        
        self.status_var = tk.StringVar(value="Please initialize the client with your API key")
        status_bar = ttk.Label(left_panel, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.add_to_history("System", "Welcome! Please initialize the client with your API key to begin.")

    def stop_processing(self):
        if self.is_processing:
            self.should_stop = True
            self.task_complete = True
            self.add_to_history("System", "Task stopping...")
            self.is_processing = False
            self.reset_submit_button()
        
    def save_and_initialize(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter an API key")
            return
            
        try:
            self.initialize_anthropic(api_key)
            os.environ['ANTHROPIC_API_KEY'] = api_key
            self.add_to_history("System", "API key saved and client initialized successfully")
            self.status_label.config(text="✓ Client Initialized")
            self.submit_btn.config(state='normal')
            self.status_var.set("Ready")
            self.init_btn.config(text="Reinitialize Client")
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize client: {str(e)}")
            self.add_to_history("Error", f"Client initialization failed: {str(e)}")
            self.status_label.config(text="✗ Client Failed")
    
    def initialize_anthropic(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
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
    
    def toggle_key_visibility(self):
        self.api_entry.config(show='' if self.show_key_var.get() else '*')
    
    def add_to_history(self, source, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {source}: {message}\n"
        
        self.history_text.configure(state='normal')
        self.history_text.insert(tk.END, formatted_message)
        self.history_text.see(tk.END)
        self.history_text.configure(state='disabled')
        self.root.update_idletasks()
    
    def clear_input(self):
        self.input_text.delete(1.0, tk.END)
    
    def handle_submit(self):
        if not self.client:
            messagebox.showerror("Error", "Please initialize the client first")
            return
            
        if self.is_processing:
            messagebox.showwarning("Processing", "Please wait for the current request to complete.")
            return
        
        self.is_processing = True
        self.submit_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.status_var.set("Processing request...")
        
        threading.Thread(target=self.submit_prompt, daemon=True).start()

    def reset_submit_button(self):
        self.submit_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.status_var.set("Ready")
    
    def submit_prompt(self):
        try:
            prompt = self.input_text.get(1.0, tk.END).strip()
            if not prompt:
                return
            
            self.current_iteration = 0
            self.task_complete = False
            self.current_task = prompt
            self.conversation_history = []
            self.should_stop = False
            
            self.add_to_history("User", prompt)
            self.clear_input()
            
            initial_screenshot = self.execute_tool_action('screenshot', {})
            
            initial_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Task to complete: {prompt} - Please proceed with the necessary actions to complete this task. Here is the current screen state:"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": self.current_screenshot["image_data"]
                        }
                    }
                ]
            }
            
            self.conversation_history.append(initial_message)
            
            response = self.client.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0,
                messages=[initial_message],
                tools=[{
                    "type": "computer_20241022",
                    "name": "computer",
                    "display_width_px": self.target_width,
                    "display_height_px": self.target_height,
                    "display_number": 1
                }],
                betas=["computer-use-2024-10-22"]
            )
            
            self.process_response(response)
            
        except Exception as e:
            self.add_to_history("Error", f"Error: {str(e)}")
        
        finally:
            self.is_processing = False
            self.root.after(0, self.reset_submit_button)
    
    def process_response(self, response):
        try:
            if self.should_stop:
                self.add_to_history("System", "Task stopped by user")
                return
                
            if self.current_iteration >= self.max_iterations:
                self.add_to_history("System", f"Maximum iterations ({self.max_iterations}) reached.")
                self.task_complete = True
                return

            self.current_iteration += 1
            self.add_to_history("Debug", f"Iteration {self.current_iteration}/{self.max_iterations}")

            task_completed = False
            for content in response.content:
                if hasattr(content, 'text'):
                    text = content.text.lower()
                    if any(phrase in text for phrase in [
                        "task completed", "successfully completed", "finished the task",
                        "task is done", "completed successfully", "mission accomplished",
                        "we have completed", "i have completed", "task has been completed"
                    ]):
                        task_completed = True
                        self.task_complete = True
                        self.add_to_history("System", "✓ Task completed successfully!")
                        return

            for content in response.content:
                if self.should_stop:
                    self.add_to_history("System", "Task stopped by user")
                    return
                    
                if hasattr(content, 'text'):
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": [{
                            "type": "text",
                            "text": content.text
                        }]
                    })
                    self.add_to_history("Claude", content.text)
                    
                elif hasattr(content, 'type') and content.type == 'tool_use':
                    tool_input = getattr(content, 'input', {})
                    action = tool_input.get('action', 'unknown')
                    
                    self.add_to_history("Tool", f"Executing: {action}")
                    result = self.execute_tool_action(action, tool_input)
                    
                    time.sleep(0.5)
                    
                    next_actions = []
                    if any(prev_content.text.lower() for prev_content in response.content 
                          if hasattr(prev_content, 'text')):
                        text = ' '.join(content.text.lower() for content in response.content 
                                      if hasattr(content, 'text'))
                        
                        if action == 'mouse_move':
                            if 'click' in text:
                                next_actions.append({'action': 'left_click', 'input': {}})
                                if 'type' in text:
                                    type_text = tool_input.get('text', '')
                                    if type_text:
                                        next_actions.append({
                                            'action': 'type',
                                            'input': {'text': type_text}
                                        })
                        elif action == 'left_click':
                            if 'type' in text:
                                type_text = tool_input.get('text', '')
                                if type_text:
                                    next_actions.append({
                                        'action': 'type',
                                        'input': {'text': type_text}
                                    })
                    
                    if result and result.get("type") != "error":
                        all_results = [result]
                        for next_action in next_actions:
                            if self.should_stop:
                                self.add_to_history("System", "Task stopped by user")
                                return
                            
                            self.add_to_history("System", f"Executing additional action: {next_action['action']}")
                            next_result = self.execute_tool_action(next_action['action'], next_action['input'])
                            if next_result:
                                all_results.append(next_result)
                                time.sleep(0.5)
                        
                        time.sleep(0.5)
                        new_screenshot_result = self.execute_tool_action('screenshot', {})
                        
                        if len(all_results) > 1:
                            result = {
                                "type": "combined_action",
                                "actions": all_results
                            }
                        
                        if self.should_stop:
                            self.add_to_history("System", "Task stopped by user")
                            return
                        
                        messages = [
                            {
                                "role": "user",
                                "content": [{
                                    "type": "text",
                                    "text": f"Your current task is: {self.current_task}\nPlease verify if the task is completed. If not, continue with the necessary actions."
                                }]
                            }
                        ]
                        
                        messages.extend(self.conversation_history)
                        
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "text",
                                "text": f"Action(s) completed: {json.dumps(result)}. Here is the current screen state after these actions:"
                            }, {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": self.current_screenshot["image_data"]
                                }
                            }]
                        })

                        try:
                            if not self.should_stop:
                                new_response = self.client.beta.messages.create(
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
                                
                                self.process_response(new_response)
                            
                        except Exception as api_error:
                            if "safety reasons" in str(api_error):
                                if not self.should_stop:
                                    self.add_to_history("System", "Retrying without screenshot...")
                                    messages = [msg for msg in messages 
                                              if "image" not in str(msg.get("content", ""))]
                                    retry_response = self.client.beta.messages.create(
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
                                    self.process_response(retry_response)
                            else:
                                raise api_error

        except Exception as e:
            self.add_to_history("Error", f"Error processing response: {str(e)}")
            self.task_complete = True
    
    def execute_tool_action(self, action, tool_input):
        try:
            time.sleep(0.2)
            
            if action == 'screenshot':
                screenshot = pyautogui.screenshot()
                max_size = (self.target_width, self.target_height)
                
                screenshot = screenshot.resize(max_size, Image.Resampling.LANCZOS)
                
                if hasattr(self, 'show_screenshots_var') and self.show_screenshots_var.get():
                    photo = ImageTk.PhotoImage(screenshot)
                    self.image_label.configure(image=photo)
                    self.image_label.image = photo
                
                buffered = BytesIO()
                screenshot.save(buffered, format="JPEG", quality=60, optimize=True)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                size_kb = len(buffered.getvalue()) / 1024
                self.add_to_history("Debug", f"Screenshot size: {size_kb:.2f}KB")
                
                self.current_screenshot = {
                    "image_data": img_str,
                    "size": size_kb,
                    "resolution": f"{max_size[0]}x{max_size[1]}"
                }
                
                self.add_to_history("System", "Screenshot captured and processed")
                return {"type": "screenshot_taken"}
        
            elif action == 'mouse_move':
                coordinates = tool_input.get('coordinate', [0, 0])
                
                real_x = min(int(coordinates[0] / self.scale_x), self.screen_width - 10)
                real_y = min(int(coordinates[1] / self.scale_y), self.screen_height - 10)
                
                self.add_to_history("Debug", 
                    f"Coordinate conversion:\n"
                    f"Input coordinates: ({coordinates[0]}, {coordinates[1]})\n"
                    f"Screen resolution: {self.screen_width}x{self.screen_height}\n"
                    f"Scale factors: {self.scale_x:.3f}, {self.scale_y:.3f}\n"
                    f"Last position: {self.last_mouse_pos}\n"
                    f"Calculated real coordinates: ({real_x}, {real_y})"
                )
                
                try:
                    current_x, current_y = pyautogui.position()
                    steps = 10
                    for i in range(steps + 1):
                        intermediate_x = current_x + ((real_x - current_x) * i / steps)
                        intermediate_y = current_y + ((real_y - current_y) * i / steps)
                        pyautogui.moveTo(intermediate_x, intermediate_y, duration=0.02)
                    
                    self.last_mouse_pos = (real_x, real_y)
                    self.add_to_history("System", 
                        f"Mouse moved to ({real_x}, {real_y})\n"
                        f"Original coordinates: ({coordinates[0]}, {coordinates[1]})"
                    )
                    return {
                        "type": "mouse_moved",
                        "from": [current_x, current_y],
                        "to": [real_x, real_y],
                        "original": coordinates,
                        "relative": coordinates[0] < 100 and coordinates[1] < 100
                    }
                except Exception as mouse_error:
                    self.add_to_history("Error", f"Mouse move failed: {str(mouse_error)}")
                    return {"type": "error", "error": str(mouse_error)}
                
            elif action == 'left_click':
                if self.last_mouse_pos:
                    try:
                        time.sleep(0.1)
                        pyautogui.click(self.last_mouse_pos[0], self.last_mouse_pos[1])
                        self.add_to_history("System", f"Clicked at {self.last_mouse_pos}")
                        
                        time.sleep(2.0)
                        
                        return {
                            "type": "click",
                            "position": self.last_mouse_pos
                        }
                    except Exception as click_error:
                        self.add_to_history("Error", f"Click failed: {str(click_error)}")
                        return {"type": "error", "error": str(click_error)}
                else:
                    self.add_to_history("Error", "No previous mouse position for click")
                    return {"type": "error", "message": "No mouse position"}
                
            elif action == 'type':
                text = tool_input.get('text', '')
                pyautogui.write(text, interval=0.1)
                self.add_to_history("System", f"Typed: {text}")
                return {
                    "type": "type",
                    "text": text
                }
                
            elif action == 'key':
                key = tool_input.get('text', '')
                pyautogui.press(key)
                time.sleep(0.5)
                self.add_to_history("System", f"Pressed key: {key}")
                return {
                    "type": "key",
                    "key": key
                }
            
            return {"status": "unknown_action"}
                
        except Exception as e:
            self.add_to_history("Error", f"Tool execution error: {str(e)}")
            return {"error": str(e)}
    
    def continue_conversation_with_context(self, tool_result):
        try:
            if tool_result.get("type") == "screenshot":
                next_message = {
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": f"I'm helping you with: {self.current_task}"
                    }, {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": tool_result["image_data"]
                        }
                    }]
                }
            else:
                next_message = {
                    "role": "user",
                    "content": [{
                        "type": "text",
                        "text": f"Current task: {self.current_task}\nLast action performed: {tool_result.get('action')} with result: {json.dumps(tool_result)}"
                    }]
                }

            messages = [{
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": f"We are using a VM environment with screen resolution {self.screen_width}x{self.screen_height}. Mouse coordinates have been scaled appropriately."
                }]
            }, next_message]

            response = self.client.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0,
                messages=messages,
                tools=[{
                    "type": "computer_20241022",
                    "name": "computer",
                    "display_width_px": self.screen_width,
                    "display_height_px": self.screen_height,
                    "display_number": 1
                }],
                betas=["computer-use-2024-10-22"]
            )
            
            self.process_response(response)
            
        except Exception as e:
            if "rate_limit_error" in str(e):
                self.add_to_history("System", "Rate limit reached. Waiting 60 seconds...")
                time.sleep(60)
                self.continue_conversation_with_context(tool_result)
            else:
                self.add_to_history("Error", f"Error continuing conversation: {str(e)}")
                self.task_complete = True