from .ClaudeVMInterface import ClaudeVMInterface
import tkinter as tk


root = tk.Tk()
app = ClaudeVMInterface(root)
root.mainloop()

__all__ = ["ClaudeVMInterface"]