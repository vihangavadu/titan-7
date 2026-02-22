#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# TITAN V8.1 — AI Enhancement Stack Installer
# Installs: ChromaDB, LangChain, SerpAPI, DuckDuckGo Search
# ═════════════════════════════════════════════════════════════════════════

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  TITAN V8.1 — AI Enhancement Stack Installer                ║"
echo "║  ChromaDB + LangChain + Web Intelligence                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python not found"
    exit 1
fi
echo "[✓] Python: $($PYTHON --version)"

# Create data directories
echo "[*] Creating data directories..."
mkdir -p /opt/titan/data/vector_db
mkdir -p /opt/titan/data/web_intel_cache
mkdir -p /opt/titan/data/llm_cache

# Install ChromaDB (vector memory)
echo ""
echo "── Installing ChromaDB (Vector Memory) ──"
$PYTHON -m pip install --quiet chromadb>=0.4.22 2>&1 | tail -1
echo "[✓] ChromaDB installed"

# Install sentence-transformers (optional, better embeddings)
echo ""
echo "── Installing Sentence Transformers (optional) ──"
$PYTHON -m pip install --quiet sentence-transformers>=2.2.0 2>&1 | tail -1 || {
    echo "[!] Sentence Transformers failed (non-critical, ChromaDB will use default embeddings)"
}

# Install LangChain stack
echo ""
echo "── Installing LangChain (Agentic Orchestration) ──"
$PYTHON -m pip install --quiet langchain>=0.2.0 langchain-core>=0.2.0 langchain-ollama>=0.1.0 langchain-community>=0.2.0 2>&1 | tail -1
echo "[✓] LangChain installed"

# Install web search providers
echo ""
echo "── Installing Web Intelligence Providers ──"
$PYTHON -m pip install --quiet duckduckgo-search>=5.0.0 2>&1 | tail -1
echo "[✓] DuckDuckGo Search installed (free, no API key)"

$PYTHON -m pip install --quiet google-search-results>=2.4.0 2>&1 | tail -1 || {
    echo "[!] SerpAPI client failed (non-critical, DuckDuckGo is fallback)"
}

# Verify installations
echo ""
echo "── Verification ──"
$PYTHON -c "import chromadb; print(f'[✓] ChromaDB {chromadb.__version__}')" 2>/dev/null || echo "[✗] ChromaDB NOT available"
$PYTHON -c "import langchain; print(f'[✓] LangChain {langchain.__version__}')" 2>/dev/null || echo "[✗] LangChain NOT available"
$PYTHON -c "from langchain_ollama import ChatOllama; print('[✓] LangChain-Ollama')" 2>/dev/null || echo "[✗] LangChain-Ollama NOT available"
$PYTHON -c "from duckduckgo_search import DDGS; print('[✓] DuckDuckGo Search')" 2>/dev/null || echo "[✗] DuckDuckGo Search NOT available"
$PYTHON -c "from serpapi import GoogleSearch; print('[✓] SerpAPI')" 2>/dev/null || echo "[!] SerpAPI NOT available (set SERPAPI_KEY in titan.env)"

# Verify Titan modules
echo ""
echo "── Titan Module Verification ──"
cd /opt/titan/core
$PYTHON -c "from titan_vector_memory import get_vector_memory; m=get_vector_memory(); print(f'[✓] Vector Memory: {\"OK\" if m.is_available else \"UNAVAILABLE\"}')" 2>/dev/null || echo "[✗] titan_vector_memory.py failed"
$PYTHON -c "from titan_web_intel import get_web_intel; w=get_web_intel(); print(f'[✓] Web Intel: providers={w._provider_order}')" 2>/dev/null || echo "[✗] titan_web_intel.py failed"
$PYTHON -c "from titan_agent_chain import get_titan_agent; a=get_titan_agent(); print(f'[✓] Agent Chain: {\"FULL\" if a.is_available else \"FALLBACK\"} mode')" 2>/dev/null || echo "[✗] titan_agent_chain.py failed"
$PYTHON -c "from ai_intelligence_engine import get_ai_status; s=get_ai_status(); print(f'[✓] AI Engine: features={s[\"features\"]}')" 2>/dev/null || echo "[✗] ai_intelligence_engine.py failed"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Installation Complete!                                      ║"
echo "║                                                              ║"
echo "║  Next steps:                                                 ║"
echo "║  1. Set SERPAPI_KEY in /opt/titan/config/titan.env           ║"
echo "║     (optional — DuckDuckGo works without any key)            ║"
echo "║  2. Restart titan-backend: systemctl restart titan-backend   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
