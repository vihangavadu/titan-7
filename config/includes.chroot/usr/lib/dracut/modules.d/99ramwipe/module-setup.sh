#!/bin/bash
check() { return 0; }
depends() { return 0; }
install() { inst_hook cleanup 99 "$moddir/titan-wipe.sh"; }
