---
phase: 02-client-install-paths
plan: "02"
subsystem: install
tags: [install, claude-code, spawn, cli, security, migration]
dependency_graph:
  requires: [02-01]
  provides: [claude-code-install-path]
  affects: [lib/install.js, lib/cli.js, lib/config.js, test/install.test.js, test/cli.test.js]
tech_stack:
  added: [node:child_process spawnSync injectable]
  patterns: [injectable spawn, masked snippet, TDD RED-GREEN]
key_files:
  created:
    - lib/install.js
    - test/install.test.js
  modified:
    - lib/cli.js
    - lib/config.js
    - test/cli.test.js
decisions:
  - installClaudeCode uses single deps.spawn injection surface; finishInit forwards io.spawn ?? spawnSync
  - buildSnippet is a shared helper used for both CLI-absent and print mode to ensure identical masked output
  - claudeAvailable wraps spawn in try/catch to treat ENOENT as false without throwing
  - claude-code removed from JSON_MCP_CLIENTS but retained in SUPPORTED_CLIENTS so finishInit guard still accepts it
metrics:
  duration: 15
  completed: "2026-06-09"
---

# Phase 02 Plan 02: Claude Code Install via CLI Summary

## One-liner

Claude Code now installed via `claude mcp add OCP --scope user --env K=V ... -- npx -y github:omilia/mcp run` with injectable spawn for test assertion, graceful CLI-absent masked fallback, and full Phase-1 test migration.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 RED | Add failing tests for install.js | ad421ca | test/install.test.js |
| 1 GREEN | Implement lib/install.js | 44a84f8 | lib/install.js |
| 2a | Wire claude-code through installClaudeCode in cli.js + config.js | cd93b76 | lib/cli.js, lib/config.js |
| 2b | Migrate all claude-code tests in test/cli.test.js | efd005e | test/cli.test.js |

## What Was Done

### Task 1 — lib/install.js (TDD)

Created `lib/install.js` with three exports:

- `buildClaudeMcpAddArgs(opts)`: builds the `claude mcp add` argv array. Derives env pairs via `getEnvBlock(authChoice, opts)` from `lib/config.js` (single source of truth). The token is a single array element; never shell-interpolated (T-02-03 mitigation).

- `claudeAvailable(spawn)`: calls `spawn("claude", ["--version"])` in try/catch. ENOENT or non-zero status returns false without throwing (T-02-06 mitigation).

- `installClaudeCode(options, io, deps = {})`: canonical spawn injection surface (`deps.spawn ?? spawnSync`). Three paths:
  1. `options.print === true` → emit masked snippet via `buildSnippet`, return 0 (no spawn).
  2. `!claudeAvailable(spawn)` → emit masked guidance + snippet, return 0 (CLI-03).
  3. Available → spawn `claude mcp add`, return 0/1 based on exit code.

`buildSnippet(opts)` is a private helper that renders env values through `maskSecret` before composing the human-facing command string — used for both CLI-absent and print paths so they emit identical masked output (T-02-04).

### Task 2a — lib/config.js + lib/cli.js

- `lib/config.js`: removed `claude-code` from `JSON_MCP_CLIENTS` (now `Set(["cursor","claude"])`); explicitly added `"claude-code"` to `SUPPORTED_CLIENTS` so the SUPPORTED_CLIENTS guard still accepts it; removed the `if (client === "claude-code") return ~/.claude/settings.json` branch from `clientConfigPath` so it falls through to `return undefined` (CLI-02).

- `lib/cli.js`: added `import { spawnSync } from "node:child_process"` and `import { installClaudeCode } from "./install.js"`; in `finishInit`, added the canonical dispatch before `buildClientConfig`: `if (effectiveOptions.client === "claude-code") { return installClaudeCode(effectiveOptions, io, { spawn: io.spawn ?? spawnSync }); }`.

### Task 2b — test/cli.test.js (7 edits)

1. "clientConfigPath resolves claude-code to ~/.claude/settings.json" → asserts `undefined` (CLI-02).
2. "writes claude-code config to an explicit path" → replaced with spawn-argv capture test asserting exact `mcp add ... -- npx -y github:omilia/mcp run` argv array (CLI-01).
3. WIZ-05 print test → changed `--client claude-code` to `--client cursor` (JSON client for JSON assertion).
4. Added new "claude-code --print emits the masked mcp add command, no spawn (CLI-01)" test.
5. wizard+--write test → changed first scripted answer `"1"` (claude-code) to `"2"` (claude).
6. wizard-skips-fields test → changed `--client claude-code` to `--client claude`.
7. WIZ-01/WIZ-04 confirmation-summary test → changed first scripted answer `"1"` to `"2"` (claude), preserving JSON-boundary assertion and masked tail check.

## Verification Results

- `node --test` full suite: **112 pass, 0 fail** (111 original + 1 new test added in Task 2b)
- `grep -r 'settings.json' lib/` → 0 matches (CLI-02 confirmed)
- `clientConfigPath("claude-code", {HOME:"/h"})` → `undefined` (CLI-02 confirmed)
- `JSON_MCP_CLIENTS.has("claude-code")` → `false`; `SUPPORTED_CLIENTS.has("claude-code")` → `true`
- Spawn-capture test asserts exact `claude mcp add OCP --scope user --env K=V ... -- npx -y github:omilia/mcp run` argv
- CLI-absent path: returns 0, stdout contains "mcp add", raw token absent, masked tail present
- `--print` path: returns 0, no spawn recorded, masked snippet emitted
- No `createScriptedIo` call scripts answer `"1"` (claude-code)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new threat surface introduced. All T-02-03, T-02-04, T-02-05, T-02-06, T-02-07 mitigations implemented as planned.

## Self-Check: PASSED

- lib/install.js exists: confirmed
- test/install.test.js exists: confirmed
- Commit ad421ca (RED) exists: confirmed
- Commit 44a84f8 (GREEN) exists: confirmed
- Commit cd93b76 (Task 2a) exists: confirmed
- Commit efd005e (Task 2b) exists: confirmed
- Full suite 112 pass 0 fail: confirmed
- No settings.json in lib/: confirmed
