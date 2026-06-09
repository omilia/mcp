---
phase: 03-install-verification
plan: "02"
subsystem: smoketest
tags: [smoketest, mcp-handshake, stdio, injectable-spawn, security, no-leak]
dependency_graph:
  requires: [lib/runtime.js buildRunCommand]
  provides: [smokeTest]
  affects: [lib/smoketest.js, test/smoketest.test.js]
tech_stack:
  added: []
  patterns:
    - injectable-spawn (deps.spawn ?? nodeSpawn)
    - injectable-createInterface (deps.createInterface ?? nodeCreateInterface)
    - injectable-buildRunCommand (deps.buildRunCommand ?? buildRunCommand)
    - settled-guard (resolve exactly once across success/empty/timeout/spawn-error)
    - newline-delimited JSON-RPC 2.0 stdio handshake
key_files:
  created:
    - lib/smoketest.js
    - test/smoketest.test.js
  modified: []
decisions:
  - "Settled guard (boolean flag + single cleanup function) ensures child.kill() fires exactly once on all exit paths"
  - "Result shape restricted to ok/toolCount/hasReadGuide/reason — env and raw child output excluded (VER-03)"
  - "reason strings use static templates; child.message is included for spawn errors but OCP env values are never interpolated"
  - "createInterface also injected (deps.createInterface) to enable unit tests without spawning a real process"
  - "Integration test detected uv on PATH and passed live; skips cleanly when uv absent"
metrics:
  duration_minutes: 10
  completed: "2026-06-09"
  tasks: 2
  files: 2
requirements: [VER-02, VER-03]
---

# Phase 03 Plan 02: smokeTest MCP handshake Summary

MCP stdio smoke-test module `lib/smoketest.js` — spawns the resolved `uv run fastmcp run src/server.py:mcp` command, performs a JSON-RPC `initialize` + `tools/list` handshake, and returns a clean result object with no credential leakage.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for smokeTest handshake, no-leak, timeout, integration | 4b7c443 | test/smoketest.test.js |
| 2 (GREEN) | Implement smokeTest MCP handshake with injectable transport | 6a3c0b5 | lib/smoketest.js |

## Verification

- `node --test test/smoketest.test.js` — 11/11 pass (integration test ran live against real uv server)
- `node --test` (full suite) — 142/142 pass (131 prior + 11 new; no regressions)
- `grep -n "buildRunCommand" lib/smoketest.js` — confirmed at lines 4 and 31
- `grep -n "kill" lib/smoketest.js` — confirmed cleanup at line 67

## Behavior Delivered

- `smokeTest()` with tools `[{name:"read_guide"},{name:"x"}]` → `{ ok: true, toolCount: 2, hasReadGuide: true }`
- `smokeTest()` with `tools: []` → `{ ok: false, reason: "server returned no tools" }`
- `smokeTest({ timeoutMs: 50 })` with silent transport → `{ ok: false, reason: "smoke test timed out after 50ms" }`, `kill()` invoked once
- `smokeTest()` with ENOENT spawn → `{ ok: false, reason: "failed to start server: ..." }`, never throws
- `OCP_ACCESS_TOKEN: "leak-tok-9999"` in command.env → token absent from `JSON.stringify(result)` (VER-03)
- Integration test with real uv server → `{ ok: true, hasReadGuide: true }`

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|-----------|
| T-03-04 (VER-03) | Result object restricted to ok/toolCount/hasReadGuide/reason; env values and raw child output never copied in; no-leak test asserts planted token absent |
| T-03-05 | Module never writes child stdout/stderr to process.stdout/stderr; reason strings are static templates with no child output interpolation |
| T-03-06 | Single bounded timer (30s default); settled guard ensures child.kill() runs exactly once on success/empty/timeout/spawn-error |
| T-03-07 | child `error` event resolves ok:false with static reason; guarded integration test skips when uv absent |
| T-03-SC | No package installs — node:child_process + node:readline only |

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED commit: `4b7c443` `test(03-02): add failing tests for smokeTest handshake, no-leak, timeout, integration`
- GREEN commit: `6a3c0b5` `feat(03-02): implement smokeTest MCP handshake with injectable transport`

## Self-Check: PASSED

- [x] lib/smoketest.js exists (152 lines, exports smokeTest)
- [x] test/smoketest.test.js exists (415 lines, 11 tests)
- [x] 4b7c443 exists in git log (RED)
- [x] 6a3c0b5 exists in git log (GREEN)
- [x] `buildRunCommand` confirmed in lib/smoketest.js at lines 4 and 31
- [x] `child.kill()` in cleanup path at line 67
- [x] Full suite: 142 tests, 0 failures
- [x] No-leak assertion: "leak-tok-9999" absent from JSON.stringify(result)
- [x] Integration test: ran live (uv on PATH), returned ok:true hasReadGuide:true
