---
phase: 02-client-install-paths
plan: "03"
subsystem: install
tags: [install, claude-desktop, manifest, cli, security, test]
dependency_graph:
  requires: [02-02]
  provides: [claude-desktop-write-path-verified, manifest-consistency-locked]
  affects: [test/cli.test.js]
tech_stack:
  added: []
  patterns: [end-to-end write assertion, invariant guard, manifest consistency test]
key_files:
  created: []
  modified:
    - test/cli.test.js
decisions:
  - CLI-05 invariant asserted in test (fail message points at 02-02), not silently restored in lib/config.js
  - manifest.json was already consistent (no drift); no source change required
  - statSync mode check guarded by process.platform !== "win32" for CI portability
  - manifest env key comparison uses .sort() for order-independent deep-equal
metrics:
  duration: 5
  completed: "2026-06-09"
---

# Phase 02 Plan 03: Claude Desktop Write-Path Verification Summary

## One-liner

Claude Desktop write-path verified end-to-end (npx -y github:omilia/mcp run, correct macOS path, mode 0o600) and .mcpb manifest env/args consistency locked by test — no lib/ source modified.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Claude Desktop write-path and manifest tests | fe3d69a | test/cli.test.js |
| 2 | Manifest consistency verified (no drift) | fe3d69a | manifest.json (unchanged) |

## What Was Done

### Task 1 — End-to-end Claude Desktop write-path verification

Added four new tests to `test/cli.test.js`:

1. **CLI-05 invariant guard**: Imports `JSON_MCP_CLIENTS` from `lib/config.js` and asserts `JSON_MCP_CLIENTS.has("claude") === true`. Failure message explicitly points at 02-02 as the defect source. This plan does NOT modify `lib/config.js`.

2. **Path resolution test**: Asserts `clientConfigPath("claude", { HOME: "/home/user" })` returns `/home/user/Library/Application Support/Claude/claude_desktop_config.json` — the canonical macOS Claude Desktop path.

3. **End-to-end write test (CLI-04)**: Runs `runCli(["init", "--client", "claude", "--write", "--path", tmpfile, "--base-url", "https://ocp.example.com", "--access-token", "pat-desktop-1234"])`, then asserts: exit 0, file parses as valid JSON, `mcpServers.OCP.command === "npx"`, `mcpServers.OCP.args` deep-equals `["-y", "github:omilia/mcp", "run"]` (CLI-05 consistency), env carries supplied base URL and token, file mode is `0o600` (T-02-07).

4. **Manifest consistency test (CLI-04, T-02-08)**: Reads `manifest.json` from the repo root via `readFileSync + JSON.parse`, asserts: `mcp_config.args` last element is `"run"`, some arg contains `bin/ocp-mcp.js`, and `Object.keys(mcp_config.env).sort()` deep-equals `Object.keys(getEnvBlock("pat", { useEnvVars: true })).sort()` — locking `OCP_BASE_URL + OCP_ACCESS_TOKEN` as the PAT env contract.

### Task 2 — manifest.json verification

Verified `manifest.json` is internally consistent:
- `server.entry_point`: `"bin/ocp-mcp.js"` — matches `mcp_config.args[0]` path (`"${__dirname}/bin/ocp-mcp.js"`)
- `mcp_config.args`: `["${__dirname}/bin/ocp-mcp.js", "run"]` — last element is `"run"`, prior element contains `bin/ocp-mcp.js`
- `mcp_config.env` keys: `OCP_BASE_URL`, `OCP_ACCESS_TOKEN` — exactly match PAT `getEnvBlock` output
- Bundle uses `node` (not `npx`) — correct for self-contained bundle behavior; intentional distinction from the Claude Desktop JSON write path

No drift found. `manifest.json` left unchanged.

## Verification Results

- `node --test` full suite: **116 pass, 0 fail** (112 previous + 4 new tests)
- `JSON_MCP_CLIENTS.has("claude")` → `true` (CLI-05 invariant confirmed)
- `clientConfigPath("claude", {HOME:"/home/user"})` → `/home/user/Library/Application Support/Claude/claude_desktop_config.json`
- End-to-end claude write: exit 0, valid JSON, `npx -y github:omilia/mcp run`, correct env, mode `0o600`
- manifest.json env keys deep-equal PAT getEnvBlock keys; args end with `"run"`

## Deviations from Plan

None — plan executed exactly as written. manifest.json was already consistent; no correction required.

## Known Stubs

None.

## Threat Flags

No new threat surface introduced. T-02-07, T-02-08, T-02-09 mitigations verified by test assertions.

## Self-Check: PASSED

- test/cli.test.js modified: confirmed
- manifest.json unchanged (no drift): confirmed
- Commit fe3d69a exists: confirmed
- Full suite 116 pass 0 fail: confirmed
- JSON_MCP_CLIENTS.has("claude") === true: confirmed
- clientConfigPath("claude") returns macOS path: confirmed
- End-to-end write uses npx -y github:omilia/mcp run: confirmed
- File mode 0o600 asserted: confirmed
- manifest env keys match PAT getEnvBlock: confirmed
