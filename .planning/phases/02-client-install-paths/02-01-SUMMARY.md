---
phase: 02-client-install-paths
plan: "01"
subsystem: test-fixtures
tags: [test, fixtures, package-name, golden-sha]
dependency_graph:
  requires: []
  provides: [green-test-baseline]
  affects: [test/cli.test.js]
tech_stack:
  added: []
  patterns: [golden-sha regression gate]
key_files:
  created: []
  modified:
    - test/cli.test.js
decisions:
  - PAT_INIT_GOLDEN_SHA256 derived from actual runCli output, not hand-copied from plan docs
metrics:
  duration: 5
  completed: "2026-06-09"
---

# Phase 02 Plan 01: Fix Stale Test Fixtures Summary

## One-liner

Updated Cursor args fixture from `@omilia/mcp-server` to `github:omilia/mcp` and recomputed the PAT golden-SHA constant from actual CLI output to restore green test baseline.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Update stale Cursor args fixture and recompute PAT golden SHA | 75e03a6 | test/cli.test.js |
| 2 | Confirm full suite green, no residual @omilia/mcp-server references | (no file changes) | — |

## What Was Done

### Task 1

Two stale fixtures in `test/cli.test.js` were corrected:

1. The `args` literal inside "builds Cursor config with inline literal placeholders by default" was changed from `["-y", "@omilia/mcp-server", "run"]` to `["-y", "github:omilia/mcp", "run"]`, matching `PACKAGE_NAME` in `lib/config.js`.

2. `PAT_INIT_GOLDEN_SHA256` was updated from `556844bc...` to `9f03b6648fc1e5573acf9bc3fc5bc0c7f56ee3f839fe5bb8acf5d4d498103647`, recomputed by running actual `init --client claude --print` output through `crypto.createHash('sha256')`. The actual emitted JSON confirms the package name is already `github:omilia/mcp` in `lib/config.js`.

### Task 2

`grep -rn '@omilia/mcp-server' test/` returned 0 matches. Full suite (`node --test`) passed 87 tests with 0 failures. No further file changes were needed.

## Verification Results

- `node --test test/cli.test.js`: 31 pass, 0 fail
- `node --test` (full suite): 87 pass, 0 fail
- `grep -rn '@omilia/mcp-server' test/` returns 0 matches
- No `lib/` source files modified

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes were introduced. Test-only changes only.

## Self-Check: PASSED

- test/cli.test.js modified: confirmed (2 lines changed)
- Commit 75e03a6 exists: confirmed
- Full suite green: 87 pass, 0 fail
