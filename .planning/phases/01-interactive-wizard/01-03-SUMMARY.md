---
phase: 01-interactive-wizard
plan: "03"
subsystem: cli-wizard-wiring
tags: [cli, wizard, tdd, security, confirmation-summary, no-tty-guard, async]
dependency_graph:
  requires: [wizard-decision-layer, wizard-io-layer]
  provides: [cli-wizard-wiring, runInit-async]
  affects: [lib/cli.js, bin/ocp-mcp.js, test/cli.test.js]
tech_stack:
  added: []
  patterns: [tdd-red-green, io-injection, promise-resolve-compat, async-sync-dual-return, finishInit-extraction]
key_files:
  created: []
  modified:
    - lib/cli.js
    - bin/ocp-mcp.js
    - test/cli.test.js
decisions:
  - "finishInit() extracted as synchronous helper; both sync and async runInit paths call it to avoid code duplication"
  - "wizard TTY guard triggers only when io.input is explicitly injected (not undefined); legacy callers without io.input fall through to placeholder-default synchronous path for backward compat"
  - "runWizard receives wizardIo = { input: io.input, output: io.stdout } to bridge runCli's {input,stdout,stderr} shape with wizard's {input,output} shape"
  - "parseInitOptions authChoice defaults to 'pat'; wizard skips authChoice prompt when already set, so scripted tests use 3 answers (client, baseUrl, accessToken) not 4"
  - "confirmation summary token masking assertion checks only the summary preamble (before '{') since the final config JSON legitimately contains the raw token in the print path"
  - "no-TTY guard requires io.input !== undefined to preserve backward compat with legacy createIo() callers that don't inject io.input"
metrics:
  duration_seconds: 1080
  completed_date: "2026-06-09"
  tasks_completed: 2
  files_created: 0
  files_modified: 3
  tests_written: 5
  tests_passing: 85
---

# Phase 01 Plan 03: CLI Wizard Wiring Summary

`runInit` in `lib/cli.js` rewired with wizard gate (WIZ-01), masked confirmation summary before any write (WIZ-04), fully-flagged non-interactive path unchanged (WIZ-05), no-TTY guard with actionable error (WIZ-06), and `bin/ocp-mcp.js` updated to await a possibly-async `runCli` result.

## What Was Built

### lib/cli.js (modified)

**BLOCKER 1 fix:** Removed `if (!options.client) throw new Error("Missing required option: --client")` from `parseInitOptions`. Client enforcement is now handled in `finishInit` via the existing `SUPPORTED_CLIENTS.has` guard.

**New import:** `buildConfirmationSummary`, `buildNoTtyError`, `missingPromptFields`, `runWizard` from `./wizard.js`.

**`finishInit(effectiveOptions, io)`** — synchronous helper extracted from the original `runInit` body. Handles `SUPPORTED_CLIENTS` guard, `buildClientConfig`, and the print/write logic. Called by both the sync and async paths.

**`runInit` restructured with three branches (in priority order):**
1. **No-TTY guard (WIZ-06):** If `missingPromptFields(options).length > 0` AND `io.input !== undefined` AND `!io.input.isTTY` → write `buildNoTtyError(missing)` to stderr, return 1. Does not hang.
2. **Interactive wizard (WIZ-01, WIZ-04):** If `missingPromptFields(options).length > 0` AND `io.input.isTTY` → async IIFE: `await runWizard(options, wizardIo)`, write `buildConfirmationSummary(merged)` to stdout BEFORE calling `finishInit`, return `Promise<integer>`.
3. **Synchronous (WIZ-05):** Fully-flagged or legacy no-input path → call `finishInit(options, io)` synchronously, return integer. Golden SHA preserved.

**IO shape bridge:** `wizardIo = { input: io.input, output: io.stdout }` maps `runCli`'s `{input, stdout, stderr}` to wizard's `{input, output}`.

### bin/ocp-mcp.js (modified)

Changed to `process.exitCode = await Promise.resolve(runCli(process.argv.slice(2)))` using ESM top-level await. Handles both synchronous integer and async Promise returns transparently.

### test/cli.test.js (extended)

Added imports: `existsSync` (already in fs imports), `Readable` from `node:stream`.

**`createScriptedIo(answers)`** helper: builds `io` with lazy async generator `Readable` (isTTY=true) plus stdout/stderr capture. Returns `{ io, output }`.

**5 new integration tests:**
1. `no-TTY bare init returns 1 and stderr names --client (WIZ-06)` — injected `io.input: { isTTY: false }`, asserts result=1 and stderr matches `/--client/`, does NOT contain old throw message
2. `interactive bare init reaches masked confirmation summary (WIZ-01, WIZ-04)` — 3 scripted answers (client, baseUrl, accessToken), asserts result=0, stdout contains "Configuration summary", token absent from summary preamble, masked tail present
3. `fully-flagged --print returns config JSON only, no prompts (WIZ-05)` — all 4 flags provided, asserts stdout parses as JSON, no prompt labels ("Enter number or value:", "Select", "MCP client")
4. `wizard + --write: confirmation summary emitted before file write (WIZ-04 ordering)` — scripted TTY io + write path, asserts summary on stdout, file exists, file parses as JSON, raw token absent from stdout
5. `wizard skips pre-supplied flag fields, prompts only for missing ones (WIZ-05 partial)` — `--client` and `--base-url` pre-supplied, only `accessToken` missing, asserts askChoice "Enter number or value:" absent, askText "Base URL:" absent from preamble, token absent from summary

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED (both tasks) | 2ebe466 | test(01-03): add failing tests for wizard CLI integration |
| GREEN (Task 1) | 0218d5d | feat(01-03): rewire runInit with wizard gate, confirmation, and no-TTY guard |
| GREEN (Task 2) | 7af5856 | feat(01-03): add integration tests for wizard CLI wiring |

RED gate satisfied: 3 of 4 new tests failed before implementation (fully-flagged test already passed since no behavior change was needed). GREEN gate satisfied for both tasks.

## Verification Results

All acceptance criteria passed:

- `node --test` — 85/87 tests pass; 2 pre-existing failures unchanged (Cursor `@omilia/mcp-server` assertion and PAT golden SHA — both Phase 4 scope)
- `grep -c 'Missing required option: --client' lib/cli.js` → 0
- `grep -c 'await' bin/ocp-mcp.js` → 1
- `grep -c 'from "./wizard.js"' lib/cli.js` → 1
- no-TTY bare init: returns 1, stderr contains "--client", no "Missing required option" message
- Interactive flow: confirmation summary present, token masked in summary, resolved exit code 0
- Fully-flagged --print: JSON-parseable stdout, no prompt labels
- Wizard + --write: summary on stdout, file created, token absent from stdout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Backward compatibility for legacy io callers without io.input**
- **Found during:** Task 1 GREEN — existing tests (e.g., `runCli(["init", "--client", "cursor"], io)`) used `createIo()` which has no `io.input`. `missingPromptFields({client:"cursor",authChoice:"pat"})` returns `["baseUrl","accessToken"]`, triggering the no-TTY guard and returning 1 — breaking 16 previously-passing tests.
- **Issue:** The no-TTY guard `if (missing.length > 0 && !isTty)` was too broad; it fired even for legacy callers who passed `--client` but no `io.input`.
- **Fix:** Added `io.input !== undefined` condition: `if (missing.length > 0 && io.input !== undefined && !isTty)`. Legacy callers (no injected input) fall through to the synchronous finishInit path, preserving placeholder-default behavior.
- **Files modified:** `lib/cli.js`
- **Commit:** 0218d5d

**2. [Rule 1 - Bug] IO shape mismatch — runCli {input,stdout,stderr} vs wizard {input,output}**
- **Found during:** Task 1 GREEN — `TypeError: Cannot read properties of undefined (reading 'write')` in `askChoice` at `io.output.write(prompt)`.
- **Issue:** `runWizard` and the prompt primitives expect `io.output`, but `runCli` uses `io.stdout`. Passing `io` directly to `runWizard` caused `io.output` to be undefined.
- **Fix:** Construct `wizardIo = { input: io.input, output: io.stdout }` before calling `runWizard`.
- **Files modified:** `lib/cli.js`
- **Commit:** 0218d5d

**3. [Rule 1 - Bug] Scripted test answers wrong count (authChoice skipped by wizard)**
- **Found during:** Task 1 GREEN test iteration — interactive test failed; base URL was consuming the second "1" (meant for authChoice).
- **Issue:** `parseInitOptions` defaults `authChoice` to `"pat"`. Since "pat" is pre-set, `missingPromptFields` does NOT include `authChoice`. The wizard skips the auth prompt. Tests with 4 scripted answers (`["1","1","url","token"]`) fed the second "1" to baseUrl.
- **Fix:** Updated scripted answers to 3 (`["1","url","token"]`) and documented the default in test comments.
- **Files modified:** `test/cli.test.js`
- **Commit:** 0218d5d, 7af5856

**4. [Rule 1 - Bug] Token masking assertion too broad for print path**
- **Found during:** Task 1 GREEN — `assert.equal(output.stdout.includes("super-secret-token-1234"), false)` failed because the final config JSON (printed to stdout by finishInit) contains the raw token value in `OCP_ACCESS_TOKEN`.
- **Issue:** WIZ-04 requires the CONFIRMATION SUMMARY to mask secrets; the config output itself legitimately shows the token the user entered.
- **Fix:** Extract the summary preamble (stdout before the first `{`) and assert the raw token absent from that portion only. Token in config JSON is expected behavior.
- **Files modified:** `test/cli.test.js`
- **Commit:** 7af5856

## Known Stubs

None. All wizard integration points are fully wired:
- `runWizard` drives real prompt primitives (from lib/prompts.js)
- `buildConfirmationSummary` applies real masking (from lib/wizard.js)
- `buildNoTtyError` returns a real actionable error string (from lib/wizard.js)
- `finishInit` builds and writes/prints the real config

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-01-07: Info Disclosure via confirmation summary | `buildConfirmationSummary` masks all secret fields; test asserts raw token absent from summary preamble | Mitigated |
| T-01-08: DoS via no-TTY prompt hang | `runInit` checks `io.input?.isTTY`; no-TTY+missing-input path returns 1 immediately via `buildNoTtyError`, never calls `runWizard` | Mitigated |
| T-01-10: Regression of --print/--write contract | `finishInit` extracted from original `runInit` body unchanged; golden SHA preserved; all 24 previously-passing tests still pass | Mitigated |

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes. This plan wires existing lib/wizard.js and lib/prompts.js functions into lib/cli.js.

## Self-Check: PASSED

- `lib/cli.js` modified with wizard import: FOUND
- `bin/ocp-mcp.js` contains await: FOUND
- `test/cli.test.js` contains createScriptedIo: FOUND
- RED commit 2ebe466 exists: FOUND
- GREEN commit 0218d5d exists: FOUND
- GREEN commit 7af5856 exists: FOUND
- `grep -c 'Missing required option: --client' lib/cli.js` = 0: CONFIRMED
- Full test suite: 85/87 pass; 2 pre-existing failures unchanged: CONFIRMED
