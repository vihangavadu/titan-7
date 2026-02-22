# TITAN Development Hub

A comprehensive development integration hub for TITAN OS that provides chat interface, task management, code analysis, and AI-powered assistance with GitHub Copilot/Windsurf integration.

## Features

### 🤖 AI Integration
- **Chat Interface**: Natural language interaction with AI assistants
- **GitHub Copilot Integration**: Direct integration with GitHub Copilot API
- **Windsurf Support**: Compatible with Windsurf AI platform
- **Context-Aware Responses**: AI understands TITAN OS codebase and current context

### 💻 Code Management
- **Code Analysis**: Analyze Python files for improvements and suggestions
- **Real-time Suggestions**: Get AI-powered code suggestions
- **Git Integration**: Built-in Git operations and version control
- **File Monitoring**: Track changes in TITAN core modules

### 📋 Task Management
- **Task Creation**: Create and track development tasks
- **Priority Management**: Set task priorities (Critical, High, Medium, Low)
- **Status Tracking**: Monitor task progress (Pending, In Progress, Completed)
- **Auto-Assignment**: Intelligent task assignment based on context

### 🖥️ User Interface
- **GUI Mode**: Full-featured graphical interface (Tkinter-based)
- **CLI Mode**: Command-line interface for server environments
- **Dark Theme**: Easy-on-the-eyes dark interface theme
- **Responsive Design**: Adapts to different screen sizes

## Installation

### Prerequisites
- Python 3.7 or higher
- Git (for version control features)
- TITAN OS development environment

### Setup

1. **Clone or navigate to TITAN directory**:
   ```bash
   cd /opt/titan  # or your TITAN installation path
   ```

2. **Install dependencies**:
   ```bash
   python3 -m pip install -r apps/requirements.txt --user
   ```

3. **Make launchers executable** (Linux/macOS):
   ```bash
   chmod +x apps/launch_dev_hub.sh
   ```

## Usage

### Quick Start

#### GUI Mode (Recommended)
```bash
# Linux/macOS
./apps/launch_dev_hub.sh

# Windows
apps\launch_dev_hub.bat
```

#### CLI Mode
```bash
# Force CLI mode
./apps/launch_dev_hub.sh --cli

# Or directly
python3 apps/titan_dev_hub.py
```

### Command Line Options
```bash
--cli         Force CLI mode
--gui         Force GUI mode (default)
--debug       Enable debug logging
--session ID  Load specific session
--help        Show help message
```

### GUI Interface

The GUI consists of three main panels:

1. **Chat Interface** (Left)
   - Interactive chat with AI assistant
   - Full chat history
   - Real-time responses

2. **Tasks Panel** (Right - Tasks Tab)
   - View all development tasks
   - Create new tasks with priority
   - Track task status

3. **Code Analysis** (Right - Analysis Tab)
   - Select files for analysis
   - View code statistics
   - Get improvement suggestions

4. **Git Operations** (Right - Git Tab)
   - View Git status
   - Commit changes
   - Track file modifications

### CLI Commands

In CLI mode, you can use these commands:

- `tasks` - List all tasks
- `analyze <file>` - Analyze a specific file
- `commit` - Commit current changes
- `status` - Show current status
- `quit` - Exit the application

## Configuration

The configuration file is located at:
```
/opt/titan/config/dev_hub_config.json
```

### Key Configuration Options

#### AI Settings
```json
{
  "ai": {
    "provider": "copilot",        // copilot, windsurf, custom
    "api_key": "",                // Your API key
    "model": "gpt-4",             // AI model to use
    "max_tokens": 2000,           // Maximum response tokens
    "temperature": 0.7            // Response randomness
  }
}
```

#### Git Settings
```json
{
  "git": {
    "auto_commit": true,          // Auto-commit changes
    "commit_prefix": "[TITAN-DevHub]",
    "branch": "main",             // Default branch
    "auto_push": false            // Auto-push to remote
  }
}
```

#### UI Settings
```json
{
  "ui": {
    "theme": "dark",              // dark, light
    "font_size": 12,              // UI font size
    "window_size": [1200, 800],   // Window dimensions
    "auto_save": true             // Auto-save sessions
  }
}
```

## AI Integration Setup

### GitHub Copilot
1. Install GitHub Copilot extension in your IDE
2. Authenticate with GitHub
3. Set `provider: "copilot"` in config
4. Add your Copilot API key if required

### Windsurf
1. Set up Windsurf account
2. Configure `provider: "windsurf"` in config
3. Add Windsurf API credentials

### Custom AI Provider
1. Set `provider: "custom"` in config
2. Configure API endpoint and authentication
3. Ensure compatibility with OpenAI API format

## Development Workflow

### 1. Start Development Session
```bash
./launch_dev_hub.sh
```

### 2. Analyze Current State
The hub automatically analyzes:
- Current Git status
- Modified files
- Active tasks
- Project statistics

### 3. Chat with AI Assistant
Ask questions like:
- "What needs to be implemented for V7.7?"
- "Analyze the fingerprint manager"
- "Create task: Fix canvas detection"
- "Review my recent changes"

### 4. Manage Tasks
- Create tasks from AI suggestions
- Set priorities and track progress
- Auto-generate commit messages

### 5. Code Analysis
- Select files for detailed analysis
- Get improvement suggestions
- Apply AI-generated fixes

### 6. Git Operations
- Review changes before committing
- Auto-generate commit messages
- Track version history

## Advanced Features

### Session Management
- Automatic session saving
- Session history tracking
- Export/import sessions

### Code Suggestions
- Real-time code analysis
- AI-powered improvements
- Automatic refactoring suggestions

### Project Analytics
- Code quality metrics
- Development velocity tracking
- Task completion statistics

### Integration with TITAN Core
The hub integrates with TITAN OS core modules:
- `bug_patch_bridge.py` - Patch management
- `forensic_monitor.py` - System monitoring
- `lucid_vpn.py` - VPN management
- `location_spoofer.py` - Location spoofing
- And more...

## Troubleshooting

### Common Issues

#### GUI Not Available
```bash
# Install tkinter (Ubuntu/Debian)
sudo apt-get install python3-tk

# Or use CLI mode
./launch_dev_hub.sh --cli
```

#### Permission Denied
```bash
# Make launchers executable
chmod +x apps/launch_dev_hub.sh

# Or run with Python directly
python3 apps/titan_dev_hub.py
```

#### Dependencies Missing
```bash
# Install all dependencies
python3 -m pip install -r apps/requirements.txt --user

# Or install individually
python3 -m pip install requests gitpython black
```

#### Git Issues
```bash
# Initialize Git repository
cd /opt/titan
git init
git add .
git commit -m "Initial commit"
```

### Debug Mode
Enable debug logging for troubleshooting:
```bash
./launch_dev_hub.sh --debug
```

Check logs in:
- Console output
- Session files in `/opt/titan/sessions/`
- TITAN logs in `/opt/titan/logs/`

## Contributing

To contribute to the TITAN Development Hub:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the hub
5. Submit a pull request

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd titan-7

# Install in development mode
python3 -m pip install -e .

# Run tests
python3 -m pytest tests/
```

## API Reference

### Main Classes

#### `TitanDevHub`
Main application class that coordinates all components.

#### `AIInterface`
Handles communication with AI providers.

#### `CodeAnalyzer`
Analyzes Python files and generates suggestions.

#### `TaskManager`
Manages development tasks and priorities.

#### `GitHandler`
Handles Git operations and version control.

### Key Methods

```python
# Chat with AI
response = hub.chat("Analyze the fingerprint manager")

# Create task
task_id = hub.create_task("Fix bug", "Description", "high")

# Analyze code
analysis = hub.analyze_code("core/fingerprint_manager.py")

# Commit changes
success = hub.commit_changes("Implemented feature X")
```

## License

This project is part of TITAN OS and follows the same licensing terms.

## Support

For support and questions:
- Check the troubleshooting section
- Review session logs
- Create issues in the repository
- Contact the TITAN development team

---

**TITAN Development Hub** - Empowering TITAN OS development with AI assistance
