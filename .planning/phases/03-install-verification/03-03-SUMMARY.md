---
phase: 03-install-verification
plan: "03"
subsystem: verify
tags: [verify, preflight, smoketest, cli-wiring, injectable-io, security, no-leak, tdd]
dependency_graph:
  requires: [lib/preflight.js checkPrerequisites, lib/smoketest.js smokeTest]
  provides: [runVerification, buildVerifySummary, --no-verify-install flag, io.verify injection surface]
  affects: [lib/verify.js, lib/cli.js, bin/ocp-mcp.js, test/verify.test.js]
tech_stack:
  added: []
  patterns:
    - injectable-verify (io.verify ?? NOOP_VERIFY)
    - CANONICAL VERIFY CONTRACT (bin injects real runVerification; tests inject stubs)
    - async-on-demand (finishInit returns Promise only when io.verify is injected)
    - whitelist-only summary rendering (VER-03)
key_files:
  created:
    - lib/verify.js
    - test/verify.test.js
  modified:
    - lib/cli.js
    - bin/ocp-mcp.js
decisions:
  - "io.verify injection surface: finishInit only goes async when io.verify is present; absent = synchronous no-op path keeps existing --write tests green without uv"
  - "bin/ocp-mcp.js injects process.verify = runVerification so production CLI path runs real verification"
  - "buildVerifySummary reads only whitelisted fields (name, ok, hint, found, toolCount, reason) — credentials structurally excluded (VER-03)"
  - "runVerification skips smokeTest when prereqs.ok is false — cannot smoke-test without uv/node"
  - "--no-verify-install opt-out flag added to parseInitOptions; default verifyInstall:true"
metrics:
  duration_minutes: 18
  completed: "2026-06-09"
  tasks: 2
  files: 4
requirements: [VER-01, VER-02, VER-03]
---

# Phase 03 Plan 03: Install Verification Orchestration Summary

`lib/verify.js` orchestrates `checkPrerequisites` then (conditionally) `smokeTest` and renders a per-check [✓]/[✗] PASS/FAIL summary; wired into `finishInit` via `io.verify` injection surface with `--no-verify-install` opt-out and production inject in `bin/ocp-mcp.js`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for runVerification, buildVerifySummary, CLI wiring | 710f002 | test/verify.test.js |
| 2 (GREEN) | Implement runVerification/buildVerifySummary and wire into finishInit | f22e948 | lib/verify.js, lib/cli.js, bin/ocp-mcp.js |

## Verification

- `node --test test/verify.test.js` — 13/13 pass
- `node --test` (full suite) — 155/155 pass (142 prior + 13 new; 0 regressions)
- `grep -n "no-verify-install" lib/cli.js` — confirmed at lines 251 and 362
- `grep -n "io\.verify" lib/cli.js` — confirmed at lines 74, 76, 108, 110
- PAT_INIT_GOLDEN_SHA256 golden-SHA test passes — `--print` path untouched by verification

## Behavior Delivered

- `buildVerifySummary({ checks:[node✓,uv✓], prereqsOk:true, smoke:{ok:true,toolCount:3} })` → "Result: PASS"
- `buildVerifySummary` with uv missing → "[✗] uv — hint", smoke "skipped (prerequisites missing)", "Result: FAIL"
- `buildVerifySummary` with smoke fail → "[✗] server smoke test — reason", "Result: FAIL"
- `runVerification` with all-pass deps → `{ ok: true, summary }` with "Result: PASS"
- `runVerification` with prereq fail → `{ ok: false }`, smokeTest NOT invoked
- `runVerification` never rejects — defensive try/catch wraps entire body
- `--write` with `io.verify = passing stub` → exit 0, summary on stdout
- `--write` with `io.verify = failing stub` → non-zero exit, "Result: FAIL" on stdout
- `--write --no-verify-install` → io.verify NOT called, exit 0
- `--client claude --print` → PAT golden-SHA unchanged (verification gated out on print)
- Planted token "leak-tok-9999" absent from all stdout/stderr (VER-03)
- Production bin: `process.verify = runVerification` → real verification on install

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-03-08 (VER-03) | buildVerifySummary renders only whitelisted fields (name, ok, hint, found, toolCount, reason); no-leak test asserts planted token absent from summary and all stdout/stderr |
| T-03-09 | Always emits "Result: PASS" or "Result: FAIL" line; exit code 0/non-zero folded from verification result |
| T-03-10 | Verification gated to non-print + verifyInstall + io.verify present; --print path untouched; golden-SHA + --write tests re-run as regression gate (0 failures) |
| T-03-11 | Inherited from 03-02: bounded timeout + child kill; runVerification awaits bounded smokeTest |
| T-03-SC | No package installs — ESM imports only |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical backward compat] io.verify gated on presence, not injected default**

- **Found during:** Task 2 implementation
- **Issue:** The plan proposed defaulting `io.verify` to NOOP_VERIFY when absent. However, making `finishInit` async (returning Promise) unconditionally would break the 4 existing synchronous `--write` tests that assert `exitCode === 0` directly without awaiting.
- **Fix:** The async code path is only entered when `io.verify` is actually injected (`io.verify` is truthy). When absent, `finishInit` returns a synchronous integer 0 as before. Production path restored by having `bin/ocp-mcp.js` inject `process.verify = runVerification`.
- **Files modified:** lib/cli.js, bin/ocp-mcp.js
- **Commit:** f22e948

## TDD Gate Compliance

- RED commit: 710f002 `test(03-03): add failing tests for runVerification, buildVerifySummary, CLI wiring`
- GREEN commit: f22e948 `feat(03-03): implement runVerification/buildVerifySummary and wire into finishInit`

## Known Stubs

None — all fields are wired. The `io.verify` no-op for non-injected callers is intentional (production path injects real `runVerification` via `bin/ocp-mcp.js`).

## Self-Check: PASSED

- [x] lib/verify.js exists (exports runVerification async + buildVerifySummary pure)
- [x] test/verify.test.js exists (13 tests)
- [x] lib/cli.js contains `--no-verify-install` and `io.verify` wiring
- [x] bin/ocp-mcp.js injects `process.verify = runVerification`
- [x] 710f002 exists in git log (RED)
- [x] f22e948 exists in git log (GREEN)
- [x] Full suite: 155 tests, 0 failures
- [x] PAT golden-SHA test passes
- [x] No-leak assertion: "leak-tok-9999" absent from stdout/stderr
