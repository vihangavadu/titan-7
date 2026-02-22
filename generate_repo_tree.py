#!/usr/bin/env python3
"""
Generate comprehensive Titan OS repository tree for AI agent deep analysis.
Includes every file, folder, subfolder, script, and artifact.
"""

import os
from pathlib import Path

def generate_tree(directory, prefix="", output_lines=None, max_depth=None, current_depth=0):
    """Generate tree structure recursively."""
    if output_lines is None:
        output_lines = []
    
    if max_depth is not None and current_depth >= max_depth:
        return output_lines
    
    try:
        items = sorted(os.listdir(directory), key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower()))
    except PermissionError:
        return output_lines
    
    # Filter out .git objects to keep tree readable
    if directory.endswith('.git'):
        items = [i for i in items if i not in ['objects', 'logs'] or current_depth < 2]
    
    for i, item in enumerate(items):
        item_path = os.path.join(directory, item)
        is_last = (i == len(items) - 1)
        
        # Tree characters
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "
        
        # Add directory indicator
        display_name = f"{item}/" if os.path.isdir(item_path) else item
        
        # Add file size for files
        size_info = ""
        if os.path.isfile(item_path):
            try:
                size = os.path.getsize(item_path)
                if size > 1024*1024:
                    size_info = f" ({size/(1024*1024):.1f} MB)"
                elif size > 1024:
                    size_info = f" ({size/1024:.1f} KB)"
                elif size > 0:
                    size_info = f" ({size} bytes)"
            except:
                pass
        
        output_lines.append(f"{prefix}{connector}{display_name}{size_info}")
        
        # Recurse into directories
        if os.path.isdir(item_path):
            generate_tree(item_path, prefix + extension, output_lines, max_depth, current_depth + 1)
    
    return output_lines

def main():
    root = Path(__file__).parent
    
    print("Generating Titan OS repository tree...")
    
    output = [
        "# TITAN OS V7.0 SINGULARITY - COMPLETE REPOSITORY TREE",
        "",
        "**Generated for AI Agent Deep Analysis**",
        "This tree includes every file, folder, script, and artifact in the Titan OS repository.",
        "",
        "```",
        "titan-7/"
    ]
    
    tree_lines = generate_tree(str(root))
    output.extend(tree_lines)
    output.append("```")
    
    # Add statistics
    total_files = sum(1 for line in tree_lines if not line.strip().endswith('/'))
    total_dirs = sum(1 for line in tree_lines if line.strip().endswith('/'))
    
    output.extend([
        "",
        "## Repository Statistics",
        f"- **Total Directories:** {total_dirs}",
        f"- **Total Files:** {total_files}",
        f"- **Total Items:** {total_files + total_dirs}",
        "",
        "## Key Directories",
        "- `iso/config/includes.chroot/opt/titan/` - Core Titan OS modules (73 Python modules)",
        "- `iso/config/includes.chroot/opt/titan/apps/` - Trinity GUI applications",
        "- `iso/config/includes.chroot/etc/` - System configuration files",
        "- `scripts/` - Build and deployment scripts",
        "- `tests/` - Test suites",
        "- `docs/` - Documentation",
        "",
        "---",
        f"Generated: {Path(__file__).name}",
    ])
    
    output_file = root / "TITAN_OS_REPO_TREE.md"
    output_file.write_text('\n'.join(output), encoding='utf-8')
    
    print(f"✓ Repository tree generated: {output_file}")
    print(f"  - {total_dirs} directories")
    print(f"  - {total_files} files")
    print(f"  - {len(tree_lines)} total items")

if __name__ == "__main__":
    main()
