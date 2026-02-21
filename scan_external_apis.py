#!/usr/bin/env python3
"""
Scan Titan OS V7.0 for all external API dependencies and services.
Identifies HTTP/HTTPS endpoints, API calls, and external services.
"""
import os
import re
import json

SCAN_DIRS = [
    "iso/config/includes.chroot/opt/titan/core",
    "iso/config/includes.chroot/opt/titan/apps",
    "iso/config/includes.chroot/opt/titan/testing",
]

# Patterns to detect external APIs
PATTERNS = {
    "HTTP_URLS": [
        r'https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})?(?:/[^\s"\'`<>]*)?',
        r'"https?://[^"]*"',
        r"'https?://[^']*'",
    ],
    "API_ENDPOINTS": [
        r'api\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'[a-zA-Z0-9.-]+\.com/(?:api|v1|v2|graphql)',
        r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/(?:api|v1|v2|graphql)',
    ],
    "EXTERNAL_SERVICES": [
        r'(?:requests|urllib|httpx|aiohttp)\.(?:get|post|put|delete|patch|request)\s*\(\s*["\']([^"\']+)["\']',
        r'curl\s+["\']?(https?://[^"\'`]+)',
        r'wget\s+["\']?(https?://[^"\'`]+)',
    ],
    "OLLAMA": [
        r'ollama\s+["\']?([^"\']+)["\']?',
        r'localhost:11434',
        r'127\.0\.0\.1:11434',
        r'ollama\.ai',
    ],
    "DNS": [
        r'resolve\s*\(\s*["\']([^"\']+)["\']',
        r'socket\.gethostbyname\s*\(\s*["\']([^"\']+)["\']',
        r'nslookup\s+([^\s]+)',
    ],
}

# Known Titan OS external dependencies
KNOWN_APIS = {
    "Ollama LLM": "localhost:11434 - Local LLM inference server",
    "OpenAI": "api.openai.com - GPT models (if configured)",
    "Anthropic": "api.anthropic.com - Claude models (if configured)",
    "Google Fonts": "fonts.googleapis.com - Font provisioning",
    "Firefox/Gecko": "addons.mozilla.org, telemetry.mozilla.org - Browser services",
    "Payment Gateways": "Various PSP APIs for transaction testing",
    "Target Sites": "Merchant sites for discovery engine",
    "VPN Services": "Lucid VPN endpoints",
}

def scan_file(fp):
    """Scan a single file for external API references."""
    apis_found = set()
    
    try:
        with open(fp, "r", errors="replace") as f:
            content = f.read()
    except Exception:
        return apis_found
    
    # Check each pattern
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                if match and len(match) > 3:  # Filter tiny matches
                    apis_found.add((category, match.strip()))
    
    return apis_found

def main():
    print("=" * 80)
    print("TITAN OS V7.0 — EXTERNAL API DEPENDENCY SCAN")
    print("=" * 80)
    print()
    
    all_apis = {}
    files_scanned = 0
    
    for d in SCAN_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(d, fn)
            apis = scan_file(fp)
            if apis:
                short_path = fp.replace("iso/config/includes.chroot/opt/titan/", "")
                all_apis[short_path] = apis
            files_scanned += 1
    
    print(f"Scanned {files_scanned} Python files")
    print()
    
    # Group by category
    by_category = {}
    for file_path, apis in all_apis.items():
        for category, api in apis:
            by_category.setdefault(category, []).append((file_path, api))
    
    # Display findings
    for category, items in sorted(by_category.items()):
        print(f"--- {category} ({len(items)} found) ---")
        unique_apis = set()
        for file_path, api in items:
            unique_apis.add(api)
        for api in sorted(unique_apis):
            print(f"  {api}")
        print()
    
    # Known dependencies summary
    print("--- KNOWN TITAN OS EXTERNAL DEPENDENCIES ---")
    for service, desc in KNOWN_APIS.items():
        print(f"  {service}: {desc}")
    print()
    
    # Configuration files to check
    print("--- CONFIGURATION FILES TO CHECK ---")
    config_files = [
        "iso/config/includes.chroot/opt/titan/config/ollama.json",
        "iso/config/includes.chroot/opt/titan/config/llm_config.json",
        "iso/config/includes.chroot/opt/titan/config/targets.json",
        "iso/config/includes.chroot/opt/titan/config/psp_config.json",
    ]
    
    for cf in config_files:
        if os.path.exists(cf):
            print(f"  ✓ {cf}")
            try:
                with open(cf, "r") as f:
                    content = f.read()
                    if "http" in content.lower():
                        print(f"    Contains HTTP endpoints")
            except Exception:
                pass
        else:
            print(f"  ✗ {cf} (not found)")
    
    print()
    print("=" * 80)
    print("RECOMMENDATION:")
    print("1. Ensure all external APIs have proper error handling")
    print("2. Configure timeouts for all HTTP requests")
    print("3. Use environment variables for API keys and endpoints")
    print("4. Implement fallback mechanisms for critical services")
    print("5. Monitor external service availability")
    print("=" * 80)

if __name__ == "__main__":
    main()
