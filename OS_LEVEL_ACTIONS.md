# OS-Level Execution Layer

## Overview

The OS-Level Executor provides the agent with **maximum power and reliability** by directly interfacing with the Windows operating system through PowerShell and CMD commands. This bypasses GUI automation issues and provides deterministic, fast execution.

## Why OS-Level Actions?

### Problems with GUI Automation
- **Unreliable**: Clicks can miss targets, UI elements can move
- **Slow**: Need to wait for animations, rendering
- **Fragile**: Breaks when UI changes
- **Focus Issues**: Windows can steal focus

### OS-Level Advantages
- **Deterministic**: Commands always execute the same way
- **Fast**: No waiting for UI rendering
- **Reliable**: Direct system calls
- **Powerful**: Can do things GUI can't

## Available Actions

### 1. `os_open_app` - Open Applications
**Most reliable way to launch apps!**

```json
{
  "action": "os_open_app",
  "args": {
    "name": "chrome"
  }
}
```

**Supported Apps:**
- `notepad`, `calculator`, `paint`
- `chrome`, `edge`, `firefox`, `brave`
- `vscode`, `cmd`, `powershell`, `terminal`
- `outlook`, `word`, `excel`, `powerpoint`
- `explorer`, `taskmanager`, `settings`

**How it works:** Uses PowerShell `Start-Process` command

---

### 2. `os_run_command` - Run Any OS Command
**Ultimate power - execute any PowerShell/CMD command!**

```json
{
  "action": "os_run_command",
  "args": {
    "command": "Get-Process | Where-Object {$_.Name -eq 'chrome'}",
    "shell": "powershell",
    "wait": true
  }
}
```

**Examples:**

**List running processes:**
```json
{
  "action": "os_run_command",
  "args": {
    "command": "Get-Process | Select-Object Name, CPU | Sort-Object CPU -Descending",
    "shell": "powershell"
  }
}
```

**Get network info:**
```json
{
  "action": "os_run_command",
  "args": {
    "command": "ipconfig /all",
    "shell": "cmd"
  }
}
```

**Create directory:**
```json
{
  "action": "os_run_command",
  "args": {
    "command": "New-Item -ItemType Directory -Path 'C:\\MyFolder'",
    "shell": "powershell"
  }
}
```

---

### 3. `os_open_url` - Open URLs
**Opens URL in default browser - very reliable!**

```json
{
  "action": "os_open_url",
  "args": {
    "url": "https://google.com"
  }
}
```

**How it works:** Uses PowerShell `Start-Process` with URL

---

### 4. `os_file_operation` - File Operations
**Create, read, delete, copy, move files**

**Create file:**
```json
{
  "action": "os_file_operation",
  "args": {
    "operation": "create",
    "path": "C:\\Users\\user\\Desktop\\test.txt",
    "content": "Hello World!"
  }
}
```

**Read file:**
```json
{
  "action": "os_file_operation",
  "args": {
    "operation": "read",
    "path": "C:\\Users\\user\\Desktop\\test.txt"
  }
}
```

**Copy file:**
```json
{
  "action": "os_file_operation",
  "args": {
    "operation": "copy",
    "path": "C:\\source.txt",
    "destination": "C:\\dest.txt"
  }
}
```

**Delete file:**
```json
{
  "action": "os_file_operation",
  "args": {
    "operation": "delete",
    "path": "C:\\Users\\user\\Desktop\\test.txt"
  }
}
```

---

### 5. `os_window_control` - Window Management
**Control windows using PowerShell**

**Close window by title:**
```json
{
  "action": "os_window_control",
  "args": {
    "operation": "close",
    "window_title": "Chrome"
  }
}
```

**List all open windows:**
```json
{
  "action": "os_window_control",
  "args": {
    "operation": "list"
  }
}
```

---

### 6. `os_clipboard` - Clipboard Operations
**Copy/paste using PowerShell**

**Copy to clipboard:**
```json
{
  "action": "os_clipboard",
  "args": {
    "operation": "copy",
    "text": "Hello, this is copied!"
  }
}
```

**Get clipboard content:**
```json
{
  "action": "os_clipboard",
  "args": {
    "operation": "get"
  }
}
```

---

### 7. `os_system_control` - System Controls
**Control system settings**

**Set volume:**
```json
{
  "action": "os_system_control",
  "args": {
    "operation": "volume_set",
    "level": 50
  }
}
```

**Get all processes:**
```json
{
  "action": "os_system_control",
  "args": {
    "operation": "get_processes"
  }
}
```

**Kill process:**
```json
{
  "action": "os_system_control",
  "args": {
    "operation": "kill_process",
    "process_name": "chrome"
  }
}
```

---

## Usage Guidelines

### When to Use OS-Level Actions

✅ **Use OS actions for:**
- Opening applications (most reliable)
- Opening URLs
- File operations
- Running system commands
- Window management
- Clipboard operations
- System information gathering

❌ **Don't use OS actions for:**
- Typing in specific UI fields (use `type` action)
- Clicking specific UI elements (use `click` or `click_text`)
- Browser DOM manipulation (use `browser_*` actions)

### Action Hierarchy (Preference Order)

1. **OS-Level Actions** (Most Reliable) ⭐⭐⭐
   - `os_open_app`, `os_run_command`, `os_open_url`
   
2. **Semantic Actions** (Smart) ⭐⭐
   - `vscode_open`, `browser_search`, `launch_app`
   
3. **GUI Actions** (Fallback) ⭐
   - `click`, `type`, `scroll`

### Best Practices

1. **Always prefer OS actions when available**
   ```json
   // ❌ Bad
   {"action": "launch_app", "args": {"name": "chrome"}}
   
   // ✅ Good
   {"action": "os_open_app", "args": {"name": "chrome"}}
   ```

2. **Use os_run_command for complex tasks**
   ```json
   // Instead of multiple GUI clicks, use one command
   {
     "action": "os_run_command",
     "args": {
       "command": "Get-ChildItem C:\\ | Where-Object {$_.Length -gt 1MB}",
       "shell": "powershell"
     }
   }
   ```

3. **Combine OS actions with GUI actions**
   ```json
   // Step 1: Open app with OS (reliable)
   {"action": "os_open_app", "args": {"name": "notepad"}}
   
   // Step 2: Type with GUI (precise)
   {"action": "type", "args": {"text": "Hello World"}}
   ```

## Security Considerations

⚠️ **Important:** The `os_run_command` action is very powerful and can execute ANY system command. The agent should:

1. Never run destructive commands without user confirmation
2. Validate file paths before operations
3. Use safe PowerShell practices
4. Log all OS-level actions

## Implementation Details

### Technology Stack
- **PowerShell**: Primary shell for Windows automation
- **CMD**: Fallback for legacy commands
- **subprocess**: Python module for command execution
- **Windows APIs**: Direct system calls

### Error Handling
All OS actions return:
```python
{
    "success": bool,
    "output": str,  # Command output
    "error": str,   # Error message if failed
    "returncode": int  # Exit code
}
```

## Examples

### Example 1: Open Chrome and Navigate
```json
// Step 1: Open Chrome
{
  "thought": "Opening Chrome using OS command for reliability",
  "action": "os_open_app",
  "args": {"name": "chrome"}
}

// Step 2: Navigate to URL
{
  "thought": "Using Ctrl+L to focus address bar",
  "action": "press_key",
  "args": {"key": "ctrl+l"}
}

// Step 3: Type URL and submit
{
  "thought": "Typing URL and submitting",
  "action": "type",
  "args": {"text": "google.com", "submit": true}
}
```

### Example 2: Create and Edit File
```json
// Step 1: Create file
{
  "action": "os_file_operation",
  "args": {
    "operation": "create",
    "path": "C:\\Users\\user\\Desktop\\notes.txt",
    "content": "My Notes\n========\n"
  }
}

// Step 2: Open in Notepad
{
  "action": "os_run_command",
  "args": {
    "command": "notepad C:\\Users\\user\\Desktop\\notes.txt",
    "shell": "cmd",
    "wait": false
  }
}
```

### Example 3: System Information
```json
{
  "action": "os_run_command",
  "args": {
    "command": "systeminfo | findstr /C:\"OS Name\" /C:\"Total Physical Memory\"",
    "shell": "cmd"
  }
}
```

---

## Conclusion

The OS-Level Executor makes the agent **significantly more powerful and reliable** by:
- ✅ Bypassing GUI automation issues
- ✅ Providing direct system access
- ✅ Enabling complex tasks via PowerShell
- ✅ Offering deterministic execution

**Use OS-level actions whenever possible for maximum reliability!** 🚀
