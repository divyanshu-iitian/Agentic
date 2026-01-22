
import json
from pathlib import Path
import os

print("--- DIAGNOSTIC START ---")

# 1. Define Path
file_path = Path(__file__).parent / "agent_memory.json"
print(f"Target File: {file_path}")
print(f"Absolute Path: {file_path.absolute()}")

# 2. Check Permissions
print(f"Directory Exists: {file_path.parent.exists()}")
print(f"Directory Writable: {os.access(file_path.parent, os.W_OK)}")

# 3. Try READ
try:
    if file_path.exists():
        with open(file_path, "r") as f:
            content = f.read()
            print(f"Current Content Length: {len(content)}")
            print(f"Current Content Preview: {content[:50]}")
    else:
        print("File does not exist yet.")
except Exception as e:
    print(f"READ ERROR: {e}")

# 4. Try WRITE
try:
    test_data = [{"task": "DIAGNOSTIC_TEST", "feedback": "System Check", "steps": [], "timestamp": "NOW"}]
    with open(file_path, "w") as f:
        json.dump(test_data, f, indent=2)
    print("WRITE SUCCESS: Data written to disk.")
except Exception as e:
    print(f"WRITE ERROR: {e}")

# 5. Verify WRITE
try:
    with open(file_path, "r") as f:
        new_content = json.load(f)
        print(f"VERIFICATION: Read back {len(new_content)} entries.")
        if new_content[0]["task"] == "DIAGNOSTIC_TEST":
             print("VERIFICATION PASSED: Content matches.")
        else:
             print("VERIFICATION FAILED: Content mismatch.")
except Exception as e:
    print(f"VERIFICATION ERROR: {e}")
    
print("--- DIAGNOSTIC END ---")
