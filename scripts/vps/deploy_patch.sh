#!/bin/bash
set -e
cp /opt/titan/src/apps/titan_intelligence.py /opt/titan/apps/titan_intelligence.py
cp /opt/titan/src/apps/titan_dev_hub.py /opt/titan/apps/titan_dev_hub.py
python3 -m py_compile /opt/titan/apps/titan_intelligence.py && echo "titan_intelligence.py: OK"
python3 -m py_compile /opt/titan/apps/titan_dev_hub.py && echo "titan_dev_hub.py: OK"
systemctl restart titan-dev-hub
sleep 2
systemctl is-active titan-dev-hub && echo "titan-dev-hub: active"
curl -s http://127.0.0.1:8877/api/health
