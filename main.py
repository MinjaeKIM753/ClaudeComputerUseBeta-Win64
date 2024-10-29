# main.py
import tkinter as tk
import sys
import traceback
import logging
import os
from datetime import datetime
from computeruse import ComputerInterface

def setup_logging() -> None:
    """Setup logging configuration"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join('logs', f'computeruse_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_requirements() -> bool:
    """Check if all required packages are installed"""
    # Map pip package names to their import names
    package_map = {
        'anthropic': 'anthropic',
        'Pillow': 'PIL',  # Pillow imports as PIL
        'PyAutoGUI': 'pyautogui'
    }
    
    missing_packages = []
    
    for package, import_name in package_map.items():
        try:
            __import__(import_name)
            logging.info(f"Found package: {package}")
        except ImportError:
            missing_packages.append(package)
            logging.error(f"Missing package: {package}")
    
    if missing_packages:
        print("Missing required packages:")
        print("\n".join(f"- {pkg}" for pkg in missing_packages))
        print("\nPlease install missing packages using:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logging.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

def main() -> None:
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        logging.info("Application starting...")
        
        # Check requirements
        if not check_requirements():
            logging.error("Missing required packages")
            sys.exit(1)
        
        # Create main window
        root = tk.Tk()
        
        # Set window icon if available
        try:
            if os.path.exists("img/icon.ico"):
                root.iconbitmap("img/icon.ico")
        except Exception as e:
            logging.warning(f"Could not load window icon: {e}")
        
        # Initialize application
        app = ComputerInterface(root)
        
        # Set exception handler
        sys.excepthook = handle_exception
        
        # Start application
        logging.info("Starting main loop...")
        root.mainloop()
        
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        logging.info("Application shutting down...")

if __name__ == "__main__":
    main()