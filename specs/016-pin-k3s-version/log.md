## analyst · spec · done
2026-10-13T03:47:13Z

**Did:** Wrote spec.md: 5 criteria, 2 open questions (live version, ansible tooling).

**Evidence:**
- k3s install.sh @ v1.34.12+k3s1 `setup_env`: an explicit `agent` argument selects agent mode without K3S_URL
- `git ls-remote` k3s tags: newest v1.34.12, v1.35.9, v1.36.5, v1.37.1

**Changed files:** `specs/016-pin-k3s-version/spec.md`

**Open issues:** OQ1 live version (owner), OQ2 tooling

**Next:** Spec gate
