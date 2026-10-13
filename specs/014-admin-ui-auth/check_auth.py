"""Checks #14 (AC1-AC4) against rendered charts.  usage: python3 -I check_auth.py <render dir> <repo root>"""
import re, subprocess, sys, pathlib
O, repo = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
read = lambda n: (O / f"{n}.yaml").read_text()
docs = lambda t: [d for d in t.split("\n---") if d.strip()]
kind = lambda d, k: re.search(rf"^kind: {k}\s*$", d, re.M)
named = lambda d, n: re.search(rf"^  name: {n}\s*$", d, re.M)
ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
MW = "traefik.ingress.kubernetes.io/router.middlewares"

lh = [d for d in docs(read("longhorn")) if kind(d, "Ingress")]
check("AC1 Longhorn Ingress uses longhorn-system-basic-auth", lh and re.search(rf"{MW}: \"?longhorn-system-basic-auth@kubernetescrd", lh[0]))
dash = [d for d in docs(read("traefik")) if kind(d, "IngressRoute") and "traefik-dashboard" in d]
check("AC1 Traefik dashboard route uses basic-auth", dash and re.search(r"middlewares:\s+- name: basic-auth", dash[0]))

ag = docs(read("adguard"))
ing = [d for d in ag if kind(d, "Ingress")]
check("AC2 AdGuard Ingress adguard.homelab.local with adguard-basic-auth",
      ing and "host: adguard.homelab.local" in ing[0] and re.search(rf"{MW}: \"?adguard-basic-auth@kubernetescrd", ing[0]))
lb_ui = [d for d in ag if kind(d, "Service") and "type: LoadBalancer" in d and re.search(r"targetPort: 3000", d)]
check("AC2 no LoadBalancer exposes AdGuard UI port 3000", not lb_ui)

ia = docs(read("ingress-auth"))
for ns in ["longhorn-system", "adguard", "traefik"]:
    es = [d for d in ia if kind(d, "ExternalSecret") and named(d, "basic-auth") and f"namespace: {ns}" in d]
    mw = [d for d in ia if kind(d, "Middleware") and named(d, "basic-auth") and f"namespace: {ns}" in d]
    check(f"AC3 {ns}: ExternalSecret basic-auth (users <- ingress-auth.htpasswd)", es and re.search(
        r"secretKey: users\s+remoteRef:\s+key: ingress-auth\s+property: htpasswd", es[0]) and "name: openbao" in es[0])
    check(f"AC3 {ns}: Middleware basicAuth -> secret basic-auth", mw and re.search(r"basicAuth:\s+secret: basic-auth", mw[0]))
g = subprocess.run(["grep", "-rnE", r"\$2[aby]\$|\$apr1\$|\{SHA\}", str(repo / "kubernetes")], capture_output=True, text=True)
check("AC3 no htpasswd hashes in kubernetes/", g.stdout == "", g.stdout.strip()[:200])

wave = lambda app: int(re.search(r'sync-wave: "(\d+)"', (repo / f"kubernetes/apps/infrastructure/{app}/application.yaml").read_text()).group(1)) \
    if (repo / f"kubernetes/apps/infrastructure/{app}/application.yaml").exists() else -1
check("AC4 ingress-auth syncs after external-secrets and traefik",
      wave("ingress-auth") > wave("external-secrets") and wave("ingress-auth") > wave("traefik"),
      f"ingress-auth={wave('ingress-auth')} eso={wave('external-secrets')} traefik={wave('traefik')}")
print("RESULT:", "PASS" if all(ok) else "FAIL"); sys.exit(0 if all(ok) else 1)
