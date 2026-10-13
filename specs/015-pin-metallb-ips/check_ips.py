"""Checks #15 IP pinning (AC1-AC5) against rendered charts.
usage: python3 -I check_ips.py <traefik.yaml> <adguard.yaml> <metallb.yaml> <repo root>"""
import ipaddress as ip, re, subprocess, sys, pathlib
tr, ag, mb = (pathlib.Path(p).read_text() for p in sys.argv[1:4]); repo = pathlib.Path(sys.argv[4])
TRAEFIK, DNS, UI = "192.168.1.200", "192.168.1.201", "192.168.1.203"
docs = lambda t: [d for d in t.split("\n---") if d.strip()]
ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
def svc(t, name=None):
    return [d for d in docs(t) if re.search(r"^kind: Service\s*$", d, re.M) and "type: LoadBalancer" in d
            and (name is None or re.search(rf"^  name: {name}\s*$", d, re.M))]
pin = lambda d: (re.findall(r"metallb\.io/loadBalancerIPs: \"?([\d.,]+)\"?", d) or [None])[0]

t = svc(tr); check("AC1 one Traefik LB Service", len(t) == 1)
check("AC1 Traefik pinned", t and pin(t[0]) == TRAEFIK, t and pin(t[0]))
d, u = svc(ag, "adguard-home-dns"), svc(ag, "adguard-home-http")
check("AC2 AdGuard DNS pinned", d and pin(d[0]) == DNS, d and pin(d[0]))
check("AC2 AdGuard UI pinned", u and pin(u[0]) == UI, u and pin(u[0]))
g = subprocess.run(["grep", "-rn", "metallb.universe.tf", str(repo / "kubernetes")], capture_output=True, text=True)
check("AC2 no deprecated metallb.universe.tf key", g.stdout == "", g.stdout.strip())
rw = re.findall(r'domain: "\*\.homelab\.local"\s+answer: (\S+)', ag)
check("AC3 rewrite answer == Traefik pin", rw == [TRAEFIK] and t and pin(t[0]) == rw[0], rw)

pools = {}
for p in docs(mb):
    if re.search(r"^kind: IPAddressPool\s*$", p, re.M):
        name = re.search(r"^  name: (\S+)", p, re.M).group(1)
        rng = re.findall(r"- (\d+\.\d+\.\d+\.\d+)-(\d+\.\d+\.\d+\.\d+)", p)
        auto = re.search(r"autoAssign: (\w+)", p)
        pools[name] = ([(ip.ip_address(a), ip.ip_address(b)) for a, b in rng], auto.group(1) if auto else "true")
static = [n for n, (_, a) in pools.items() if a == "false"]
check("AC5 exactly one autoAssign:false pool", len(static) == 1, str({n: a for n, (_, a) in pools.items()}))
inside = lambda addr, n: any(a <= ip.ip_address(addr) <= b for a, b in pools[n][0])
check("AC5 every pin inside the static pool", static and all(inside(x, static[0]) for x in (TRAEFIK, DNS, UI)))
spans = sorted(r for rs, _ in pools.values() for r in rs)
check("AC5 pools don't overlap", all(spans[i][1] < spans[i + 1][0] for i in range(len(spans) - 1)), str(spans))
l2 = [p for p in docs(mb) if re.search(r"^kind: L2Advertisement\s*$", p, re.M)]
check("AC5 L2Advertisement covers every pool", l2 and all(re.search(rf"- {n}\s*$", l2[0], re.M) for n in pools))
print("RESULT:", "PASS" if all(ok) else "FAIL"); sys.exit(0 if all(ok) else 1)
