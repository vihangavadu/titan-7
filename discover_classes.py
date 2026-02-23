#!/usr/bin/env python3
"""Discover actual class names in all core modules."""
import os, sys, importlib, inspect
sys.path.insert(0, "/opt/titan/core")
sys.path.insert(0, "/opt/titan")

core = "/opt/titan/core"
files = sorted([f[:-3] for f in os.listdir(core) if f.endswith(".py") and f != "__init__.py"])

for mn in files:
    try:
        m = importlib.import_module(mn)
        classes = [n for n, o in inspect.getmembers(m, inspect.isclass) if o.__module__ == mn]
        funcs = [n for n, o in inspect.getmembers(m, inspect.isfunction) if o.__module__ == mn]
        if classes:
            print(f"{mn}: CLASSES={classes[:8]}")
        elif funcs:
            print(f"{mn}: FUNCS={funcs[:8]}")
        else:
            attrs = [a for a in dir(m) if not a.startswith("_")]
            print(f"{mn}: ATTRS={attrs[:8]}")
    except Exception as e:
        print(f"{mn}: ERR={str(e)[:80]}")
