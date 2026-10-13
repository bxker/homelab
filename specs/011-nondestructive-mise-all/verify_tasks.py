import tomllib, subprocess, sys, os, tempfile, pathlib, shutil
repo = pathlib.Path(sys.argv[1]); out = []
tasks = tomllib.load(open(repo/"mise.toml","rb"))["tasks"]
def scripts(t):
    r = t.get("run", [])
    r = [r] if isinstance(r, (str, dict)) else r
    return [x for x in r if isinstance(x, str)]
def steps(t):
    r = t.get("run", [])
    r = [r] if isinstance(r, (str, dict)) else r
    return [x["task"] for x in r if isinstance(x, dict)] + t.get("depends", [])
ok = True
# 1. syntax of every script under sh (mise default: sh -c -o errexit)
for n, t in tasks.items():
    for s in scripts(t):
        p = subprocess.run(["sh", "-n", "-c", s], capture_output=True, text=True)
        if p.returncode: ok = False; out.append(f"SYNTAX FAIL {n}: {p.stderr}")
out.append(f"syntax: {sum(len(scripts(t)) for t in tasks.values())} scripts checked under sh -n")
# 2. reachability: does any task reachable from X run 'tofu destroy' / auto-approve destroy?
def reach(n, seen=None):
    seen = seen or set()
    if n in seen: return seen
    seen.add(n)
    for c in steps(tasks[n]): reach(c, seen)
    return seen
for root in ["all", "cluster", "infra"]:
    r = reach(root); bad = [n for n in r if any("tofu destroy" in s for s in scripts(tasks[n]))]
    out.append(f"AC1 {root}: reaches {sorted(r)} -> destroy tasks: {bad or 'none'}")
    ok &= not bad
for n, t in tasks.items():
    for s in scripts(t):
        if "tofu destroy" in s and "auto-approve" in s: ok = False; out.append(f"AC2 FAIL auto-approve destroy in {n}")
out.append("AC2: no '-auto-approve' on any destroy" )
out.append("AC5: '|| true' present anywhere: " + str(any("|| true" in s for t in tasks.values() for s in scripts(t))))
out.append("interactive: " + str({n: tasks[n].get("interactive") for n in ["infra","infra-destroy","rebuild"]}))
# 3. behavioural: run infra script with a stub tofu
def run_infra(actions, answer):
    d = pathlib.Path(tempfile.mkdtemp()); (d/"terraform").mkdir(); log = d/"calls.log"
    stub = d/"bin"; stub.mkdir()
    (stub/"tofu").write_text(f'''#!/bin/sh
echo "$*" >> {log}
case "$1" in
  plan) touch tfplan ;;
  show) printf '{{"resource_changes":[{{"address":"x","change":{{"actions":{actions}}}}}]}}' ;;
esac
''')
    os.chmod(stub/"tofu", 0o755)
    env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}")
    p = subprocess.run(["sh","-c","-o","errexit", scripts(tasks["infra"])[0]], cwd=d, env=env,
                       input=answer, capture_output=True, text=True)
    calls = log.read_text().split("\n") if log.exists() else []
    applied = any(c.startswith("apply") for c in calls)
    leftover = (d/"terraform"/"tfplan").exists(); shutil.rmtree(d)
    return p.returncode, applied, leftover
for actions, ans, want_apply in [('["create"]', "", True), ('["no-op"]', "", True),
                                 ('["update"]', "", True), ('["delete","create"]', "no\n", False),
                                 ('["create","delete"]', "\n", False), ('["delete"]', "yes\n", True)]:
    rc, applied, left = run_infra(actions, ans)
    good = applied == want_apply and left is False
    ok &= good
    out.append(f"AC4 infra actions={actions} answer={ans.strip()!r}: rc={rc} applied={applied} tfplan_left={left} {'OK' if good else 'FAIL'}")
# 4. rebuild confirmation step
for ans, want_rc in [("homelab\n", 0), ("nope\n", 1), ("\n", 1)]:
    p = subprocess.run(["sh","-c","-o","errexit", scripts(tasks["rebuild"])[0]], input=ans,
                       env=dict(os.environ, CLUSTER_NAME="homelab"), capture_output=True, text=True)
    good = p.returncode == want_rc; ok &= good
    out.append(f"AC3 rebuild answer={ans.strip()!r}: rc={p.returncode} {'OK' if good else 'FAIL'}")
out.append(f"rebuild steps after prompt: {steps(tasks['rebuild'])}")
print("\n".join(out)); print("RESULT:", "PASS" if ok else "FAIL")
