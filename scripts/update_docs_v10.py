#!/usr/bin/env python3
"""
TITAN X V10.0 — Batch Doc Updater
Updates version headers, module counts, AI model references, and dates
across all 77+ documentation files.
"""
import os
import re
import sys
from pathlib import Path
from datetime import datetime

DOCS_DIR = Path(__file__).parent.parent / "docs"
DATE_STR = datetime.now().strftime("%Y-%m-%d")

# Replacements: (pattern, replacement)
REPLACEMENTS = [
    # Version headers
    (r'TITAN\s+V7\.\d+(?:\.\d+)?', 'TITAN X V10.0'),
    (r'TITAN\s+V8\.\d+(?:\.\d+)?', 'TITAN X V10.0'),
    (r'TITAN\s+V9\.\d+(?:\.\d+)?', 'TITAN X V10.0'),
    (r'Titan\s+V7\.\d+(?:\.\d+)?', 'Titan X V10.0'),
    (r'Titan\s+V8\.\d+(?:\.\d+)?', 'Titan X V10.0'),
    (r'Titan\s+V9\.\d+(?:\.\d+)?', 'Titan X V10.0'),
    # Version numbers in text
    (r'Version:\s*7\.\d+\.\d+', 'Version: 10.0.0'),
    (r'Version:\s*8\.\d+\.\d+', 'Version: 10.0.0'),
    (r'Version:\s*9\.\d+\.\d+', 'Version: 10.0.0'),
    (r'\bv7\.\d+\.\d+\b', 'v10.0.0'),
    (r'\bv8\.\d+\.\d+\b', 'v10.0.0'),
    (r'\bv9\.\d+\.\d+\b', 'v10.0.0'),
    # Module counts
    (r'\b56\s+(?:core\s+)?modules?\b', '115 core modules'),
    (r'\b86\s+(?:core\s+)?modules?\b', '115 core modules'),
    (r'\b90\s+(?:core\s+)?modules?\b', '115 core modules'),
    (r'\b96\s+(?:core\s+)?modules?\b', '115 core modules'),
    # AI model counts
    (r'\b3\s+AI\s+models?\b', '4 AI models'),
    (r'\b3\s+models?\s+\(', '4 models ('),
    (r'\b58\s+(?:AI\s+)?task\s+routes?\b', '67 AI task routes'),
    (r'\b33\s+(?:AI\s+)?task\s+routes?\b', '67 AI task routes'),
    # GUI app counts (keep 11)
    (r'\b4\s+GUI\s+apps?\b', '11 GUI apps'),
    (r'\b5\s+GUI\s+apps?\b', '11 GUI apps'),
    # BIN database
    (r'\b25\s+BINs?\b', '110+ BINs'),
    # Codename
    (r'SINGULARITY', 'TITAN_X'),
]

def update_file(filepath):
    """Update a single doc file. Returns (changed, num_replacements)."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return False, 0

    original = content
    total_replacements = 0

    for pattern, replacement in REPLACEMENTS:
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            total_replacements += count

    if content != original:
        filepath.write_text(content, encoding='utf-8')
        return True, total_replacements
    return False, 0

def main():
    if not DOCS_DIR.exists():
        print(f"Docs directory not found: {DOCS_DIR}")
        sys.exit(1)

    md_files = sorted(DOCS_DIR.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files in {DOCS_DIR}")
    print(f"Date: {DATE_STR}")
    print()

    changed_files = 0
    total_replacements = 0

    for f in md_files:
        rel = f.relative_to(DOCS_DIR)
        changed, count = update_file(f)
        if changed:
            print(f"  UPDATED  {rel} ({count} replacements)")
            changed_files += 1
            total_replacements += count
        else:
            print(f"  OK       {rel}")

    # Also update README.md if present
    readme = DOCS_DIR.parent / "README.md"
    if readme.exists():
        changed, count = update_file(readme)
        if changed:
            print(f"  UPDATED  README.md ({count} replacements)")
            changed_files += 1
            total_replacements += count

    print()
    print(f"{'='*50}")
    print(f"  Files scanned:  {len(md_files) + (1 if readme.exists() else 0)}")
    print(f"  Files updated:  {changed_files}")
    print(f"  Replacements:   {total_replacements}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
