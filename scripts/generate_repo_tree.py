#!/usr/bin/env python3
"""
TITAN OS - Complete Repository Tree Generator
Generates a comprehensive folder-to-folder, file-to-file tree of the entire repository.
Captures EVERYTHING - no files are skipped (including temp, hidden, junk files).

Features:
- Multiple output formats: text tree, JSON, markdown
- Configurable filters (but defaults to capturing everything)
- File size, count, and metadata
- Handles large repos efficiently
- Cross-platform (Windows/Linux/Mac)

Usage:
  # Generate all formats with default settings (captures everything)
  python scripts/generate_repo_tree.py

  # Custom output directory
  python scripts/generate_repo_tree.py --output-dir ./reports

  # Only specific formats
  python scripts/generate_repo_tree.py --format text json

  # Apply filters (exclude certain patterns)
  python scripts/generate_repo_tree.py --exclude ".git" "__pycache__"
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_file_size_human(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}PB"


def should_exclude(path: Path, exclude_patterns: Set[str]) -> bool:
    """Check if path matches any exclude pattern."""
    if not exclude_patterns:
        return False
    
    path_str = str(path)
    path_parts = path.parts
    
    for pattern in exclude_patterns:
        # Check if pattern matches any part of the path
        if pattern in path_parts:
            return True
        # Check if pattern is in the full path string
        if pattern in path_str:
            return True
    
    return False


def scan_directory(
    root_path: Path,
    exclude_patterns: Set[str] = None,
    include_hidden: bool = True,
) -> Dict:
    """
    Recursively scan directory and build complete tree structure.
    
    Returns:
        Dict with structure:
        {
            "name": "folder_name",
            "type": "directory",
            "path": "relative/path",
            "size": total_bytes,
            "file_count": int,
            "dir_count": int,
            "children": [...],
        }
    """
    exclude_patterns = exclude_patterns or set()
    
    def _scan(current_path: Path, relative_to: Path) -> Dict:
        rel_path = current_path.relative_to(relative_to)
        
        node = {
            "name": current_path.name or str(current_path),
            "type": "directory" if current_path.is_dir() else "file",
            "path": str(rel_path),
            "size": 0,
            "file_count": 0,
            "dir_count": 0,
        }
        
        if current_path.is_file():
            try:
                node["size"] = current_path.stat().st_size
                node["file_count"] = 1
                node["modified"] = current_path.stat().st_mtime
            except (OSError, PermissionError):
                node["size"] = 0
                node["error"] = "access_denied"
            return node
        
        # Directory
        children = []
        total_size = 0
        total_files = 0
        total_dirs = 0
        
        try:
            entries = sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except (OSError, PermissionError):
            node["error"] = "access_denied"
            return node
        
        for entry in entries:
            # Skip if matches exclude pattern
            if should_exclude(entry, exclude_patterns):
                continue
            
            # Skip hidden files if not included (but default is to include)
            if not include_hidden and entry.name.startswith("."):
                continue
            
            child_node = _scan(entry, relative_to)
            children.append(child_node)
            
            total_size += child_node["size"]
            total_files += child_node["file_count"]
            total_dirs += child_node["dir_count"]
            
            if child_node["type"] == "directory":
                total_dirs += 1
        
        node["children"] = children
        node["size"] = total_size
        node["file_count"] = total_files
        node["dir_count"] = total_dirs
        
        return node
    
    return _scan(root_path, root_path)


def tree_to_text(node: Dict, prefix: str = "", is_last: bool = True, show_size: bool = True) -> List[str]:
    """Convert tree structure to text representation (ASCII tree)."""
    lines = []
    
    # Current node
    connector = "└── " if is_last else "├── "
    name = node["name"]
    
    if node["type"] == "directory":
        suffix = f"/ ({node['file_count']} files, {node['dir_count']} dirs"
        if show_size:
            suffix += f", {get_file_size_human(node['size'])}"
        suffix += ")"
        name = f"{name}{suffix}"
    else:
        if show_size:
            name = f"{name} ({get_file_size_human(node['size'])})"
    
    lines.append(f"{prefix}{connector}{name}")
    
    # Children
    if "children" in node and node["children"]:
        extension = "    " if is_last else "│   "
        new_prefix = prefix + extension
        
        children = node["children"]
        for i, child in enumerate(children):
            child_is_last = (i == len(children) - 1)
            lines.extend(tree_to_text(child, new_prefix, child_is_last, show_size))
    
    return lines


def tree_to_markdown(node: Dict, level: int = 0, show_size: bool = True) -> List[str]:
    """Convert tree structure to markdown format."""
    lines = []
    
    indent = "  " * level
    
    if node["type"] == "directory":
        icon = "📁"
        suffix = f" ({node['file_count']} files, {node['dir_count']} dirs"
        if show_size:
            suffix += f", {get_file_size_human(node['size'])}"
        suffix += ")"
    else:
        icon = "📄"
        suffix = f" ({get_file_size_human(node['size'])})" if show_size else ""
    
    lines.append(f"{indent}- {icon} **{node['name']}**{suffix}")
    
    if "children" in node and node["children"]:
        for child in node["children"]:
            lines.extend(tree_to_markdown(child, level + 1, show_size))
    
    return lines


def tree_to_flat_list(node: Dict, result: List[Dict] = None) -> List[Dict]:
    """Convert tree to flat list of all files with full paths."""
    if result is None:
        result = []
    
    if node["type"] == "file":
        result.append({
            "path": node["path"],
            "name": node["name"],
            "size": node["size"],
            "size_human": get_file_size_human(node["size"]),
            "modified": node.get("modified", 0),
        })
    
    if "children" in node:
        for child in node["children"]:
            tree_to_flat_list(child, result)
    
    return result


def generate_summary(tree: Dict) -> Dict:
    """Generate summary statistics from tree."""
    return {
        "total_files": tree["file_count"],
        "total_directories": tree["dir_count"],
        "total_size_bytes": tree["size"],
        "total_size_human": get_file_size_human(tree["size"]),
        "root_name": tree["name"],
        "root_path": tree["path"],
    }


def generate_extension_stats(flat_list: List[Dict]) -> Dict[str, Dict]:
    """Generate statistics by file extension."""
    stats = defaultdict(lambda: {"count": 0, "total_size": 0})
    
    for item in flat_list:
        name = item["name"]
        ext = Path(name).suffix.lower() or "(no extension)"
        stats[ext]["count"] += 1
        stats[ext]["total_size"] += item["size"]
    
    # Convert to regular dict and add human-readable sizes
    result = {}
    for ext, data in sorted(stats.items(), key=lambda x: x[1]["total_size"], reverse=True):
        result[ext] = {
            "count": data["count"],
            "total_size": data["total_size"],
            "total_size_human": get_file_size_human(data["total_size"]),
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate complete repository tree (captures everything)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for generated files (default: current directory)",
    )
    parser.add_argument(
        "--format",
        nargs="+",
        choices=["text", "json", "markdown", "all"],
        default=["all"],
        help="Output formats to generate (default: all)",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Patterns to exclude (e.g., .git __pycache__). Default: none (captures everything)",
    )
    parser.add_argument(
        "--no-hidden",
        action="store_true",
        help="Exclude hidden files (files starting with .)",
    )
    parser.add_argument(
        "--no-size",
        action="store_true",
        help="Don't show file sizes in output",
    )
    parser.add_argument(
        "--prefix",
        default="repo_tree",
        help="Prefix for output filenames (default: repo_tree)",
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not root_path.exists():
        print(f"Error: Root path does not exist: {root_path}", file=sys.stderr)
        return 1
    
    exclude_patterns = set(args.exclude) if args.exclude else set()
    include_hidden = not args.no_hidden
    show_size = not args.no_size
    
    formats = args.format
    if "all" in formats:
        formats = ["text", "json", "markdown"]
    
    print("=" * 70)
    print("TITAN OS - Complete Repository Tree Generator")
    print("=" * 70)
    print(f"Root: {root_path}")
    print(f"Output: {output_dir}")
    print(f"Formats: {', '.join(formats)}")
    print(f"Exclude patterns: {exclude_patterns or 'None (capturing everything)'}")
    print(f"Include hidden: {include_hidden}")
    print("=" * 70)
    print()
    
    # Scan directory
    print("Scanning directory tree...")
    start_time = time.time()
    tree = scan_directory(root_path, exclude_patterns, include_hidden)
    scan_time = time.time() - start_time
    print(f"Scan complete in {scan_time:.2f}s")
    print()
    
    # Generate summary
    summary = generate_summary(tree)
    print("Summary:")
    print(f"  Total files: {summary['total_files']:,}")
    print(f"  Total directories: {summary['total_directories']:,}")
    print(f"  Total size: {summary['total_size_human']}")
    print()
    
    # Generate flat list for extension stats
    flat_list = tree_to_flat_list(tree)
    ext_stats = generate_extension_stats(flat_list)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Generate outputs
    if "text" in formats:
        print("Generating text tree...")
        text_lines = [
            "=" * 70,
            "COMPLETE REPOSITORY TREE",
            "=" * 70,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Root: {root_path}",
            f"Files: {summary['total_files']:,}",
            f"Directories: {summary['total_directories']:,}",
            f"Total size: {summary['total_size_human']}",
            "=" * 70,
            "",
        ]
        text_lines.extend(tree_to_text(tree, show_size=show_size))
        text_lines.append("")
        text_lines.append("=" * 70)
        text_lines.append("FILE EXTENSION STATISTICS")
        text_lines.append("=" * 70)
        for ext, stats in list(ext_stats.items())[:20]:  # Top 20
            text_lines.append(f"{ext:20} {stats['count']:>6} files  {stats['total_size_human']:>10}")
        
        text_file = output_dir / f"{args.prefix}_{timestamp}.txt"
        text_file.write_text("\n".join(text_lines), encoding="utf-8")
        print(f"  ✓ {text_file}")
    
    if "json" in formats:
        print("Generating JSON...")
        json_data = {
            "metadata": {
                "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "root_path": str(root_path),
                "scan_time_seconds": scan_time,
            },
            "summary": summary,
            "extension_stats": ext_stats,
            "tree": tree,
            "flat_list": flat_list,
        }
        json_file = output_dir / f"{args.prefix}_{timestamp}.json"
        json_file.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        print(f"  ✓ {json_file}")
    
    if "markdown" in formats:
        print("Generating markdown...")
        md_lines = [
            "# Complete Repository Tree",
            "",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Root:** `{root_path}`  ",
            f"**Files:** {summary['total_files']:,}  ",
            f"**Directories:** {summary['total_directories']:,}  ",
            f"**Total size:** {summary['total_size_human']}  ",
            "",
            "## Directory Tree",
            "",
        ]
        md_lines.extend(tree_to_markdown(tree, show_size=show_size))
        md_lines.extend([
            "",
            "## File Extension Statistics",
            "",
            "| Extension | Files | Total Size |",
            "|-----------|------:|-----------:|",
        ])
        for ext, stats in list(ext_stats.items())[:30]:  # Top 30
            md_lines.append(f"| `{ext}` | {stats['count']:,} | {stats['total_size_human']} |")
        
        md_file = output_dir / f"{args.prefix}_{timestamp}.md"
        md_file.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"  ✓ {md_file}")
    
    print()
    print("=" * 70)
    print("Complete! All files captured (including temp/hidden/junk files).")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
