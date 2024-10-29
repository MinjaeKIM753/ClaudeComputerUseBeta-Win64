# computeruse/gui/styles.py
from tkinter import ttk
from typing import Any

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
        background="#ff4444",
        font=('Helvetica', 10),
        padding=5
    )
    
    return style