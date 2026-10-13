"""Checks #16 (AC1-AC5) statically.  usage: python3 check_k3s.py <repo root>   (needs PyYAML)"""
import json, re, sys, pathlib, yaml
repo = pathlib.Path(sys.argv[1]); ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
inv = yaml.safe_load((repo / "ansible/inventory.yml").read_text())
plays = yaml.safe_load((repo / "ansible/playbooks/k3s.yml").read_text())
tasks = [(p.get("name"), t) for p in plays for t in p.get("tasks", [])]
text = (repo / "ansible/playbooks/k3s.yml").read_text()

ver = inv["all"]["vars"].get("k3s_version")
check("AC1 k3s_version defined once in inventory all.vars", bool(ver) and (repo / "ansible/inventory.yml").read_text().count("k3s_version:") == 1, ver)
installs = [t for _, t in tasks if str(t.get("name", "")).startswith("Install k3s")
            and any(k in t for k in ("ansible.builtin.command", "ansible.builtin.shell"))]
creates = lambda t: t.get("args", {}).get("creates") or (t.get("ansible.builtin.command") or {}).get("creates")
check("AC1 two k3s install tasks", len(installs) == 2, [t["name"] for t in installs])
check("AC1 every install sets INSTALL_K3S_VERSION={{ k3s_version }}",
      installs and all(str(t.get("environment", {}).get("INSTALL_K3S_VERSION", "")).replace(" ", "") == "{{k3s_version}}" for t in installs))
check("AC2 no get.k3s.io anywhere", "get.k3s.io" not in text)
dl = [t for _, t in tasks if "ansible.builtin.get_url" in t]
check("AC2 install.sh downloaded from the pinned tag", dl and all(
    "raw.githubusercontent.com/k3s-io/k3s/{{ k3s_version }}/install.sh" in t["ansible.builtin.get_url"]["url"] for t in dl))

def cmdline(t):
    m = t.get("ansible.builtin.command") or t.get("ansible.builtin.shell") or ""
    return json.dumps(m) + json.dumps(t.get("environment", {}))
check("AC3 no command or command env mentions the token", not [t["name"] for _, t in tasks if "k3s_token" in cmdline(t) or "K3S_TOKEN" in cmdline(t)])
cfg = [t for _, t in tasks if "/etc/rancher/k3s/config.yaml" == (t.get("ansible.builtin.copy") or {}).get("dest")]
check("AC3 agents get config.yaml (root, 0600, no_log) with server and token", cfg and all(
    t.get("no_log") is True and t["ansible.builtin.copy"].get("mode") == "0600" and t["ansible.builtin.copy"].get("owner") == "root"
    and "k3s_token" in str(t["ansible.builtin.copy"].get("content")) and "server" in str(t["ansible.builtin.copy"].get("content")) for t in cfg))
tok = [t for _, t in tasks if "k3s_token" in json.dumps(t) or "node-token" in json.dumps(t)]
check("AC3 every task touching the token is no_log", tok and all(t.get("no_log") is True for t in tok if "wait_for" not in json.dumps(t)),
      [t["name"] for t in tok if t.get("no_log") is not True])
check("AC4 every install keeps creates: /usr/local/bin/k3s", installs and all(creates(t) == "/usr/local/bin/k3s" for t in installs))

guard = [p for p in plays if any("ansible.builtin.assert" in t for t in p.get("tasks", []))]
check("AC6 a version-check play runs first, on all k3s nodes, any_errors_fatal",
      guard and plays[0] is guard[0] and set(re.split(r"[:,]", plays[0]["hosts"])) == {"k3s_cp", "k3s_workers"} and plays[0].get("any_errors_fatal") is True)

rv = json.loads((repo / "renovate.json").read_text())
cm = [m for m in rv.get("customManagers", []) if m.get("depNameTemplate") == "k3s-io/k3s"]
check("AC5 Renovate custom manager for k3s-io/k3s (github-releases)", cm and cm[0].get("datasourceTemplate") == "github-releases")
if cm:
    pyre = lambda s: re.sub(r"\(\?<(\w+)>", r"(?P<\1>", s)
    files = [p for p in cm[0]["managerFilePatterns"] if re.search(pyre(p.strip("/")), "ansible/inventory.yml")]
    m = re.search(pyre(cm[0]["matchStrings"][0]), (repo / "ansible/inventory.yml").read_text())
    vr = re.match(pyre(cm[0]["versioningTemplate"].removeprefix("regex:")), ver or "")
    check("AC5 file pattern matches ansible/inventory.yml", files)
    check("AC5 matchString captures the pinned version", m and m.group("currentValue") == ver, m and m.group("currentValue"))
    check("AC5 versioning regex parses it", vr and vr.group("build"), vr and vr.groupdict())
print("RESULT:", "PASS" if all(ok) else "FAIL"); sys.exit(0 if all(ok) else 1)
