@echo off
"C:\Program Files\Git\bin\bash.exe" -c "sshpass -p 'Xt7mKp9wRv3n.Jq2026' ssh -o StrictHostKeyChecking=no root@72.62.72.48 'bash /root/vps_verify_real.sh' 2>&1; echo EXIT:$?"
