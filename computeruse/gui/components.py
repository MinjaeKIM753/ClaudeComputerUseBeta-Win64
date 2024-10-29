# computeruse/gui/components.py
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Any, Optional, Tuple
from PIL import Image, ImageTk
import base64
from io import BytesIO

class APIFrame(ttk.LabelFrame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent, text="API Configuration", padding="5")
        self.controller = controller
        
        ttk.Label(self, text="API Key:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.api_key_var = tk.StringVar(value=self.controller.config.get_api_key())
        self.api_entry = ttk.Entry(
            self,
            textvariable=self.api_key_var,
            width=50,
            show='*'
        )
        self.api_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self,
            text="Show Key",
            variable=self.show_key_var,
            command=self.toggle_key_visibility
        ).pack(side=tk.LEFT)
        
        self.init_btn = ttk.Button(
            self,
            text="Initialize Client",
            command=self.controller.save_and_initialize,
            style="Action.TButton"
        )
        self.init_btn.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(
            self,
            text="⭕ Client Not Initialized",
            style="Status.TLabel"
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
    
    def toggle_key_visibility(self) -> None:
        self.api_entry.config(show='' if self.show_key_var.get() else '*')

class OptionsFrame(ttk.LabelFrame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent, text="Options", padding="5")
        self.controller = controller
        
        # Main options
        options_frame = ttk.Frame(self)
        options_frame.pack(fill=tk.X, expand=True)
        
        # Screenshots toggle
        self.show_screenshots_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Show Screenshots",
            variable=self.show_screenshots_var,
            command=self.controller.update_screenshot_preview
        ).pack(side=tk.LEFT, padx=5)
        
        # Mouse behavior
        mouse_frame = ttk.LabelFrame(options_frame, text="Mouse", padding="3")
        mouse_frame.pack(side=tk.LEFT, padx=5)
        
        self.teleport_mouse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            mouse_frame,
            text="Instant Movement",
            variable=self.teleport_mouse_var
        ).pack(side=tk.LEFT, padx=5)
        
        # Resolution settings
        resolution_frame = ttk.LabelFrame(self, text="Resolution Settings", padding="3")
        resolution_frame.pack(fill=tk.X, expand=True, pady=5)
        
        # Downscale control
        scale_frame = ttk.Frame(resolution_frame)
        scale_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(scale_frame, text="Downscale:").pack(side=tk.LEFT)
        
        self.downscale_var = tk.DoubleVar(value=0.5)
        self.downscale_scale = ttk.Scale(
            scale_frame,
            from_=0.1,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.downscale_var,
            command=self.on_scale_changed
        )
        self.downscale_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.downscale_label = ttk.Label(scale_frame, text="0.5")
        self.downscale_label.pack(side=tk.LEFT, padx=5)
        
        # Native resolution display
        native_res = f"{self.controller.interface.native_width}x{self.controller.interface.native_height}"
        ttk.Label(resolution_frame, text=f"Native: {native_res}").pack(side=tk.LEFT, padx=10)
        
        # Target resolution display
        self.target_res_label = ttk.Label(resolution_frame, text="Target: calculating...")
        self.target_res_label.pack(side=tk.LEFT, padx=10)
        
        # Timing settings
        timing_frame = ttk.LabelFrame(self, text="Timing Settings", padding="3")
        timing_frame.pack(fill=tk.X, expand=True, pady=5)
        
        ttk.Label(timing_frame, text="Action Delay:").pack(side=tk.LEFT)
        
        self.wait_time_var = tk.DoubleVar(value=3.0)
        wait_scale = ttk.Scale(
            timing_frame,
            from_=0.5,
            to=10.0,
            orient=tk.HORIZONTAL,
            variable=self.wait_time_var
        )
        wait_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.wait_time_label = ttk.Label(timing_frame, text="3.0s")
        self.wait_time_label.pack(side=tk.LEFT, padx=5)
    
    def on_scale_changed(self, *args) -> None:
        """Handle scale change events"""
        value = round(self.downscale_var.get(), 1)
        self.downscale_var.set(value)
        self.downscale_label.config(text=f"{value:.1f}")
        
        # Update target resolution display
        target_width = int(self.controller.interface.native_width * value)
        target_height = int(self.controller.interface.native_height * value)
        self.target_res_label.config(text=f"Target: {target_width}x{target_height}")
        
        # Update interface
        self.controller.interface.update_target_resolution(value)
        
        # Update preview if available
        self.controller.update_screenshot_preview()
    
    def snap_to_nearest_tenth(self, event: Optional[tk.Event]) -> None:
        """Snap scale value to nearest tenth"""
        value = round(self.downscale_var.get() * 10) / 10
        self.downscale_var.set(value)
        self.on_scale_changed()

class CoordinateDebugFrame(ttk.LabelFrame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent, text="Coordinate Debug", padding="5")
        self.controller = controller
        
        # Debug mode toggle
        debug_frame = ttk.Frame(self)
        debug_frame.pack(fill=tk.X, expand=True)
        
        ttk.Checkbutton(
            debug_frame,
            text="Enable Coordinate Debug",
            variable=self.controller.debug_mode
        ).pack(side=tk.LEFT, padx=5)
        
        # Coordinate display
        coord_frame = ttk.Frame(self)
        coord_frame.pack(fill=tk.X, expand=True, pady=5)
        
        # Screen coordinates
        screen_frame = ttk.LabelFrame(coord_frame, text="Screen", padding="3")
        screen_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.screen_coords = ttk.Label(screen_frame, text="X: 0, Y: 0")
        self.screen_coords.pack(side=tk.LEFT, padx=5)
        
        # Scaled coordinates
        scaled_frame = ttk.LabelFrame(coord_frame, text="Scaled", padding="3")
        scaled_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.scaled_coords = ttk.Label(scaled_frame, text="X: 0, Y: 0")
        self.scaled_coords.pack(side=tk.LEFT, padx=5)
        
        # Scale factor
        scale_frame = ttk.LabelFrame(coord_frame, text="Scale", padding="3")
        scale_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.scale_factor = ttk.Label(scale_frame, text="1.0")
        self.scale_factor.pack(side=tk.LEFT, padx=5)
        
        # Last action
        self.last_action_frame = ttk.LabelFrame(self, text="Last Action", padding="3")
        self.last_action_frame.pack(fill=tk.X, expand=True, pady=5)
        
        self.last_action = ttk.Label(self.last_action_frame, text="No action yet")
        self.last_action.pack(side=tk.LEFT, padx=5)
    
    def update_coordinates(self, 
                         screen_x: int, screen_y: int,
                         scaled_x: int, scaled_y: int,
                         scale: float) -> None:
        """Update coordinate displays"""
        if self.controller.debug_mode.get():
            self.screen_coords.config(text=f"X: {screen_x}, Y: {screen_y}")
            self.scaled_coords.config(text=f"X: {scaled_x}, Y: {scaled_y}")
            self.scale_factor.config(text=f"{scale:.1f}")
    
    def update_last_action(self, action_type: str, coordinates: Tuple[float, float]) -> None:
        """Update last action display"""
        if self.controller.debug_mode.get():
            self.last_action.config(
                text=f"{action_type} at X: {coordinates[0]:.1f}, Y: {coordinates[1]:.1f}"
            )

class PreviewFrame(ttk.LabelFrame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent, text="Preview & Debug", padding="5")
        self.controller = controller
        
        # Screenshot preview
        self.preview_label = ttk.Label(self, text="No screenshot available")
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # Coordinate overlay canvas
        self.overlay = tk.Canvas(self, highlightthickness=0)
        self.overlay.pack(fill=tk.BOTH, expand=True)
        
        # Mouse position tracking
        self.overlay.bind('<Motion>', self.on_mouse_move)
        
        # Coordinate markers
        self.markers = []
    
    def update_preview(self, screenshot_data: str) -> None:
        try:
            screenshot = Image.open(BytesIO(base64.b64decode(screenshot_data)))
            
            # Get widget dimensions
            width = self.winfo_width()
            height = self.winfo_height()
            
            # Resize maintaining aspect ratio
            screenshot.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(screenshot)
            self.preview_label.configure(image=photo)
            self.preview_label.image = photo
            
            # Clear previous markers
            self.clear_markers()
            
        except Exception as e:
            self.controller.logger.add_entry("Error", f"Preview update failed: {str(e)}")
    
    def add_coordinate_marker(self, x: float, y: float, color: str = "red", 
                            label: str = "") -> None:
        """Add a coordinate marker to the overlay"""
        if self.controller.debug_mode.get():
            marker = self.overlay.create_oval(
                x-5, y-5, x+5, y+5,
                outline=color,
                width=2
            )
            if label:
                text = self.overlay.create_text(
                    x+10, y-10,
                    text=label,
                    fill=color,
                    anchor="w"
                )
                self.markers.extend([marker, text])
            else:
                self.markers.append(marker)
    
    def clear_markers(self) -> None:
        """Clear all coordinate markers"""
        for marker in self.markers:
            self.overlay.delete(marker)
        self.markers.clear()
    
    def on_mouse_move(self, event: tk.Event) -> None:
        """Handle mouse movement over preview"""
        if self.controller.debug_mode.get():
            # Get relative coordinates in preview
            x = event.x
            y = event.y
            
            # Calculate scaled coordinates
            scale = self.controller.options_frame.downscale_var.get()
            scaled_x = int(x / scale)
            scaled_y = int(y / scale)
            
            # Update coordinate debug display
            self.controller.coord_debug_frame.update_coordinates(
                x, y, scaled_x, scaled_y, scale
            )

class InputFrame(ttk.LabelFrame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent, text="Input", padding="5")
        self.controller = controller
        
        # Input area
        self.input_text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            width=70,
            height=5,
            font=('Arial', 10)
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(side=tk.RIGHT, pady=(5, 0))
        
        # Submit button
        self.submit_btn = ttk.Button(
            button_frame,
            text="Submit",
            command=self.controller.handle_submit,
            state='disabled',
            style="Action.TButton"
        )
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_btn = ttk.Button(
            button_frame,
            text="Stop",
            command=self.controller.stop_processing,
            state='disabled',
            style="Stop.TButton"
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_input,
            style="Action.TButton"
        )
        clear_btn.pack(side=tk.LEFT)
        
        # Add common tasks dropdown
        self.add_task_templates()
    
    def add_task_templates(self) -> None:
        """Add dropdown for common task templates"""
        template_frame = ttk.Frame(self)
        template_frame.pack(side=tk.LEFT, pady=(5, 0))
        
        ttk.Label(template_frame, text="Quick Tasks:").pack(side=tk.LEFT, padx=5)
        
        tasks = [
            "Open Notepad and type 'Hello World'",
            "Take a screenshot and save it",
            "Open Calculator and perform 2+2",
            "Create a new folder on desktop",
            "Open browser and go to google.com",
            "Change system volume",
            "Move mouse to screen center",
            "Right click and select from menu"
        ]
        
        self.task_var = tk.StringVar()
        task_menu = ttk.OptionMenu(
            template_frame,
            self.task_var,
            "Select a task...",
            *tasks,
            command=self.load_template
        )
        task_menu.pack(side=tk.LEFT)
    
    def load_template(self, selection: str) -> None:
        """Load selected task template into input"""
        if selection != "Select a task...":
            self.clear_input()
            self.input_text.insert(tk.END, selection)
    
    def clear_input(self) -> None:
        """Clear the input text"""
        self.input_text.delete(1.0, tk.END)

class HistoryFrame(ttk.LabelFrame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent, text="Action History", padding="5")
        self.controller = controller
        
        # Create text widget with improved styling
        self.history_text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            width=70,
            height=20,
            font=('Courier', 10),
            bg='#1e1e1e',
            fg='#ffffff'
        )
        self.history_text.pack(fill=tk.BOTH, expand=True)
        
        # Add text tags for different message types
        self.history_text.tag_configure("system", foreground="#00ff00")
        self.history_text.tag_configure("error", foreground="#ff0000")
        self.history_text.tag_configure("debug", foreground="#888888")
        self.history_text.tag_configure("action", foreground="#00ffff")
        self.history_text.tag_configure("claude", foreground="#ffff00")
        
        # Control frame at bottom
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Clear button
        ttk.Button(
            control_frame,
            text="Clear History",
            command=self.clear_history,
            style="Action.TButton"
        ).pack(side=tk.LEFT)
        
        # Auto-scroll toggle
        self.auto_scroll = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            control_frame,
            text="Auto-scroll",
            variable=self.auto_scroll
        ).pack(side=tk.LEFT, padx=10)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(control_frame, text="Filters", padding="3")
        filter_frame.pack(side=tk.LEFT, padx=10)
        
        # Message type filters
        self.filters = {
            "system": tk.BooleanVar(value=True),
            "error": tk.BooleanVar(value=True),
            "debug": tk.BooleanVar(value=True),
            "action": tk.BooleanVar(value=True),
            "claude": tk.BooleanVar(value=True)
        }
        
        for msg_type, var in self.filters.items():
            ttk.Checkbutton(
                filter_frame,
                text=msg_type.capitalize(),
                variable=var,
                command=self.apply_filters
            ).pack(side=tk.LEFT, padx=2)
        
        # Set the text widget for the logger
        self.controller.logger.set_text_widget(self.history_text)
    
    def clear_history(self) -> None:
        """Clear the history text"""
        self.history_text.configure(state='normal')
        self.history_text.delete(1.0, tk.END)
        self.history_text.configure(state='disabled')
    
    def apply_filters(self) -> None:
        """Apply message type filters"""
        self.history_text.configure(state='normal')
        
        # Hide all tags first
        for tag in self.filters.keys():
            self.history_text.tag_config(tag, elide=not self.filters[tag].get())
        
        self.history_text.configure(state='disabled')

class StatusBar(ttk.Frame):
    def __init__(self, parent: Any, controller: Any):
        super().__init__(parent)
        self.controller = controller
        
        # Status message
        self.status_var = tk.StringVar(value="Ready to start")
        self.status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            style="Status.TLabel"
        )
        self.status_label.pack(fill=tk.X, expand=True)
        
        # Progress frame
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, expand=True, pady=(5, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=self.controller.config.get_setting('max_iterations')
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Iteration counter
        self.iteration_label = ttk.Label(
            progress_frame,
            text="0/0",
            style="Status.TLabel",
            width=10
        )
        self.iteration_label.pack(side=tk.LEFT, padx=5)
        
        # Additional status indicators
        status_indicators = ttk.Frame(self)
        status_indicators.pack(fill=tk.X, expand=True, pady=(5, 0))
        
        # Mouse position
        self.mouse_pos_label = ttk.Label(
            status_indicators,
            text="Mouse: (0, 0)",
            style="Status.TLabel"
        )
        self.mouse_pos_label.pack(side=tk.LEFT, padx=5)
        
        # Scale factor
        self.scale_label = ttk.Label(
            status_indicators,
            text="Scale: 1.0",
            style="Status.TLabel"
        )
        self.scale_label.pack(side=tk.LEFT, padx=5)
        
        # Resolution
        self.resolution_label = ttk.Label(
            status_indicators,
            text="Resolution: Native",
            style="Status.TLabel"
        )
        self.resolution_label.pack(side=tk.LEFT, padx=5)
    
    def update_iterations(self, current: int, maximum: int) -> None:
        """Update iteration counter"""
        self.iteration_label.config(text=f"{current}/{maximum}")
        self.progress_var.set(current)
    
    def update_mouse_position(self, x: int, y: int) -> None:
        """Update mouse position display"""
        self.mouse_pos_label.config(text=f"Mouse: ({x}, {y})")
    
    def update_scale(self, scale: float) -> None:
        """Update scale factor display"""
        self.scale_label.config(text=f"Scale: {scale:.1f}")
    
    def update_resolution(self, width: int, height: int) -> None:
        """Update resolution display"""
        self.resolution_label.config(text=f"Resolution: {width}x{height}")

# Styles
def create_style() -> ttk.Style:
    style = ttk.Style()
    
    # Configure frame styles
    style.configure(
        "MainFrame.TFrame",
        background="#f0f0f0",
        relief="flat"
    )
    
    # Configure label styles
    style.configure(
        "Header.TLabel",
        font=('Helvetica', 12, 'bold'),
        padding=5
    )
    
    style.configure(
        "Status.TLabel",
        font=('Helvetica', 10),
        padding=3
    )
    
    # Configure button styles
    style.configure(
        "Action.TButton",
        font=('Helvetica', 10),
        padding=5
    )
    
    style.configure(
        "Stop.TButton",
        font=('Helvetica', 10, 'bold'),
        padding=5,
        background="#ff4444"
    )
    
    return style