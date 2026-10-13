## analyst · spec · done
2026-10-13T03:47:13Z

**Did:** Wrote spec.md: 5 criteria, 2 open questions (live version, ansible tooling).

**Evidence:**
- k3s install.sh @ v1.34.12+k3s1 `setup_env`: an explicit `agent` argument selects agent mode without K3S_URL
- `git ls-remote` k3s tags: newest v1.34.12, v1.35.9, v1.36.5, v1.37.1

**Changed files:** `specs/016-pin-k3s-version/spec.md`

**Open issues:** OQ1 live version (owner), OQ2 tooling

**Next:** Spec gate

## analyst · spec (rev 1) · done
2026-10-13T03:49:56Z

**Did:** OQ1 resolved: live version unknown (Terraform has no k3s info), so pin v1.36.5+k3s1 provisionally and added AC6 (fail loudly on mismatch).

**Changed files:** `specs/016-pin-k3s-version/spec.md`

**Next:** plan

## architect · plan · done
2026-10-13T03:49:56Z

**Did:** Wrote plan.md: 2 tasks (playbook+inventory; renovate+doc).

**Changed files:** `specs/016-pin-k3s-version/plan.md`

**Open issues:** none

**Next:** Plan gate

## implementer · T1 · done
2026-10-13T03:53:05Z

**Did:** `k3s_version` in inventory; first play checks installed k3s against it (any_errors_fatal); both installs download `install.sh` from the pinned tag (versioned filename) and run it via `command` argv with `INSTALL_K3S_VERSION`; agents read server/token from `/etc/rancher/k3s/config.yaml` (0600, no_log); token slurp/set_fact no_log.

**Evidence:**
- `check_k3s.py` → AC1–AC4, AC6 PASS (two check-script selection bugs fixed first; both selections still pass on baseline, see .runs)
- version-check play run locally: no k3s → skipped; matching → ok; mismatched v1.33.5 → both hosts fail with the message
- agent config rendered with a sample token → valid YAML, mode 600
- `ansible-playbook --syntax-check` ok; `ansible-lint` 4 failures → 0 (production profile)

**Changed files:** `ansible/inventory.yml`, `ansible/playbooks/k3s.yml`

**Next:** review T1

## infra-reviewer + security-reviewer · T1 · done
2026-10-13T03:53:05Z

**Findings:**
- MEDIUM (fixed in T1): `get_url` without `force` keeps a stale `install.sh` after a version bump → versioned filename.
- LOW: existing agents keep `K3S_URL`/`K3S_TOKEN` in `/etc/systemd/system/k3s-agent.service.env` from the old install; the new config.yaml duplicates them (no restart). Cleaning that file needs a restart, so it's left out of scope.

**Next:** commit T1, T2

## implementer · T2 · done
2026-10-13T03:54:16Z

**Did:** Renovate regex custom manager for `k3s_version` (github-releases k3s-io/k3s, +k3sN versioning) and a `k3s-upgrade` packageRule; CLAUDE.md provisioning note. Rewrote the JSON edit by hand to keep the file's compact style.

**Evidence:** `check_k3s.py` → RESULT: PASS (14/14)

**Changed files:** `renovate.json`, `CLAUDE.md`

**Next:** verify

## engine · scope note
2026-10-13T03:54:16Z

Out-of-scope fix on this branch (commit efeb270): restored `specs/014-admin-ui-auth/plan.md` and `specs/015-pin-metallb-ips/plan.md`, which the engine's own approval step had truncated before they merged. Listed at the Deliver gate.
