#!/bin/bash
cd /opt/titan && python3 - <<'PYEOF'
import sys
sys.path.insert(0, "core")
from tls_parrot import TLSParrotEngine, ParrotTarget
e = TLSParrotEngine()
p = e.ja4_permutation(ParrotTarget.CHROME_131_WIN11, "amazon.com")
print(f"JA4 permuted: {p.get('ja4_permuted')}")
print(f"JA4 computed: {p.get('ja4_computed')}")
print(f"Ciphers: {len(p['cipher_suites'])}")
print(f"Extensions: {len(p['extensions'])}")
p2 = e.ja4_permutation(ParrotTarget.CHROME_131_WIN11, "amazon.com")
same = p['cipher_suites'] == p2['cipher_suites']
print(f"Per-session shuffle: {'DIFFERENT each time' if not same else 'SAME order'}")
PYEOF
