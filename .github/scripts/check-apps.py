"""Check that every child ArgoCD Application has a sync-wave and a retry.

usage: python3 .github/scripts/check-apps.py <repo root>   (needs PyYAML)

For each kubernetes/apps/*/*/application.yaml (symlinks skipped) it fails, naming the file, when
  - metadata.annotations["argocd.argoproj.io/sync-wave"] is missing or not an integer string, or
  - spec.syncPolicy.retry.limit is missing.
Prints PASS/FAIL per file and exits 1 on any failure.
"""
import pathlib
import re
import sys

import yaml

WAVE = "argocd.argoproj.io/sync-wave"
repo = pathlib.Path(sys.argv[1])
ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}".rstrip())


files = [f for f in sorted(repo.glob("kubernetes/apps/*/*/application.yaml")) if not f.is_symlink()]
check("found child application.yaml files", files, f"({len(files)})")
for f in files:
    rel = f.relative_to(repo)
    app = yaml.safe_load(f.read_text()) or {}
    wave = ((app.get("metadata") or {}).get("annotations") or {}).get(WAVE)
    check(f"{rel} has an integer {WAVE}", isinstance(wave, str) and re.fullmatch(r"-?\d+", wave), f"got {wave!r}")
    retry = ((app.get("spec") or {}).get("syncPolicy") or {}).get("retry") or {}
    check(f"{rel} has spec.syncPolicy.retry.limit", "limit" in retry, f"got {retry.get('limit')!r}")
print("RESULT:", "PASS" if all(ok) else "FAIL")
sys.exit(0 if all(ok) else 1)
