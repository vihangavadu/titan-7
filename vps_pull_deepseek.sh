#!/bin/bash
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  PULLING deepseek-r1:8b                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Disk before pull:"
df -h / | tail -1
echo ""

echo "Pulling deepseek-r1:8b (~5GB)..."
ollama pull deepseek-r1:8b

echo ""
echo "Pull complete. Models now installed:"
ollama list
echo ""
echo "Disk after pull:"
df -h / | tail -1
