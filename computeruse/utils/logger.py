# computeruse/utils/logger.py
from datetime import datetime
from typing import List, Dict
import tkinter as tk
from tkinter import scrolledtext

class Logger:
    def __init__(self):
        self.history: List[Dict] = []
        self.text_widget: scrolledtext.ScrolledText = None
        
    def set_text_widget(self, widget: scrolledtext.ScrolledText) -> None:
        self.text_widget = widget
        
    def add_entry(self, source: str, message: str) -> str:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = {
            'timestamp': timestamp,
            'source': source,
            'message': message
        }
        self.history.append(entry)
        formatted_message = f"[{timestamp}] {source}: {message}\n"
        
        if self.text_widget:
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, formatted_message)
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
            
        return formatted_message
    
    def clear_history(self) -> None:
        self.history.clear()
        if self.text_widget:
            self.text_widget.configure(state='normal')
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.configure(state='disabled')