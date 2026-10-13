# Retro: 015-pin-metallb-ips

Ticket: gh:15 · Size: standard · PR: https://github.com/bxker/homelab/pull/45

## Metrics
| Metric | Value |
|---|---|
| Duration (intake → deliver) | ~0:10 agent time, plus gate waits |
| Time per stage | spec ~1m, plan ~3m (fetching/packaging charts), implement ~4m, verify ~1m |
| Gate rework (spec / plan / deliver) | 0 / 0 / 0 |
| Tasks | 3 (fallback mode, sequential) |
| Review first-pass rate | 3/3 |
| Retries | 0 |
| Interventions | 0 |
| Criteria passed | 5/5 (offline; live IP moves and router DHCP left to owner) |

## Reflections
1. skipped
2. skipped
3. skipped

## Proposed improvements
- `kubernetes` skill: when a chart isn't a release asset, `git clone --branch <tag>` its source and
  `helm package` it into the scratchpad (worked for traefik 32.1.1).
- spec-agent analyst: for any change to externally visible addresses (LB IPs, DNS), always ask for
  the live values first. Here the docs and values already disagreed (.201 vs .200).
- The three render checks (#11, #13, #15) should move into CI under #28 so they run on every PR.
