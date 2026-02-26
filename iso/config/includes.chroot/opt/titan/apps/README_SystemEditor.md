# TITAN DevHub System Editor

## Overview

The TITAN Development Hub v2.0.0 now includes advanced system-wide file editing capabilities, allowing the application to safely modify any file within the TITAN OS environment based on AI suggestions or user requests.

## Key Features

### 🔧 System File Editing
- **Safe Editing**: Built-in safety checks prevent modification of critical system files
- **Automatic Backups**: Every edit creates a timestamped backup before modification
- **Rollback Support**: Instant rollback to previous versions if needed
- **Syntax Validation**: Python syntax validation for code files
- **Modification History**: Complete audit trail of all system changes

### 🤖 AI-Powered Modifications
- **Command Parsing**: AI responses with `[EDIT:]` and `[MODIFY:]` commands trigger automatic system edits
- **Context-Aware**: AI understands file structure and suggests appropriate modifications
- **Safety Integration**: AI suggestions go through the same safety checks as manual edits

### 🎨 Enhanced GUI
- **System Editor Tab**: Dedicated interface for file editing
- **File Browser**: Browse and select files to edit
- **Live Preview**: Edit files with real-time preview
- **History Viewer**: View and manage modification history
- **One-Click Operations**: Load, edit, backup, and rollback with single clicks

## Safety Mechanisms

### Critical File Protection
The system automatically prevents editing of:
- System binaries and executables
- Configuration files in `/etc/`, `/boot/`, `/sys/`
- Kernel modules and drivers
- Security-critical files

### Backup Strategy
- Automatic backup creation before every edit
- Timestamped backup files in `/opt/titan/apps/backups/`
- Backup retention policy (configurable)
- Easy restoration from any backup point

### Validation Checks
- Python syntax validation for `.py` files
- File permission verification
- Disk space checks before operations
- Atomic write operations to prevent corruption

## Usage Examples

### GUI Usage
1. Launch TITAN DevHub: `python titan_dev_hub.py`
2. Navigate to "System Editor" tab
3. Use "Browse" to select a file or "Scan Files" to see editable files
4. Click "Load File" to load content into the editor
5. Make your changes in the text area
6. Click "Apply Edit" for direct edit or "Backup & Edit" for safe edit with backup
7. View modification history in the history panel
8. Use "Rollback" if needed to revert changes

### CLI Usage
```bash
# Initialize hub in CLI mode
python titan_dev_hub.py --cli

# Interactive commands available:
- edit <file_path>
- scan
- history
- rollback <modification_id>
- backup <file_path>
```

### AI Commands
The AI can generate system modification commands:

```
[EDIT:] file_path=/opt/titan/apps/core/forensic_monitor.py
operation=add_function
content=def new_logging_function():
    """Enhanced logging for forensic monitoring"""
    import logging
    logging.info("Forensic monitor active")
```

```
[MODIFY:] target=gui_update
component=tkinter_interface
change=Add new menu item "System Tools" with submenu options
```

## File Structure

```
/opt/titan/apps/
├── titan_dev_hub.py          # Main application with system editor
├── backups/                  # Automatic backup directory
│   ├── filename_20241201_123456.py.bak
│   └── ...
├── config/
│   └── dev_hub_config.json   # Configuration settings
└── README_SystemEditor.md    # This documentation
```

## Configuration

Edit `/opt/titan/apps/config/dev_hub_config.json` to customize:

```json
{
  "system_editor": {
    "backup_enabled": true,
    "backup_retention_days": 30,
    "auto_validate_syntax": true,
    "allowed_extensions": [".py", ".txt", ".md", ".json"],
    "protected_directories": ["/etc", "/boot", "/sys", "/proc"]
  },
  "ai_integration": {
    "auto_process_commands": true,
    "require_confirmation": true,
    "max_file_size_mb": 10
  }
}
```

## API Reference

### SystemEditor Class

```python
class SystemEditor:
    def edit_file(self, operation: FileEditOperation) -> Tuple[bool, str]
    def is_safe_to_edit(self, file_path: str) -> Tuple[bool, str]
    def create_backup(self, file_path: str) -> str
    def rollback_modification(self, modification_id: str) -> Tuple[bool, str]
    def get_modification_history(self) -> List[Dict]
    def scan_editable_files(self) -> List[str]
```

### FileEditOperation Dataclass

```python
@dataclass
class FileEditOperation:
    file_path: str
    new_content: str
    operation_type: str
    backup: bool = True
    validate_syntax: bool = True
```

## Security Considerations

### Access Control
- Only authorized users can perform system edits
- All modifications are logged with user attribution
- File permissions are respected and preserved

### Audit Trail
- Complete modification history with timestamps
- Before/after file comparisons stored
- User and AI attribution for each change

### Recovery Options
- Multiple rollback points available
- Emergency backup restoration procedures
- System integrity verification tools

## Troubleshooting

### Common Issues

**Edit Failed - Safety Check**
```
Cause: Attempting to edit a protected file
Solution: Choose a different file or modify protection settings
```

**Backup Creation Failed**
```
Cause: Insufficient disk space or permission issues
Solution: Free up disk space or check directory permissions
```

**Syntax Validation Failed**
```
Cause: Python code has syntax errors
Solution: Fix syntax errors before applying edit
```

### Recovery Procedures

1. **Emergency Rollback**: Use the GUI "Rollback" button or CLI `rollback` command
2. **Manual Restoration**: Restore from backup files in `/opt/titan/apps/backups/`
3. **System Check**: Run `python test_system_editor.py` to verify functionality

## Integration with AI

### Command Processing
The system automatically processes AI commands in chat responses:

- `[EDIT:]` - Direct file editing operations
- `[MODIFY:]` - Complex system modifications
- `[TASK:]` - Task creation with system edit components

### Safety Integration
All AI-generated edits go through the same safety checks as manual edits:
- Critical file protection
- Backup creation
- Syntax validation
- User confirmation (when enabled)

## Future Enhancements

### Planned Features
- [ ] Real-time collaboration editing
- [ ] Advanced diff visualization
- [ ] Scheduled system updates
- [ ] Integration with package managers
- [ ] Multi-file batch operations
- [ ] Template-based modifications

### Extensibility
The system is designed for easy extension:
- Plugin architecture for custom validators
- Configurable safety rules
- Custom backup strategies
- Additional file type support

## Support

For issues or questions regarding the System Editor:

1. Check the modification history for recent changes
2. Review the troubleshooting section above
3. Run the test suite: `python test_system_editor.py`
4. Consult the main TITAN DevHub documentation

---

**Version**: 2.0.0  
**Last Updated**: 2024-12-01  
**Compatibility**: TITAN OS 7.6+
