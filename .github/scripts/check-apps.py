"""Check that every child ArgoCD Application has a sync-wave and a retry.

usage: python3 .github/scripts/check-apps.py <repo root>   (needs PyYAML)

For each kubernetes/apps/**/application.yaml (what app-of-apps includes; symlinks skipped) it
fails, naming the file, when
  - metadata.annotations["argocd.argoproj.io/sync-wave"] is missing or not an integer string, or
  - spec.syncPolicy.retry is not a mapping with an integer limit > 0, or
  - it sets CreateNamespace=true without Pod Security warn and audit labels in
    spec.syncPolicy.managedNamespaceMetadata.labels.
Prints PASS/FAIL per file and exits 1 on any failure.
"""
import pathlib
import re
import sys

import yaml

WAVE = "argocd.argoproj.io/sync-wave"
PSA = "pod-security.kubernetes.io/"
LEVELS = {"privileged", "baseline", "restricted"}
repo = pathlib.Path(sys.argv[1])
ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}".rstrip())


def linked(f):
    return any(p.is_symlink() for p in [f, *f.parents] if p != repo and repo in p.parents)


files = [f for f in sorted(repo.glob("kubernetes/apps/**/application.yaml")) if not linked(f)]
check("found child application.yaml files", files, f"({len(files)})")
for f in files:
    rel = f.relative_to(repo)
    app = yaml.safe_load(f.read_text()) or {}
    wave = ((app.get("metadata") or {}).get("annotations") or {}).get(WAVE)
    check(f"{rel} has an integer {WAVE}", isinstance(wave, str) and re.fullmatch(r"-?\d+", wave), f"got {wave!r}")
    policy = (app.get("spec") or {}).get("syncPolicy") or {}
    retry = policy.get("retry")
    limit = retry.get("limit") if isinstance(retry, dict) else None
    good = isinstance(limit, int) and not isinstance(limit, bool) and limit > 0
    check(f"{rel} has spec.syncPolicy.retry.limit > 0", good, f"got retry {retry!r}")
    if "CreateNamespace=true" in (policy.get("syncOptions") or []):
        labels = (policy.get("managedNamespaceMetadata") or {}).get("labels") or {}
        for mode in ("warn", "audit"):
            check(f"{rel} sets {PSA}{mode}", labels.get(PSA + mode) in LEVELS, f"got {labels.get(PSA + mode)!r}")
print("RESULT:", "PASS" if all(ok) else "FAIL")
sys.exit(0 if all(ok) else 1)
