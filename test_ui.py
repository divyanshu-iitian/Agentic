"""
UI Test Script

Test the premium UI without running the full agent.
"""

import sys
sys.path.insert(0, '.')

from ui.floating_input import UIController
import time

def on_command(cmd):
    """Handle command"""
    print(f"Command received: {cmd}")

def main():
    """Test UI"""
    print("🎨 Testing Premium UI...")
    print("Press Ctrl+C to exit")
    
    # Create UI
    ui = UIController(on_command=on_command)
    ui.start()
    
    # Simulate status changes for demo
    def demo_statuses():
        time.sleep(2)
        ui.set_status("Working on task...", "#3366ff")
        time.sleep(3)
        ui.set_status("✅ Completed", "#00ff88")
    
    import threading
    demo_thread = threading.Thread(target=demo_statuses, daemon=True)
    demo_thread.start()
    
    # Run UI
    try:
        ui.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        ui.stop()

if __name__ == "__main__":
    main()
