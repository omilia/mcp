---
phase: 02-client-install-paths
verified: 2026-06-09T00:00:00Z
status: passed
score: 4/4
overrides_applied: 0
re_verification: false
---

# Phase 2: Client Install Paths Verification Report

**Phase Goal:** Claude Code installs via `claude mcp add` to the correct location; Claude Desktop installs end-to-end; all emitted config uses the GitHub distribution spec.
**Verified:** 2026-06-09
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After wizard completes for Claude Code, `claude mcp add` invoked with correct name, command (`npx -y github:omilia/mcp run`), env — NOT a write to `~/.claude/settings.json` | VERIFIED | `test/cli.test.js` line 207 asserts exact argv `["mcp","add","OCP","--scope","user","--env","OCP_BASE_URL=...","--env","OCP_ACCESS_TOKEN=...","--","npx","-y","github:omilia/mcp","run"]` via fake spawn; `grep -rc 'settings.json' lib/` = 0 matches |
| 2 | When `claude` not on PATH, print installable snippet + instructions, not silent failure | VERIFIED | `lib/install.js` lines 113–121 write guidance to `io.stdout` and return 0 on ENOENT; `test/install.test.js` lines 219–279 assert return 0, "mcp add" in stdout, raw token absent, masked tail present, no throw |
| 3 | Claude Desktop install writes config to correct location and/or `.mcpb` bundle — verified end-to-end | VERIFIED | `test/cli.test.js` line 521 runs full write to tmpfile and asserts `mcpServers.OCP.command === "npx"`, `args` deep-equals `["-y","github:omilia/mcp","run"]`, env present, mode `0o600`; `clientConfigPath("claude")` verified to resolve macOS path at line 513 |
| 4 | Every generated/written config uses `npx -y github:omilia/mcp run`, consistent across clients | VERIFIED | `PACKAGE_NAME = "github:omilia/mcp"` in `lib/config.js` line 2; `buildServerDefinition` always uses this constant; Cursor fixture asserted at `test/cli.test.js` line 49; claude Desktop write asserted at line 545; manifest.json test at line 565 asserts env keys match PAT contract |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/install.js` | `buildClaudeMcpAddArgs`, `claudeAvailable`, `installClaudeCode` with injectable spawn | VERIFIED | File exists, 142 lines, exports all three functions; single `deps.spawn ?? spawnSync` injection surface |
| `lib/config.js` | `JSON_MCP_CLIENTS` excludes `claude-code`; `SUPPORTED_CLIENTS` includes it; `clientConfigPath("claude-code")` returns `undefined` | VERIFIED | Line 15: `new Set(["cursor","claude"])`; line 19: SUPPORTED_CLIENTS includes "claude-code"; line 77: falls through to `return undefined` |
| `lib/cli.js` | `finishInit` dispatches `claude-code` to `installClaudeCode` before JSON path | VERIFIED | Lines 53–55: `if (effectiveOptions.client === "claude-code") { return installClaudeCode(effectiveOptions, io, { spawn: io.spawn ?? spawnSync }); }` |
| `test/install.test.js` | 24 tests asserting argv array, CLI-absent path (masked), print path (no spawn) | VERIFIED | 24 pass, 0 fail |
| `test/cli.test.js` | CLI-01/02/04/05 assertions; no `createScriptedIo` scripting `"1"` | VERIFIED | 36 pass, 0 fail; all scripted wizard tests use `"2"` (claude) |
| `manifest.json` | `server.mcp_config.args` ends with `"run"`, contains `bin/ocp-mcp.js`, env keys match PAT contract | VERIFIED | Asserted by test at line 565; manifest line 14: `["${__dirname}/bin/ocp-mcp.js","run"]`; env: OCP_BASE_URL + OCP_ACCESS_TOKEN |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `lib/cli.js finishInit` | `lib/install.js installClaudeCode` | `claude-code` branch dispatch with `{ spawn: io.spawn ?? spawnSync }` | WIRED | `lib/cli.js` line 54: exact canonical dispatch; imports verified at lines 1 and 12 |
| `lib/install.js` | `node:child_process spawnSync` | `deps.spawn ?? spawnSync` resolved at top of `installClaudeCode` | WIRED | Line 103: `const spawn = deps.spawn ?? spawnSync;` |
| `lib/config.js clientConfigPath("claude")` | `~/Library/Application Support/Claude/claude_desktop_config.json` | Platform path resolution | WIRED | Lines 72–74: literal path construction; asserted in test |
| `lib/cli.js writeClientConfig` | `claude_desktop_config.json` via `--path` | `writeJsonConfig` with `rootKey = "mcpServers"`, mode `0o600` | WIRED | `lib/cli.js` line 277: `writeJsonConfig(outputPath, config, "mcpServers")`; line 305: `writeFileSync(..., { mode: 0o600 })` |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces CLI and installer logic, not data-rendering components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite green | `node --test` | 116 pass, 0 fail | PASS |
| install.test.js green | `node --test test/install.test.js` | 24 pass, 0 fail | PASS |
| cli.test.js green | `node --test test/cli.test.js` | 36 pass, 0 fail | PASS |
| No `settings.json` in lib/ | `grep -rc 'settings.json' lib/` | 0 matches in all 6 lib files | PASS |
| `JSON_MCP_CLIENTS.has("claude-code")` false | Node eval | `false` | PASS |
| `SUPPORTED_CLIENTS.has("claude-code")` true | Node eval | `true` | PASS |
| `clientConfigPath("claude-code")` undefined | Node eval | `undefined` | PASS |
| `JSON_MCP_CLIENTS.has("claude")` true | Node eval | `true` | PASS |
| Zero stale `@omilia/mcp-server` in tests | `grep -rn '@omilia/mcp-server' test/` | 0 matches | PASS |

### Probe Execution

No probe scripts exist for this phase (`scripts/*/tests/probe-*.sh` not found).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-01 | 02-02 | `claude mcp add` invoked with correct argv array | SATISFIED | `test/cli.test.js` line 207 asserts exact argv; `install.test.js` line 48 asserts full PAT array |
| CLI-02 | 02-02 | `~/.claude/settings.json` write path removed | SATISFIED | `JSON_MCP_CLIENTS` excludes `claude-code`; `clientConfigPath("claude-code")` returns `undefined`; 0 `settings.json` refs in lib/ |
| CLI-03 | 02-02 | CLI-absent graceful fallback | SATISFIED | `installClaudeCode` returns 0 with masked snippet on ENOENT; 5 tests in `install.test.js` cover this path |
| CLI-04 | 02-03 | Claude Desktop write path verified end-to-end + manifest consistency | SATISFIED | End-to-end write test in `cli.test.js` line 521; manifest test at line 565 |
| CLI-05 | 02-01, 02-03 | GitHub spec (`npx -y github:omilia/mcp run`) across all clients | SATISFIED | `PACKAGE_NAME = "github:omilia/mcp"` is single source of truth; Cursor fixture, claude write test, and manifest test all assert this spec |

### Anti-Patterns Found

No TBD, FIXME, or XXX markers in any file modified by this phase. "placeholder" occurrences in `lib/config.js` and `lib/cli.js` refer to product-intended literal default values (`"your-ocp-base-url"`, etc.) — not implementation stubs. No empty implementations, no return null, no orphaned artifacts found.

### Human Verification Required

None. All success criteria are verifiable programmatically. The test suite exercises the install paths via injectable spawn, removing dependency on a real `claude` binary.

---

## Gaps Summary

No gaps. All four success criteria and all five CLI requirements (CLI-01 through CLI-05) are verified by codebase evidence and a green test suite (116 pass, 0 fail).

---

_Verified: 2026-06-09T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
