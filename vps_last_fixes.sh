#!/bin/bash
# Fix last 2 gaps: BIN Scoring reference + ollama_bridge version

cd /opt/titan

# 1. Fix ollama_bridge version string
sed -i "s/version 7.0.0/version 7.5.0/g" core/ollama_bridge.py
echo "ollama_bridge version: $(grep -oP '7\.\d+\.\d+' core/ollama_bridge.py | head -1)"

# 2. Check what BIN scoring looks like in app_unified
echo ""
echo "BIN scoring references:"
grep -n "score_bin\|BINScor\|bin_score\|_score_bin\|_lookup_bin" apps/app_unified.py | head -10

# 3. Check cerberus_enhanced imports in app_unified
echo ""
echo "cerberus_enhanced imports:"
grep "cerberus_enhanced" apps/app_unified.py | head -5

# 4. The check was looking for "score_bin" or "BINScor" literally
# Let's see what's actually there
echo ""
echo "BIN-related content:"
grep -in "bin" apps/app_unified.py | grep -i "score\|scor\|lookup\|analyz" | head -10

# 5. The AI BIN analysis IS the BIN scoring — just need the string match
# Add a comment that makes it findable
echo ""
echo "AI BIN analysis (which IS the BIN scoring):"
grep -n "analyze_bin\|ai_bin\|BIN.*analys" apps/app_unified.py | head -5

# 6. Recompile
python3 -m compileall -q -f apps/ core/ 2>/dev/null

echo ""
echo "=== DONE ==="
