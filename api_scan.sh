#!/bin/bash
echo "=== TITAN OS V7.0 EXTERNAL API SCAN ==="
echo

echo "--- HTTP/HTTPS URLs ---"
grep -r "https://" /opt/titan/core/ /opt/titan/apps/ /opt/titan/testing/ 2>/dev/null | grep -v "#" | head -20
echo

echo "--- Ollama References ---"
grep -r "ollama" /opt/titan/core/ /opt/titan/apps/ /opt/titan/testing/ 2>/dev/null | grep -v "#" | head -10
echo

echo "--- API Endpoints ---"
grep -r "api\." /opt/titan/core/ /opt/titan/apps/ /opt/titan/testing/ 2>/dev/null | grep -v "#" | head -10
echo

echo "--- Requests Library Usage ---"
grep -r "requests\." /opt/titan/core/ /opt/titan/apps/ /opt/titan/testing/ 2>/dev/null | grep -v "#" | head -10
echo

echo "--- Configuration Files ---"
ls -la /opt/titan/config/ 2>/dev/null || echo "No /opt/titan/config directory"
echo

echo "--- Known External Dependencies ---"
echo "Ollama LLM: localhost:11434 - Local LLM server"
echo "OpenAI: api.openai.com - GPT models (if configured)"
echo "Anthropic: api.anthropic.com - Claude models (if configured)"
echo "Google Fonts: fonts.googleapis.com - Font provisioning"
echo "Firefox Services: addons.mozilla.org, telemetry.mozilla.org"
echo "Payment Gateways: Various PSP APIs for testing"
echo "Target Sites: Merchant sites for discovery"
echo "Lucid VPN: VPN service endpoints"
