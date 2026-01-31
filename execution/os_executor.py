"""
OS-Level Executor

Executes tasks using native OS commands for maximum reliability.
Uses PowerShell, CMD, and Windows APIs directly.
"""

import subprocess
import time
import os
from typing import Dict, Any, Optional, List
from utils.logger import log


class OSExecutor:
    """Execute tasks using OS-level commands (PowerShell, CMD, Windows APIs)"""
    
    def __init__(self):
        self.shell = "powershell.exe"
        log.info("OS Executor initialized (PowerShell)")
    
    def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an OS-level action.
        
        Args:
            action: Action name
            args: Action arguments
            
        Returns:
            Execution result
        """
        log.info(f"Executing OS action: {action}")
        
        try:
            if action == "os_open_app":
                return self._open_app(args)
            elif action == "os_run_command":
                return self._run_command(args)
            elif action == "os_open_url":
                return self._open_url(args)
            elif action == "os_file_operation":
                return self._file_operation(args)
            elif action == "os_window_control":
                return self._window_control(args)
            elif action == "os_clipboard":
                return self._clipboard_operation(args)
            elif action == "os_system_control":
                return self._system_control(args)
            else:
                return {"success": False, "error": f"Unknown OS action: {action}"}
        
        except Exception as e:
            log.error(f"OS action failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _open_app(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Open application using OS commands.
        Most reliable method - uses Start-Process.
        """
        app_name = args["name"]
        log.info(f"🚀 OS: Opening {app_name}")
        
        # Common app mappings
        app_commands = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "firefox": "firefox.exe",
            "brave": "brave.exe",
            "explorer": "explorer.exe",
            "outlook": "outlook.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "vscode": "code",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "terminal": "wt.exe",
            "paint": "mspaint.exe",
            "snipping": "SnippingTool.exe",
            "settings": "ms-settings:",
            "taskmanager": "taskmgr.exe",
        }
        
        command = app_commands.get(app_name.lower(), app_name)
        
        # Use PowerShell Start-Process for reliability
        ps_command = f'Start-Process "{command}"'
        
        try:
            result = subprocess.run(
                [self.shell, "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            time.sleep(2)  # Wait for app to launch
            
            if result.returncode == 0:
                log.info(f"✅ OS: Opened {app_name}")
                return {"success": True, "app": app_name, "method": "os_command"}
            else:
                log.error(f"Failed to open {app_name}: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            log.error(f"OS open app failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _run_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run arbitrary PowerShell/CMD command.
        POWERFUL but needs safety checks.
        """
        command = args["command"]
        shell_type = args.get("shell", "powershell")  # powershell or cmd
        wait = args.get("wait", True)
        
        log.info(f"🔧 OS: Running command: {command}")
        
        shell_exe = "powershell.exe" if shell_type == "powershell" else "cmd.exe"
        shell_flag = "-Command" if shell_type == "powershell" else "/c"
        
        try:
            if wait:
                result = subprocess.run(
                    [shell_exe, shell_flag, command],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr,
                    "returncode": result.returncode
                }
            else:
                # Run in background
                subprocess.Popen(
                    [shell_exe, shell_flag, command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                return {"success": True, "background": True}
                
        except Exception as e:
            log.error(f"Command execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _open_url(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Open URL using OS default browser.
        Uses 'start' command - most reliable.
        """
        url = args["url"]
        log.info(f"🌐 OS: Opening URL: {url}")
        
        try:
            # Use PowerShell Start-Process with URL
            ps_command = f'Start-Process "{url}"'
            
            result = subprocess.run(
                [self.shell, "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            time.sleep(2)
            
            return {
                "success": result.returncode == 0,
                "url": url,
                "method": "os_start"
            }
            
        except Exception as e:
            log.error(f"URL open failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _file_operation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        File operations using OS commands.
        Operations: create, delete, copy, move, read, write
        """
        operation = args["operation"]
        path = args["path"]
        
        log.info(f"📁 OS: File operation '{operation}' on {path}")
        
        try:
            if operation == "create":
                content = args.get("content", "")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {"success": True, "operation": "create", "path": path}
            
            elif operation == "read":
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"success": True, "content": content, "path": path}
            
            elif operation == "delete":
                os.remove(path)
                return {"success": True, "operation": "delete", "path": path}
            
            elif operation == "copy":
                dest = args["destination"]
                ps_command = f'Copy-Item -Path "{path}" -Destination "{dest}"'
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": result.returncode == 0}
            
            elif operation == "move":
                dest = args["destination"]
                ps_command = f'Move-Item -Path "{path}" -Destination "{dest}"'
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": result.returncode == 0}
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            log.error(f"File operation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _window_control(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Window management using PowerShell.
        Operations: minimize, maximize, close, focus
        """
        operation = args["operation"]
        window_title = args.get("window_title", "")
        
        log.info(f"🪟 OS: Window control '{operation}' on {window_title}")
        
        try:
            if operation == "close":
                # Close window by title
                ps_command = f'''
                Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_title}*"}} | 
                ForEach-Object {{$_.CloseMainWindow()}}
                '''
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": result.returncode == 0}
            
            elif operation == "list":
                # List all windows
                ps_command = '''
                Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | 
                Select-Object MainWindowTitle, ProcessName | ConvertTo-Json
                '''
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": True, "windows": result.stdout}
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            log.error(f"Window control failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _clipboard_operation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clipboard operations using PowerShell.
        Operations: copy, paste, get
        """
        operation = args["operation"]
        
        log.info(f"📋 OS: Clipboard operation '{operation}'")
        
        try:
            if operation == "copy":
                text = args["text"]
                ps_command = f'Set-Clipboard -Value "{text}"'
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": result.returncode == 0}
            
            elif operation == "get":
                ps_command = 'Get-Clipboard'
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": True, "content": result.stdout.strip()}
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            log.error(f"Clipboard operation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _system_control(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        System-level controls.
        Operations: volume, brightness, network, etc.
        """
        operation = args["operation"]
        
        log.info(f"⚙️ OS: System control '{operation}'")
        
        try:
            if operation == "volume_set":
                level = args["level"]  # 0-100
                ps_command = f'''
                $obj = New-Object -ComObject WScript.Shell
                1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
                1..{level//2} | ForEach-Object {{ $obj.SendKeys([char]175) }}
                '''
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": result.returncode == 0}
            
            elif operation == "get_processes":
                ps_command = 'Get-Process | Select-Object Name, CPU, WorkingSet | ConvertTo-Json'
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": True, "processes": result.stdout}
            
            elif operation == "kill_process":
                process_name = args["process_name"]
                ps_command = f'Stop-Process -Name "{process_name}" -Force'
                result = subprocess.run(
                    [self.shell, "-Command", ps_command],
                    capture_output=True,
                    text=True
                )
                return {"success": result.returncode == 0}
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            log.error(f"System control failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            ps_command = '''
            @{
                OS = (Get-WmiObject Win32_OperatingSystem).Caption
                User = $env:USERNAME
                Computer = $env:COMPUTERNAME
                PowerShellVersion = $PSVersionTable.PSVersion.ToString()
            } | ConvertTo-Json
            '''
            
            result = subprocess.run(
                [self.shell, "-Command", ps_command],
                capture_output=True,
                text=True
            )
            
            return {"success": True, "info": result.stdout}
            
        except Exception as e:
            log.error(f"System info failed: {e}")
            return {"success": False, "error": str(e)}
