"""Direct library probes for §24 acceptance examples and edge cases.
Best-effort: candidates differ in API, so each probe is wrapped and reports
what it found. Run from repo root."""
import sys, traceback, importlib, pkgutil
import wine_stock_reporter as W

print("=== package modules ===")
import os
print(sorted(os.listdir(os.path.dirname(W.__file__))))

def show(label, fn):
    try:
        r = fn()
        print(f"[OK] {label}: {r}")
    except Exception as e:
        print(f"[ERR] {label}: {type(e).__name__}: {e}")

# Inspect parser module
try:
    P = importlib.import_module("wine_stock_reporter.parser")
    print("=== parser public names ===")
    print([n for n in dir(P) if not n.startswith('_')])
except Exception as e:
    print("parser import err:", e)

try:
    C = importlib.import_module("wine_stock_reporter.calculations")
    print("=== calculations public names ===")
    print([n for n in dir(C) if not n.startswith('_')])
except Exception as e:
    print("calc import err:", e)

# Try to parse the §24 description via any plausible parse fn
desc1 = "FV 22 CHR EP NZ 750ml/12p"
desc2 = "FV 22 CHR EP NZ 750ml/6p"
desc3 = "FV 22 RDB EP UK 750ml/6p Legacy Red"
desc_bad = "totally unparseable nonsense @@@"
import re
for modname in ("wine_stock_reporter.parser",):
    M = importlib.import_module(modname)
    for fname in dir(M):
        if fname.startswith('_'): continue
        f = getattr(M, fname)
        if callable(f):
            for d in (desc1, desc3, desc_bad):
                try:
                    out = f(d)
                    print(f"  parser.{fname}({d!r}) -> {out!r}")
                except Exception as e:
                    pass

print("=== END LIB PROBE ===")
