#!/usr/bin/env python3
"""
TITAN V8.1 SINGULARITY - Temporal Displacement Wrapper

This script provides a command-line interface for launching programs
with time displacement (libfaketime). It allows programs to perceive
a different system time, which is essential for profile aging.

Source: Unified Agent [cite: 1]

Usage:
    temporal_wrapper.py --offset-days 90 -- firefox --profile /path/to/profile
    temporal_wrapper.py --date "2025-11-01" -- command args...
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


# libfaketime library paths (varies by distro)
LIBFAKETIME_PATHS = [
    "/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1",
    "/usr/lib/faketime/libfaketime.so.1",
    "/usr/lib64/faketime/libfaketime.so.1",
]


def find_libfaketime() -> str:
    """Find the libfaketime library on the system."""
    for path in LIBFAKETIME_PATHS:
        if Path(path).exists():
            return path
    return None


def create_env(fake_time: datetime) -> dict:
    """
    Create environment variables for libfaketime.
    
    Args:
        fake_time: The datetime to present to the program
        
    Returns:
        Dictionary of environment variables
    """
    libfaketime = find_libfaketime()
    if not libfaketime:
        print("ERROR: libfaketime not found. Install with: apt install libfaketime")
        sys.exit(1)
    
    # Format time for libfaketime
    # @YYYY-MM-DD HH:MM:SS format sets absolute time
    time_str = fake_time.strftime("@%Y-%m-%d %H:%M:%S")
    
    env = os.environ.copy()
    
    # Set LD_PRELOAD to inject libfaketime
    existing_preload = env.get("LD_PRELOAD", "")
    if existing_preload:
        env["LD_PRELOAD"] = f"{libfaketime}:{existing_preload}"
    else:
        env["LD_PRELOAD"] = libfaketime
    
    # Set the fake time
    env["FAKETIME"] = time_str
    
    # Disable caching for consistent results
    env["FAKETIME_NO_CACHE"] = "1"
    
    # Don't modify file timestamps (optional, can be enabled if needed)
    env["FAKETIME_DONT_FAKE_MONOTONIC"] = "1"
    
    return env


def main():
    parser = argparse.ArgumentParser(
        description="Launch a program with time displacement (libfaketime)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a command as if it's 90 days in the past
  %(prog)s --offset-days 90 -- date
  
  # Run a command at a specific date
  %(prog)s --date "2025-11-01" -- firefox --profile /path/to/profile
  
  # Run a command 30 days in the future
  %(prog)s --offset-days -30 -- python3 myscript.py
"""
    )
    
    time_group = parser.add_mutually_exclusive_group(required=True)
    time_group.add_argument(
        "--offset-days", "-o",
        type=int,
        help="Number of days to offset (positive = past, negative = future)"
    )
    time_group.add_argument(
        "--date", "-d",
        type=str,
        help="Specific date to use (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show the effective fake time before running"
    )
    
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run (after --)"
    )
    
    args = parser.parse_args()
    
    # Remove leading '--' if present
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    
    if not command:
        parser.error("No command specified. Use -- to separate options from command.")
    
    # Calculate the fake time
    if args.offset_days is not None:
        fake_time = datetime.now() - timedelta(days=args.offset_days)
    else:
        # Parse the date string
        try:
            if " " in args.date:
                fake_time = datetime.strptime(args.date, "%Y-%m-%d %H:%M:%S")
            else:
                fake_time = datetime.strptime(args.date, "%Y-%m-%d")
                # Set to current time of day
                now = datetime.now()
                fake_time = fake_time.replace(
                    hour=now.hour,
                    minute=now.minute,
                    second=now.second
                )
        except ValueError as e:
            parser.error(f"Invalid date format: {e}")
    
    # Create the environment
    env = create_env(fake_time)
    
    if args.verbose:
        print(f"[TEMPORAL] Real time:     {datetime.now().isoformat()}")
        print(f"[TEMPORAL] Apparent time: {fake_time.isoformat()}")
        print(f"[TEMPORAL] Command:       {' '.join(command)}")
        print()
    
    # Execute the command
    try:
        result = subprocess.run(command, env=env)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print(f"ERROR: Command not found: {command[0]}")
        sys.exit(127)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
