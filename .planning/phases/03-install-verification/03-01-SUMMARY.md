---
phase: 03-install-verification
plan: "01"
subsystem: preflight
tags: [node, uv, prerequisites, injectable-spawn, security]
dependency_graph:
  requires: []
  provides: [checkNode, checkUv, checkPrerequisites]
  affects: [lib/preflight.js, test/preflight.test.js]
tech_stack:
  added: []
  patterns: [injectable-spawn (deps.spawn ?? spawnSync), TDD red-green]
key_files:
  created:
    - lib/preflight.js
    - test/preflight.test.js
  modified: []
decisions:
  - "Canonical spawn contract (deps.spawn ?? spawnSync) mirrored from lib/install.js — single injection surface per function"
  - "Raw stdout never copied into returned fields or hints — only the parsed version token is used (VER-03)"
  - "checkPrerequisites passes the same deps object to both sub-checks so a single fake spawn drives the full aggregate"
metrics:
  duration_minutes: 6
  completed: "2026-06-09"
  tasks: 2
  files: 2
requirements: [VER-01]
---

# Phase 03 Plan 01: Preflight prerequisite checks Summary

Prerequisite check module `lib/preflight.js` with injectable spawn — `checkNode` (node >= 20 required), `checkUv` (uv on PATH required), and `checkPrerequisites` aggregator — all unit-tested with fake spawn and a planted-secret assertion.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for checkNode, checkUv, checkPrerequisites | b600150 | test/preflight.test.js |
| 2 (GREEN) | Implement checkNode, checkUv, checkPrerequisites | 62a3b4d | lib/preflight.js |

## Verification

- `node --test test/preflight.test.js` — 15/15 pass
- `npm test` — 131/131 pass (116 prior + 15 new; no regressions)
- `grep -n "deps.spawn ?? spawnSync" lib/preflight.js` — confirmed at lines 27 and 71

## Behavior Delivered

- `checkNode` with `v20.11.1` stdout → `{ name: "node", ok: true, found: "18" }`
- `checkNode` with `v18.20.0` stdout → `{ name: "node", ok: false, found: "18", hint: "...https://nodejs.org..." }`
- `checkNode` on ENOENT → `{ name: "node", ok: false, found: null, hint: "...https://nodejs.org..." }`
- `checkNode` with unparseable stdout → `ok: false, found: null`
- `checkUv` with status 0 → `{ name: "uv", ok: true }`
- `checkUv` on ENOENT → `{ name: "uv", ok: false, hint: "...https://github.com/astral-sh/uv..." }`
- `checkPrerequisites` both present → `{ ok: true, missing: [] }`
- `checkPrerequisites` uv missing → `{ ok: false, missing: [uvResult] }`
- `checkPrerequisites` both missing → `{ ok: false, missing: [nodeResult, uvResult] }`

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-03-01 (VER-03) | Raw stdout not echoed — only parsed version token stored in `found`; secret-planted assertion added to test suite |
| T-03-03 | All spawn calls wrapped in try/catch; unparseable stdout → `ok: false, found: null`; never throws |

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED commit: b600150 `test(03-01): add failing tests for checkNode, checkUv, checkPrerequisites`
- GREEN commit: 62a3b4d `feat(03-01): implement checkNode, checkUv, checkPrerequisites in lib/preflight.js`

## Self-Check: PASSED

- [x] lib/preflight.js exists and exports checkNode, checkUv, checkPrerequisites
- [x] test/preflight.test.js exists with 15 tests
- [x] b600150 exists in git log
- [x] 62a3b4d exists in git log
- [x] `deps.spawn ?? spawnSync` present at lines 27 and 71
- [x] Full suite: 131 tests, 0 failures
