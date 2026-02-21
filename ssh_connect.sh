#!/bin/bash
export SSH_ASKPASS="/c/Users/Administrator/Downloads/titan-7/titan-7/askpass.sh"
export DISPLAY=":0"
export SSH_ASKPASS_REQUIRE="force"
chmod +x "$SSH_ASKPASS"

CMD="$@"

# Use SSH_ASKPASS with no-TTY trick: run ssh in background of a subshell
( exec ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o ConnectTimeout=15 root@72.62.72.48 "$CMD" ) </dev/null 2>&1
