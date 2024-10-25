from computeruse import ClaudeVMInterface
import tkinter as tk

def main():
    root = tk.Tk()
    app = ClaudeVMInterface(root)
    root.mainloop()

if __name__ == "__main__":
    main()