"""Checks AC1–AC4 for #13 against a rendered prometheus-stack chart.
usage: python3 -I check_render.py <rendered.yaml> <repo root>"""
import base64, re, subprocess, sys, pathlib
rendered, repo = pathlib.Path(sys.argv[1]).read_text(), pathlib.Path(sys.argv[2])
docs = [d for d in rendered.split("\n---") if d.strip()]
kind = lambda d, k: re.search(rf"^kind: {k}\s*$", d, re.M)
results = []
def check(name, cond, detail=""):
    results.append(cond); print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")

es = [d for d in docs if kind(d, "ExternalSecret") and "name: grafana-admin" in d]
d = es[0] if es else ""
check("AC1 ExternalSecret grafana-admin rendered", len(es) == 1)
check("AC1 apiVersion external-secrets.io/v1", "apiVersion: external-secrets.io/v1\n" in d)
check("AC1 store openbao ClusterSecretStore", re.search(r"name: openbao\s+kind: ClusterSecretStore", d) is not None)
for sk, prop in [("admin-user", "admin_user"), ("admin-password", "admin_password")]:
    check(f"AC1 {sk} <- secret/grafana.{prop}",
          re.search(rf"secretKey: {sk}\s+remoteRef:\s+key: grafana\s+property: {prop}", d) is not None)

dep = [x for x in docs if kind(x, "Deployment") and "GF_SECURITY_ADMIN_PASSWORD" in x]
check("AC2 grafana Deployment found", len(dep) == 1)
refs = re.findall(r"- name: (GF_SECURITY_ADMIN_(?:USER|PASSWORD))\s+valueFrom:\s+secretKeyRef:\s+name: (\S+)\s+key: (\S+)", dep[0] if dep else "")
check("AC2 admin env vars read grafana-admin", bool(refs) and all(n == "grafana-admin" for _, n, _ in refs), str(refs))
sidecar = re.findall(r"- name: REQ_(?:USERNAME|PASSWORD)\s+valueFrom:\s+secretKeyRef:\s+name: (\S+)", dep[0] if dep else "")
check("AC2 sidecar reload creds read grafana-admin", bool(sidecar) and set(sidecar) == {"grafana-admin"}, str(sidecar))
literal = re.findall(r"admin-password: \"?([A-Za-z0-9+/=]+)", rendered)
check("AC2 no chart-rendered admin-password literal", not literal,
      str([base64.b64decode(x).decode(errors="replace") for x in literal]))

g = subprocess.run(["grep", "-rniE", "change_?me", str(repo / "kubernetes")], capture_output=True, text=True)
check("AC3 no change_me placeholders under kubernetes/", g.stdout == "", g.stdout.strip())

wave = lambda app: re.search(r'sync-wave: "(\d+)"', (repo / f"kubernetes/apps/infrastructure/{app}/application.yaml").read_text()).group(1)
check("AC4 prometheus-stack wave > external-secrets wave", int(wave("prometheus-stack")) > int(wave("external-secrets")),
      f"{wave('prometheus-stack')} vs {wave('external-secrets')}")
print("RESULT:", "PASS" if all(results) else "FAIL")
sys.exit(0 if all(results) else 1)
