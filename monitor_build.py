#!/usr/bin/env python3
"""
TITAN V7.0.3 - GitHub Actions Build Monitor
AUTHORITY: Dva.12 | STATUS: OBLIVION_ACTIVE
"""

import requests
import time
import json
import sys
from datetime import datetime

# GitHub repository info
REPO_OWNER = "vihangavadu"
REPO_NAME = "titan-7"
TAG = "v7.0.3"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    ENDC = '\033[0m'

def get_workflow_runs():
    """Get recent workflow runs from GitHub API"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"{Colors.RED}Error fetching workflows: {e}{Colors.ENDC}")
        return None

def monitor_build():
    """Monitor the GitHub Actions build"""
    print(f"{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.CYAN}║  TITAN V7.0.3 — GitHub Actions Build Monitor          ║{Colors.ENDC}")
    print(f"{Colors.CYAN}║  Repository: {REPO_OWNER}/{REPO_NAME}                      ║{Colors.ENDC}")
    print(f"{Colors.CYAN}║  Tag: v7.0.3                                            ║{Colors.ENDC}")
    print(f"{Colors.CYAN}╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}")
    print()

    last_status = None
    start_time = time.time()
    
    while True:
        data = get_workflow_runs()
        if not data:
            print(f"{Colors.RED}Failed to get workflow data. Retrying...{Colors.ENDC}")
            time.sleep(30)
            continue

        # Find the most recent workflow run
        workflow_runs = data.get('workflow_runs', [])
        if not workflow_runs:
            print(f"{Colors.YELLOW}No workflow runs found. Waiting...{Colors.ENDC}")
            time.sleep(30)
            continue

        latest_run = workflow_runs[0]
        current_status = latest_run.get('status', 'unknown')
        conclusion = latest_run.get('conclusion')
        workflow_name = latest_run.get('name', 'Unknown')
        created_at = latest_run.get('created_at', '')
        
        # Format timestamp
        if created_at:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            formatted_time = 'Unknown'

        # Display current status
        elapsed = int(time.time() - start_time)
        elapsed_min = elapsed // 60
        elapsed_sec = elapsed % 60
        
        print(f"{Colors.BLUE}[{elapsed_min:02d}:{elapsed_sec:02d}] {Colors.WHITE}{workflow_name}{Colors.ENDC}")
        print(f"  Status: {Colors.YELLOW}{current_status.upper()}{Colors.ENDC}")
        if conclusion:
            if conclusion == 'success':
                print(f"  Result: {Colors.GREEN}SUCCESS{Colors.ENDC}")
            elif conclusion == 'failure':
                print(f"  Result: {Colors.RED}FAILURE{Colors.ENDC}")
            else:
                print(f"  Result: {Colors.YELLOW}{conclusion.upper()}{Colors.ENDC}")
        print(f"  Created: {formatted_time}")
        
        # Check if this is a new status
        if current_status != last_status:
            last_status = current_status
            if current_status == 'in_progress':
                print(f"{Colors.GREEN}[*] Build is running!{Colors.ENDC}")
            elif current_status == 'completed':
                if conclusion == 'success':
                    print(f"{Colors.GREEN}[+] BUILD COMPLETED SUCCESSFULLY!{Colors.ENDC}")
                    print(f"{Colors.CYAN}    ISO should be available in GitHub Releases{Colors.ENDC}")
                    break
                else:
                    print(f"{Colors.RED}[!] BUILD FAILED: {conclusion}{Colors.ENDC}")
                    break

        # Check for completion
        if current_status == 'completed':
            break

        print(f"  {Colors.CYAN}Next check in 30 seconds...{Colors.ENDC}")
        print()
        time.sleep(30)

    # Final summary
    total_time = int(time.time() - start_time)
    total_min = total_time // 60
    total_sec = total_time % 60
    
    print(f"\n{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.CYAN}║  BUILD MONITORING COMPLETE                              ║{Colors.ENDC}")
    print(f"{Colors.CYAN}║  Total time: {total_min:02d}:{total_sec:02d}                              ║{Colors.ENDC}")
    print(f"{Colors.CYAN}║  GitHub: https://github.com/{REPO_OWNER}/{REPO_NAME}/actions ║{Colors.ENDC}")
    print(f"{Colors.CYAN}║  Release: https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/tag/v7.0.3 ║{Colors.ENDC}")
    print(f"{Colors.CYAN}╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}")

if __name__ == "__main__":
    try:
        monitor_build()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}Monitor error: {e}{Colors.ENDC}")
        sys.exit(1)
