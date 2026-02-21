#!/usr/bin/env python3
"""
TITAN Development Integration Hub
Integrates TITAN OS development with GitHub Copilot/Windsurf and provides chat interface
"""

import os
import sys
import json
import time
import threading
import subprocess
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import hashlib
import uuid
import difflib
import ast

# Add TITAN core to path
TITAN_CORE = Path(__file__).parent / "core"
if TITAN_CORE.exists():
    sys.path.insert(0, str(TITAN_CORE))

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("GUI not available, running in CLI mode")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests module not available, some features limited")

@dataclass
class ChatMessage:
    """Chat message structure"""
    id: str
    role: str  # user, assistant, system
    content: str
    timestamp: float
    metadata: Dict[str, Any] = None

@dataclass
class DevTask:
    """Development task structure"""
    id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed
    priority: str  # low, medium, high, critical
    created_at: float
    completed_at: Optional[float] = None
    assigned_to: str = ""
    files_modified: List[str] = None
    code_changes: str = ""

@dataclass
class CodeSuggestion:
    """Code suggestion from AI"""
    id: str
    file_path: str
    original_code: str
    suggested_code: str
    explanation: str
    confidence: float
    applied: bool = False

@dataclass
class SystemModification:
    """System-wide modification record"""
    id: str
    target_file: str
    modification_type: str  # code, config, gui, system
    description: str
    original_content: str
    modified_content: str
    timestamp: float
    applied: bool = False
    backup_created: bool = False
    risk_level: str = "medium"  # low, medium, high, critical
    requires_restart: bool = False
    dependencies: List[str] = None

@dataclass
class FileEditOperation:
    """File edit operation with safety checks"""
    file_path: str
    operation: str  # insert, replace, delete, append
    line_number: Optional[int]
    content: str
    backup: bool = True
    validate_syntax: bool = True

class SystemEditor:
    """Advanced system file editor with safety checks and rollback capabilities"""
    
    def __init__(self, titan_root: Path):
        self.titan_root = titan_root
        self.backup_dir = titan_root / "backups"
        self.modifications: List[SystemModification] = []
        self.critical_files = {
            "kernel", "bootloader", "init", "systemd", "grub",
            "network", "security", "authentication", "crypto"
        }
        self.backup_dir.mkdir(exist_ok=True)
    
    def is_safe_to_edit(self, file_path: str) -> Tuple[bool, str]:
        """Check if file is safe to edit"""
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return False, "File does not exist"
        
        # Check if it's a critical system file
        file_lower = str(path).lower()
        for critical in self.critical_files:
            if critical in file_lower:
                return False, f"Critical system file detected: {critical}"
        
        # Check file permissions
        if not os.access(path, os.R_OK | os.W_OK):
            return False, "Insufficient file permissions"
        
        # Check if file is binary
        try:
            with open(path, 'rb') as f:
                chunk = f.read(1024)
                if b'\x00' in chunk:
                    return False, "Binary file - editing not supported"
        except Exception:
            return False, "Cannot read file"
        
        return True, "Safe to edit"
    
    def create_backup(self, file_path: str) -> str:
        """Create backup of file before modification"""
        path = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(path, backup_path)
            return str(backup_path)
        except Exception as e:
            raise Exception(f"Failed to create backup: {e}")
    
    def validate_python_syntax(self, code: str) -> Tuple[bool, str]:
        """Validate Python syntax"""
        if not code.strip().endswith('.py') and not code.strip().startswith('import'):
            # Not a Python file or snippet
            return True, "Not a Python file"
        
        try:
            ast.parse(code)
            return True, "Syntax valid"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Parse error: {e}"
    
    def edit_file(self, operation: FileEditOperation) -> Tuple[bool, str]:
        """Perform file edit operation with safety checks"""
        # Safety check
        is_safe, message = self.is_safe_to_edit(operation.file_path)
        if not is_safe:
            return False, f"Safety check failed: {message}"
        
        path = Path(operation.file_path)
        
        # Create backup
        backup_path = ""
        if operation.backup:
            try:
                backup_path = self.create_backup(operation.file_path)
            except Exception as e:
                return False, f"Backup failed: {e}"
        
        try:
            # Read original content
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Perform edit operation
            lines = original_content.split('\n')
            modified_content = original_content
            
            if operation.operation == "insert":
                if operation.line_number is not None:
                    lines.insert(operation.line_number - 1, operation.content)
                    modified_content = '\n'.join(lines)
                else:
                    modified_content += '\n' + operation.content
            
            elif operation.operation == "replace":
                if operation.line_number is not None:
                    if 0 <= operation.line_number - 1 < len(lines):
                        lines[operation.line_number - 1] = operation.content
                        modified_content = '\n'.join(lines)
                    else:
                        return False, f"Line number {operation.line_number} out of range"
                else:
                    # Replace all occurrences
                    modified_content = original_content.replace(operation.content, "")
            
            elif operation.operation == "delete":
                if operation.line_number is not None:
                    if 0 <= operation.line_number - 1 < len(lines):
                        del lines[operation.line_number - 1]
                        modified_content = '\n'.join(lines)
                    else:
                        return False, f"Line number {operation.line_number} out of range"
            
            elif operation.operation == "append":
                modified_content += '\n' + operation.content
            
            # Validate syntax if Python file
            if operation.validate_syntax and path.suffix == '.py':
                is_valid, validation_msg = self.validate_python_syntax(modified_content)
                if not is_valid:
                    return False, f"Syntax validation failed: {validation_msg}"
            
            # Write modified content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            # Record modification
            modification = SystemModification(
                id=str(uuid.uuid4())[:8],
                target_file=operation.file_path,
                modification_type="code",
                description=f"{operation.operation} operation",
                original_content=original_content,
                modified_content=modified_content,
                timestamp=time.time(),
                backup_created=bool(backup_path),
                risk_level="medium"
            )
            self.modifications.append(modification)
            
            return True, f"Successfully edited {operation.file_path}"
            
        except Exception as e:
            # Restore from backup if available
            if backup_path and Path(backup_path).exists():
                try:
                    shutil.copy2(backup_path, path)
                except Exception:
                    pass
            
            return False, f"Edit failed: {e}"
    
    def apply_ai_suggestion(self, suggestion: Dict) -> Tuple[bool, str]:
        """Apply AI-suggested modification"""
        file_path = suggestion.get('file_path')
        modifications = suggestion.get('modifications', [])
        
        if not file_path or not modifications:
            return False, "Invalid suggestion format"
        
        results = []
        for mod in modifications:
            operation = FileEditOperation(
                file_path=file_path,
                operation=mod.get('operation', 'replace'),
                line_number=mod.get('line_number'),
                content=mod.get('content', ''),
                backup=True,
                validate_syntax=True
            )
            
            success, message = self.edit_file(operation)
            results.append((success, message))
        
        # Check if all operations succeeded
        if all(success for success, _ in results):
            return True, "All modifications applied successfully"
        else:
            failed_messages = [msg for success, msg in results if not success]
            return False, f"Some operations failed: {'; '.join(failed_messages)}"
    
    def rollback_modification(self, modification_id: str) -> Tuple[bool, str]:
        """Rollback a specific modification"""
        for mod in self.modifications:
            if mod.id == modification_id and mod.applied:
                try:
                    with open(mod.target_file, 'w', encoding='utf-8') as f:
                        f.write(mod.original_content)
                    mod.applied = False
                    return True, f"Rolled back modification {modification_id}"
                except Exception as e:
                    return False, f"Rollback failed: {e}"
        
        return False, "Modification not found or not applied"
    
    def get_modification_history(self) -> List[SystemModification]:
        """Get history of all modifications"""
        return self.modifications.copy()

class TitanDevHub:
    """Main TITAN Development Integration Hub"""
    
    def __init__(self):
        self.version = "2.0.0"  # Upgraded for system editing capabilities
        self.titan_root = Path(__file__).parent
        self.config_file = self.titan_root / "config" / "dev_hub_config.json"
        self.chat_history: List[ChatMessage] = []
        self.tasks: List[DevTask] = []
        self.suggestions: List[CodeSuggestion] = []
        self.active_session = False
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.git_handler = GitHandler(self.titan_root)
        self.ai_interface = AIInterface(self.config.get("ai", {}))
        self.task_manager = TaskManager()
        self.code_analyzer = CodeAnalyzer(self.titan_root)
        self.system_editor = SystemEditor(self.titan_root)  # NEW: System editor
        
        print(f"TITAN Dev Hub v{self.version} initialized")
        print(f"TITAN Root: {self.titan_root}")
        print(f"GUI Available: {GUI_AVAILABLE}")
        print(f"Requests Available: {REQUESTS_AVAILABLE}")
        print(f"System Editing: ENABLED")  # NEW

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "ai": {
                "provider": "copilot",  # copilot, windsurf, custom
                "api_key": "",
                "model": "gpt-4",
                "max_tokens": 2000,
                "temperature": 0.7
            },
            "git": {
                "auto_commit": True,
                "commit_prefix": "[TITAN-DevHub]",
                "branch": "main"
            },
            "ui": {
                "theme": "dark",
                "font_size": 12,
                "window_size": [1200, 800]
            },
            "features": {
                "auto_suggest": True,
                "code_review": True,
                "task_tracking": True,
                "chat_history": True
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey not in loaded_config[key]:
                                loaded_config[key][subkey] = subvalue
                return loaded_config
            except Exception as e:
                print(f"Error loading config: {e}")
        
        # Create default config
        self.config_file.parent.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config

    def start_session(self):
        """Start development session"""
        self.active_session = True
        session_id = str(uuid.uuid4())[:8]
        
        # Add system message
        self._add_message("system", f"TITAN Dev Hub session started (ID: {session_id})")
        
        # Analyze current state
        analysis = self.code_analyzer.analyze_project()
        self._add_message("system", f"Project analysis complete: {analysis['summary']}")
        
        return session_id

    def _add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to chat history"""
        message = ChatMessage(
            id=str(uuid.uuid4())[:8],
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        self.chat_history.append(message)
        
        # Keep history manageable
        if len(self.chat_history) > 1000:
            self.chat_history = self.chat_history[-500:]

    def chat(self, user_input: str) -> str:
        """Process chat message and get AI response"""
        if not self.active_session:
            return "Please start a session first"
        
        # Add user message
        self._add_message("user", user_input)
        
        # Get context from TITAN project
        context = self._get_context_for_ai()
        
        # Get AI response
        response = self.ai_interface.chat(user_input, context)
        
        # Add assistant response
        self._add_message("assistant", response)
        
        # Process any commands in response
        self._process_ai_commands(response)
        
        return response

    def _get_context_for_ai(self) -> Dict:
        """Get relevant context for AI"""
        return {
            "titan_version": "7.6",
            "current_tasks": [t.title for t in self.tasks if t.status == "in_progress"],
            "recent_files": self.code_analyzer.get_recent_files(),
            "git_status": self.git_handler.get_status(),
            "project_stats": self.code_analyzer.get_project_stats()
        }

    def _process_ai_commands(self, response: str):
        """Process special commands from AI response"""
        if "[TASK:" in response:
            # Extract task creation
            try:
                task_data = response.split("[TASK:")[1].split("]")[0]
                title, desc = task_data.split("|", 1)
                self.create_task(title.strip(), desc.strip())
            except:
                pass
        
        # NEW: Process system modification commands
        if "[EDIT:" in response:
            try:
                edit_data = response.split("[EDIT:")[1].split("]")[0]
                self._process_edit_command(edit_data)
            except:
                pass
        
        if "[MODIFY:" in response:
            try:
                modify_data = response.split("[MODIFY:")[1].split("]")[0]
                self._process_modify_command(modify_data)
            except:
                pass
    
    def _process_edit_command(self, edit_data: str):
        """Process file edit command from AI"""
        try:
            # Parse edit data: file_path|operation|line_number|content
            parts = edit_data.split("|", 3)
            if len(parts) >= 3:
                file_path = parts[0].strip()
                operation = parts[1].strip()
                line_number = int(parts[2]) if parts[2].isdigit() else None
                content = parts[3].strip() if len(parts) > 3 else ""
                
                success = self.edit_system_file(file_path, operation, content, line_number)
                if success:
                    self._add_message("system", f"Successfully edited {file_path}")
                else:
                    self._add_message("system", f"Failed to edit {file_path}")
        except Exception as e:
            self._add_message("system", f"Edit command error: {e}")
    
    def _process_modify_command(self, modify_data: str):
        """Process system modification command from AI"""
        try:
            # Parse modify data: file_path|description|modifications_json
            parts = modify_data.split("|", 2)
            if len(parts) >= 2:
                file_path = parts[0].strip()
                description = parts[1].strip()
                modifications_json = parts[2].strip() if len(parts) > 2 else "[]"
                
                import json
                modifications = json.loads(modifications_json)
                
                suggestion = {
                    'file_path': file_path,
                    'description': description,
                    'modifications': modifications
                }
                
                success, message = self.apply_ai_suggestion(suggestion)
                self._add_message("system", f"AI modification: {message}")
        except Exception as e:
            self._add_message("system", f"Modify command error: {e}")
    
    def edit_system_file(self, file_path: str, operation: str, content: str = "", 
                        line_number: Optional[int] = None) -> bool:
        """Edit a system file with safety checks"""
        edit_op = FileEditOperation(
            file_path=file_path,
            operation=operation,
            line_number=line_number,
            content=content,
            backup=True,
            validate_syntax=True
        )
        
        success, message = self.system_editor.edit_file(edit_op)
        self._add_message("system", f"File edit: {message}")
        
        return success
    
    def apply_ai_suggestion(self, suggestion: Dict) -> Tuple[bool, str]:
        """Apply AI-suggested system modification"""
        return self.system_editor.apply_ai_suggestion(suggestion)
    
    def rollback_modification(self, modification_id: str) -> Tuple[bool, str]:
        """Rollback a system modification"""
        return self.system_editor.rollback_modification(modification_id)
    
    def get_modification_history(self) -> List[SystemModification]:
        """Get history of all system modifications"""
        return self.system_editor.get_modification_history()
    
    def scan_editable_files(self, directory: str = None) -> List[Dict]:
        """Scan for editable files in the system"""
        if directory is None:
            directory = str(self.titan_root)
        
        editable_files = []
        scan_path = Path(directory)
        
        for file_path in scan_path.rglob("*"):
            if file_path.is_file():
                # Check if file is editable
                is_safe, message = self.system_editor.is_safe_to_edit(str(file_path))
                
                file_info = {
                    'path': str(file_path),
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime,
                    'editable': is_safe,
                    'reason': message
                }
                
                editable_files.append(file_info)
        
        return editable_files

    def create_task(self, title: str, description: str, priority: str = "medium") -> str:
        """Create a new development task"""
        task = DevTask(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            status="pending",
            priority=priority,
            created_at=time.time()
        )
        
        self.tasks.append(task)
        self._add_message("system", f"Task created: {title}")
        
        return task.id

    def get_tasks(self, status: str = None) -> List[DevTask]:
        """Get tasks, optionally filtered by status"""
        if status:
            return [t for t in self.tasks if t.status == status]
        return self.tasks

    def analyze_code(self, file_path: str) -> Dict:
        """Analyze code file and get suggestions"""
        return self.code_analyzer.analyze_file(file_path)

    def apply_suggestion(self, suggestion_id: str) -> bool:
        """Apply a code suggestion"""
        for suggestion in self.suggestions:
            if suggestion.id == suggestion_id:
                success = self.code_analyzer.apply_suggestion(suggestion)
                if success:
                    suggestion.applied = True
                    self._add_message("system", f"Applied suggestion to {suggestion.file_path}")
                return success
        return False

    def commit_changes(self, message: str = None) -> bool:
        """Commit current changes"""
        if not message:
            message = f"Automated commit from TITAN Dev Hub"
        
        return self.git_handler.commit(message)

    def get_chat_history(self, limit: int = 50) -> List[ChatMessage]:
        """Get chat history"""
        return self.chat_history[-limit:]

    def save_session(self):
        """Save current session state"""
        session_data = {
            "chat_history": [asdict(m) for m in self.chat_history],
            "tasks": [asdict(t) for t in self.tasks],
            "suggestions": [asdict(s) for s in self.suggestions],
            "timestamp": time.time()
        }
        
        session_file = self.titan_root / "sessions" / f"session_{int(time.time())}.json"
        session_file.parent.mkdir(exist_ok=True)
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return str(session_file)

class GitHandler:
    """Handle Git operations"""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
    
    def get_status(self) -> Dict:
        """Get Git status"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            modified = [line for line in lines if line.strip()]
            
            return {
                "clean": len(modified) == 0,
                "modified_files": len(modified),
                "files": modified
            }
        except Exception as e:
            return {"error": str(e)}
    
    def commit(self, message: str) -> bool:
        """Commit changes"""
        try:
            # Add all changes
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            
            # Commit
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)
            
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception:
            return False

class AIInterface:
    """Interface to AI services (Copilot/Windsurf)"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.provider = config.get("provider", "copilot")
    
    def chat(self, message: str, context: Dict) -> str:
        """Chat with AI and return response"""
        # Simulate AI response for now
        # In real implementation, this would integrate with Copilot/Windsurf API
        
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        
        # Simulate processing
        time.sleep(0.5)
        
        # Generate contextual response with system editing capabilities
        message_lower = message.lower()
        
        if "edit" in message_lower or "modify" in message_lower or "change" in message_lower:
            return f"I can help you edit system files. Please specify:\n" \
                   f"• Which file to edit\n" \
                   f"• What changes to make\n" \
                   f"• Any specific line numbers\n\n" \
                   f"Example: 'Edit core/forensic_monitor.py to add logging'\n" \
                   f"I'll then generate the appropriate [EDIT:] command."
        
        elif "improve" in message_lower or "enhance" in message_lower or "upgrade" in message_lower:
            return f"I can analyze and improve TITAN OS components. Tell me:\n" \
                   f"• Which module to improve\n" \
                   f"• What improvements you want\n" \
                   f"• Any specific requirements\n\n" \
                   f"I'll generate a [MODIFY:] command with the changes."
        
        elif "gui" in message_lower or "interface" in message_lower:
            return f"I can help modify GUI components. I can:\n" \
                   f"• Update Tkinter interfaces\n" \
                   f"• Add new UI elements\n" \
                   f"• Modify layouts and styling\n" \
                   f"• Update event handlers\n\n" \
                   f"Specify which GUI file you want to modify."
        
        elif "add feature" in message_lower or "new feature" in message_lower:
            return f"I can help add new features to TITAN OS. Please provide:\n" \
                   f"• Feature description\n" \
                   f"• Target module/file\n" \
                   f"• Implementation requirements\n\n" \
                   f"I'll generate the code modifications needed."
        
        elif "fix bug" in message_lower or "bug" in message_lower:
            return f"I can help fix bugs in TITAN OS. Tell me:\n" \
                   f"• What bug you're experiencing\n" \
                   f"• Which file/module is affected\n" \
                   f"• Error messages or symptoms\n\n" \
                   f"I'll analyze and provide a fix."
        
        elif "task" in message_lower:
            return "I can help you create and manage tasks. Use the task panel or type 'create task: [title] | [description]'"
        
        elif "code" in message_lower or "analyze" in message_lower:
            return "I can analyze your TITAN code and provide suggestions. Select a file and click 'Analyze Code'."
        
        elif "git" in message_lower:
            return "I can help with Git operations. Current status shows some files may need committing."
        
        elif "rollback" in message_lower or "revert" in message_lower:
            return "I can rollback previous modifications. Use 'rollback [modification_id]' or check the modification history."
        
        else:
            return f"I understand you're working on: {message}\n\n" \
                   f"Available capabilities:\n" \
                   f"• Edit/modify any system file\n" \
                   f"• Update GUI components\n" \
                   f"• Add new features\n" \
                   f"• Fix bugs\n" \
                   f"• Analyze code\n" \
                   f"• Manage tasks\n" \
                   f"• Git operations\n\n" \
                   f"Context:\n{context_str}\n\n" \
                   f"What would you like me to help you with?"

class TaskManager:
    """Manage development tasks"""
    
    def __init__(self):
        self.tasks = []
    
    def create_task(self, title: str, description: str) -> Dict:
        """Create new task"""
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "description": description,
            "status": "pending",
            "created_at": time.time()
        }
        self.tasks.append(task)
        return task

class CodeAnalyzer:
    """Analyze TITAN codebase"""
    
    def __init__(self, titan_root: Path):
        self.titan_root = titan_root
    
    def analyze_project(self) -> Dict:
        """Analyze entire project"""
        python_files = list(self.titan_root.rglob("*.py"))
        core_files = [f for f in python_files if "core" in str(f)]
        
        return {
            "total_python_files": len(python_files),
            "core_files": len(core_files),
            "summary": f"Found {len(python_files)} Python files, {len(core_files)} in core"
        }
    
    def get_recent_files(self, limit: int = 10) -> List[str]:
        """Get recently modified files"""
        files = []
        for py_file in self.titan_root.rglob("*.py"):
            try:
                mtime = py_file.stat().st_mtime
                files.append((str(py_file), mtime))
            except:
                continue
        
        files.sort(key=lambda x: x[1], reverse=True)
        return [f[0] for f in files[:limit]]
    
    def get_project_stats(self) -> Dict:
        """Get project statistics"""
        stats = {
            "python_files": 0,
            "total_lines": 0,
            "core_modules": 0
        }
        
        for py_file in self.titan_root.rglob("*.py"):
            stats["python_files"] += 1
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    stats["total_lines"] += lines
                    
                    if "core" in str(py_file):
                        stats["core_modules"] += 1
            except:
                continue
        
        return stats
    
    def analyze_file(self, file_path: str) -> Dict:
        """Analyze specific file"""
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Simple analysis
            imports = []
            functions = []
            classes = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
                elif line.startswith('def '):
                    functions.append(line.split('(')[0].replace('def ', ''))
                elif line.startswith('class '):
                    classes.append(line.split('(')[0].replace('class ', ''))
            
            return {
                "file_path": str(path),
                "lines": len(lines),
                "imports": imports[:10],  # Limit
                "functions": functions[:10],
                "classes": classes[:10],
                "suggestions": self._generate_suggestions(content)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_suggestions(self, content: str) -> List[str]:
        """Generate code suggestions"""
        suggestions = []
        
        if "TODO" in content:
            suggestions.append("Found TODO items - consider addressing them")
        
        if len(content.split('\n')) > 500:
            suggestions.append("Large file - consider splitting into modules")
        
        if "print(" in content:
            suggestions.append("Consider using logging instead of print statements")
        
        return suggestions
    
    def apply_suggestion(self, suggestion) -> bool:
        """Apply code suggestion"""
        # Placeholder for suggestion application
        return True

class TitanDevGUI:
    """GUI for TITAN Development Hub"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TITAN Development Hub")
        self.root.geometry("1200x800")
        
        # Initialize hub
        self.hub = TitanDevHub()
        
        # Setup UI
        self.setup_ui()
        
        # Start session
        self.hub.start_session()
        self.update_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Chat
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(left_frame, text="Chat Interface", font=("Arial", 12, "bold")).pack()
        
        # Chat history
        self.chat_display = scrolledtext.ScrolledText(
            left_frame, 
            height=20, 
            wrap=tk.WORD
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(5, 5))
        
        # Input frame
        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill=tk.X)
        
        self.chat_input = ttk.Entry(input_frame)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_input.bind("<Return>", lambda e: self.send_message())
        
        ttk.Button(input_frame, text="Send", command=self.send_message).pack(side=tk.RIGHT)
        
        # Right panel - Tasks and Tools
        right_frame = ttk.Frame(main_frame, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Notebook for tabs
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tasks tab
        tasks_frame = ttk.Frame(notebook)
        notebook.add(tasks_frame, text="Tasks")
        
        ttk.Button(tasks_frame, text="Create Task", command=self.create_task_dialog).pack(pady=5)
        
        self.tasks_listbox = tk.Listbox(tasks_frame, height=10)
        self.tasks_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # System Editor tab
        editor_tab = ttk.Frame(notebook)
        notebook.add(editor_tab, text="System Editor")
        
        # File selection
        file_frame = ttk.LabelFrame(editor_tab, text="File Selection", padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        file_input_frame = ttk.Frame(file_frame)
        file_input_frame.pack(fill=tk.X)
        
        ttk.Label(file_input_frame, text="File:").pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_input_frame, textvariable=self.file_var, width=50)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(file_input_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_input_frame, text="Scan Files", command=self.scan_files).pack(side=tk.LEFT, padx=5)
        
        # Edit content
        edit_frame = ttk.LabelFrame(editor_tab, text="Edit Content", padding="10")
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.edit_text = scrolledtext.ScrolledText(edit_frame, height=12)
        self.edit_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Edit buttons
        edit_button_frame = ttk.Frame(edit_frame)
        edit_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(edit_button_frame, text="Load File", command=self.load_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(edit_button_frame, text="Apply Edit", command=self.apply_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(edit_button_frame, text="Backup & Edit", command=self.backup_and_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(edit_button_frame, text="Rollback", command=self.rollback_last).pack(side=tk.LEFT, padx=5)
        
        # Modification History
        history_frame = ttk.LabelFrame(editor_tab, text="Modification History", padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.history_text = scrolledtext.ScrolledText(history_frame, height=8)
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Button(history_frame, text="Refresh History", command=self.refresh_history).pack(pady=5)
        
        # Code Analysis tab
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Code Analysis")
        
        ttk.Button(analysis_frame, text="Select File", command=self.select_file).pack(pady=5)
        
        self.analysis_text = scrolledtext.ScrolledText(analysis_frame, height=15)
        self.analysis_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Git tab
        git_frame = ttk.Frame(notebook)
        notebook.add(git_frame, text="Git")
        
        self.git_status_text = scrolledtext.ScrolledText(git_frame, height=15)
        self.git_status_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Button(git_frame, text="Commit Changes", command=self.commit_changes).pack(pady=5)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def send_message(self):
        """Send chat message"""
        message = self.chat_input.get().strip()
        if not message:
            return
        
        self.chat_input.delete(0, tk.END)
        
        # Display user message
        self.chat_display.insert(tk.END, f"You: {message}\n\n")
        self.chat_display.see(tk.END)
        
        # Get response
        response = self.hub.chat(message)
        
        # Display response
        self.chat_display.insert(tk.END, f"Assistant: {response}\n\n")
        self.chat_display.see(tk.END)
        
        self.update_ui()
    
    def create_task_dialog(self):
        """Show task creation dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Task")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Title:").pack(pady=5)
        title_entry = ttk.Entry(dialog, width=50)
        title_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Description:").pack(pady=5)
        desc_text = scrolledtext.ScrolledText(dialog, height=8)
        desc_text.pack(pady=5)
        
        def create_task():
            title = title_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            
            if title and description:
                self.hub.create_task(title, description)
                self.update_ui()
                dialog.destroy()
        
        ttk.Button(dialog, text="Create", command=create_task).pack(pady=10)
    
    def select_file(self):
        """Select file for analysis"""
        file_path = filedialog.askopenfilename(
            title="Select Python File",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if file_path:
            analysis = self.hub.analyze_code(file_path)
            
            self.analysis_text.delete("1.0", tk.END)
            
            if "error" in analysis:
                self.analysis_text.insert(tk.END, f"Error: {analysis['error']}")
            else:
                self.analysis_text.insert(tk.END, f"File: {analysis['file_path']}\n")
                self.analysis_text.insert(tk.END, f"Lines: {analysis['lines']}\n")
                self.analysis_text.insert(tk.END, f"Functions: {', '.join(analysis['functions'])}\n")
                self.analysis_text.insert(tk.END, f"Classes: {', '.join(analysis['classes'])}\n")
                self.analysis_text.insert(tk.END, f"\nSuggestions:\n")
                for suggestion in analysis.get('suggestions', []):
                    self.analysis_text.insert(tk.END, f"• {suggestion}\n")
    
    def commit_changes(self):
        """Commit Git changes"""
        success = self.hub.commit_changes()
        
        if success:
            messagebox.showinfo("Success", "Changes committed successfully")
        else:
            messagebox.showerror("Error", "Failed to commit changes")
        
        self.update_ui()
    
    def update_ui(self):
        """Update UI elements"""
        # Update tasks
        self.tasks_listbox.delete(0, tk.END)
        for task in self.hub.get_tasks():
            status_symbol = "✓" if task.status == "completed" else "○"
            self.tasks_listbox.insert(tk.END, f"{status_symbol} {task.title} ({task.status})")
        
        # Update Git status
        git_status = self.hub.git_handler.get_status()
        self.git_status_text.delete("1.0", tk.END)
        
        if "error" in git_status:
            self.git_status_text.insert(tk.END, f"Error: {git_status['error']}")
        else:
            self.git_status_text.insert(tk.END, f"Status: {'Clean' if git_status['clean'] else 'Modified'}\n")
            self.git_status_text.insert(tk.END, f"Modified files: {git_status['modified_files']}\n\n")
            for file in git_status.get('files', []):
                self.git_status_text.insert(tk.END, f"  {file}\n")
    
    def refresh_history(self):
        """Refresh modification history"""
        try:
            history = self.hub.get_modification_history()
            self.history_text.delete(1.0, tk.END)
            
            if not history:
                self.history_text.insert(tk.END, "No modifications recorded yet.\n")
                return
            
            self.history_text.insert(tk.END, "=== MODIFICATION HISTORY ===\n\n")
            
            for i, mod in enumerate(history, 1):
                self.history_text.insert(tk.END, f"Modification #{i}\n")
                self.history_text.insert(tk.END, f"ID: {mod['id']}\n")
                self.history_text.insert(tk.END, f"File: {mod['file_path']}\n")
                self.history_text.insert(tk.END, f"Operation: {mod['operation']}\n")
                self.history_text.insert(tk.END, f"Timestamp: {mod['timestamp']}\n")
                self.history_text.insert(tk.END, f"Status: {mod['status']}\n")
                self.history_text.insert(tk.END, f"Backup: {mod['backup_path']}\n")
                self.history_text.insert(tk.END, "-" * 50 + "\n")
                
        except Exception as e:
            self.history_text.delete(1.0, tk.END)
            self.history_text.insert(tk.END, f"Error refreshing history: {str(e)}\n")
    
    def browse_file(self):
        """Browse for file to edit"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Select File to Edit",
            filetypes=[
                ("Python Files", "*.py"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            self.file_var.set(filename)
    
    def scan_files(self):
        """Scan for editable files"""
        try:
            editable_files = self.hub.scan_editable_files()
            
            # Create a simple dialog to show files
            dialog = tk.Toplevel(self.root)
            dialog.title("Editable Files")
            dialog.geometry("600x400")
            
            text_widget = scrolledtext.ScrolledText(dialog)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget.insert(tk.END, f"Found {len(editable_files)} editable files:\n\n")
            
            for file_path in editable_files:
                text_widget.insert(tk.END, f"• {file_path}\n")
            
            ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=5)
            
        except Exception as e:
            messagebox.showerror("Scan Error", f"Error scanning files: {str(e)}")
    
    def load_file(self):
        """Load file content into editor"""
        file_path = self.file_var.get().strip()
        
        if not file_path:
            messagebox.showwarning("No File", "Please select a file to load.")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.edit_text.delete(1.0, tk.END)
            self.edit_text.insert(tk.END, content)
            
            self.add_chat_message(f"Loaded file: {file_path}", "system")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Error loading file: {str(e)}")
    
    def apply_edit(self):
        """Apply edit to file"""
        file_path = self.file_var.get().strip()
        content = self.edit_text.get(1.0, tk.END).strip()
        
        if not file_path:
            messagebox.showwarning("No File", "Please select a file to edit.")
            return
        
        try:
            success, message = self.hub.edit_system_file(file_path, content)
            
            if success:
                self.add_chat_message(f"Successfully edited: {file_path}", "system")
                self.refresh_history()
            else:
                messagebox.showerror("Edit Failed", f"Failed to edit file: {message}")
                
        except Exception as e:
            messagebox.showerror("Edit Error", f"Error editing file: {str(e)}")
    
    def backup_and_edit(self):
        """Create backup and then edit file"""
        file_path = self.file_var.get().strip()
        content = self.edit_text.get(1.0, tk.END).strip()
        
        if not file_path:
            messagebox.showwarning("No File", "Please select a file to edit.")
            return
        
        try:
            # Force backup creation
            operation = FileEditOperation(
                file_path=file_path,
                new_content=content,
                operation_type="edit",
                backup=True
            )
            
            success, message = self.hub.system_editor.edit_file(operation)
            
            if success:
                self.add_chat_message(f"Successfully edited with backup: {file_path}", "system")
                self.refresh_history()
            else:
                messagebox.showerror("Edit Failed", f"Failed to edit file: {message}")
                
        except Exception as e:
            messagebox.showerror("Edit Error", f"Error editing file: {str(e)}")
    
    def rollback_last(self):
        """Rollback the last modification"""
        try:
            history = self.hub.get_modification_history()
            
            if not history:
                messagebox.showinfo("No History", "No modifications to rollback.")
                return
            
            last_mod = history[-1]
            
            result = messagebox.askyesno(
                "Confirm Rollback",
                f"Rollback last modification to {last_mod['file_path']}?\n\n"
                f"Operation: {last_mod['operation']}\n"
                f"Timestamp: {last_mod['timestamp']}"
            )
            
            if result:
                success, message = self.hub.rollback_modification(last_mod['id'])
                
                if success:
                    self.add_chat_message(f"Successfully rolled back: {last_mod['file_path']}", "system")
                    self.refresh_history()
                else:
                    messagebox.showerror("Rollback Failed", f"Failed to rollback: {message}")
                    
        except Exception as e:
            messagebox.showerror("Rollback Error", f"Error during rollback: {str(e)}")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

def main():
    """Main entry point"""
    print("TITAN Development Hub Starting...")
    
    if GUI_AVAILABLE:
        # Run GUI
        app = TitanDevGUI()
        app.run()
    else:
        # Run CLI
        hub = TitanDevHub()
        hub.start_session()
        
        print("\nCLI Mode - Type 'quit' to exit")
        print("Commands: 'tasks', 'analyze <file>', 'commit', 'status'")
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'tasks':
                    tasks = hub.get_tasks()
                    for task in tasks:
                        print(f"• {task.title} ({task.status})")
                elif user_input.startswith('analyze '):
                    file_path = user_input[9:].strip()
                    analysis = hub.analyze_code(file_path)
                    print(json.dumps(analysis, indent=2))
                elif user_input.lower() == 'commit':
                    success = hub.commit_changes()
                    print("Committed" if success else "Failed to commit")
                elif user_input.lower() == 'status':
                    print(f"Active: {hub.active_session}")
                    print(f"Tasks: {len(hub.tasks)}")
                    print(f"Messages: {len(hub.chat_history)}")
                else:
                    response = hub.chat(user_input)
                    print(f"\nAssistant: {response}")
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        # Save session
        session_file = hub.save_session()
        print(f"\nSession saved: {session_file}")

if __name__ == "__main__":
    main()
