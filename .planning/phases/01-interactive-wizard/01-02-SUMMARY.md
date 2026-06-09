---
phase: 01-interactive-wizard
plan: "02"
subsystem: wizard-io
tags: [wizard, prompts, readline, tdd, security, non-echo, io-injection]
dependency_graph:
  requires: [wizard-decision-layer]
  provides: [wizard-io-layer, runWizard]
  affects: [lib/prompts.js, lib/wizard.js, test/wizard.test.js]
tech_stack:
  added: [node:readline/promises, node:stream (test helpers)]
  patterns: [tdd-red-green, io-injection, secret-muting, lazy-readable-generator]
key_files:
  created:
    - lib/prompts.js
  modified:
    - lib/wizard.js
    - test/wizard.test.js
decisions:
  - "askSecret mutes io.output.write during readline read — typed characters never echoed, label always shown (T-01-04)"
  - "createScriptedIo uses async generator Readable so readline sees lazy EOF — required for re-prompt loops"
  - "runWizard prompts for realm in keycloak path despite requiredFieldsFor excluding it — realm has defaultValue 'master' via askText, giving user the option to override"
  - "CLIENT_CHOICES and AUTH_CHOICES declared as module-level constants in wizard.js for consistency with PROMPT_FIELDS ordering"
metrics:
  duration_seconds: 420
  completed_date: "2026-06-09"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
  tests_written: 18
  tests_passing: 56
---

# Phase 01 Plan 02: Wizard I/O Layer Summary

Terminal I/O primitives and runWizard orchestrator — non-echoing secret input, io-injected prompt functions, and a full guided flow from client selection through credential collection, all proven green over scripted streams.

## What Was Built

### lib/prompts.js (new)

Three async prompt primitives using `node:readline/promises`, all accepting injected `io = { input, output }`:

- `askChoice(label, choices, io)` — prints enumerated list, accepts 1-based index or value string, re-prompts on invalid input. Used for `client` and `authChoice` fields.
- `askText(label, opts, io)` — trims input, returns `defaultValue` on empty when provided, re-prompts when empty with no default. Used for `baseUrl`, `realm`.
- `askSecret(label, io)` — writes the label to `io.output`, then replaces `io.output.write` with a no-op before calling `rl.question("")`, restoring it after. The label is visible; typed characters and the resolved value are never written to output (T-01-04).

### lib/wizard.js (extended)

Added `export async function runWizard(options, io)`:

- Iterates `PROMPT_FIELDS` in order; per iteration recomputes `requiredFieldsFor({...options, ...answers})` so auth-conditional fields are picked up after `authChoice` resolves.
- Prompts only for missing fields — pre-supplied flag values are never re-prompted (WIZ-05).
- Routes `client` → `askChoice(CLIENT_CHOICES)`, `authChoice` → `askChoice(AUTH_CHOICES)`, secret fields → `askSecret`, rest → `askText`.
- `realm` is offered in the keycloak path with `defaultValue: "master"` so users can override without it being required.
- No `node:fs` or `node:child_process` imports — no file writes or process spawns (T-01-06).
- Returns `mergeFlagsAndAnswers(options, answers)` — flags always win over answers.

Also added `CLIENT_CHOICES` and `AUTH_CHOICES` descriptor arrays as module-level constants.

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED (Task 1) | aaa47b1 | test(01-02): add failing tests for prompts primitives |
| GREEN (Task 1) | ebb2086 | feat(01-02): implement prompts primitives |
| RED (Task 2) | 1e6d2c5 | test(01-02): add failing tests for runWizard orchestrator |
| GREEN (Task 2) | b4021cd | feat(01-02): add runWizard orchestrator to lib/wizard.js |

All four gates satisfied. No REFACTOR commits needed — implementations were clean.

## Verification Results

All acceptance criteria passed:

- `node --test test/wizard.test.js` — 56/56 tests pass (38 original + 18 new)
- `askChoice` with `[2]` input and choices `[claude-code, claude]` resolves to `"claude"`
- `askSecret("Access Token", io)` with input `"topsecret"`: captured output contains `"Access Token"`, does NOT contain `"topsecret"`
- `runWizard({}, io)` bare PAT flow resolves `client="claude-code"`, `authChoice="pat"`, `baseUrl` set, `accessToken` set
- `runWizard({client,authChoice,baseUrl}, io)` prompts exactly once (Access token label once in output)
- `grep -c 'node:readline/promises' lib/prompts.js` → 1
- `grep -c '"@\|require(' lib/prompts.js` → 0
- `grep -c 'node:fs\|node:child_process' lib/wizard.js` → 0
- `grep -c 'export async function runWizard' lib/wizard.js` → 1
- Pre-existing `cli.test.js` failures (2) confirmed pre-existing, unaffected by this plan

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-01-04: Info Disclosure via askSecret terminal echo | `io.output.write` replaced with no-op before readline read; test asserts label present AND secret absent from captured output | Mitigated |
| T-01-05: Info Disclosure via runWizard answer accumulation | Secrets held only in in-memory `answers` object; never written to output or files | Mitigated |
| T-01-06: Elevation of Privilege via runWizard side effects | `lib/wizard.js` imports neither `node:fs` nor `node:child_process`; grep gate verified 0 occurrences | Mitigated |
| T-01-SC: Tampering via npm installs | No package installs; `node:readline/promises` is stdlib; grep gate verifies no `require()` or `@scoped` imports | Mitigated |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed createScriptedIo to use lazy async generator Readable**
- **Found during:** Task 1 GREEN — `askChoice re-prompts` and `askText re-prompts` tests failed with `ERR_USE_AFTER_CLOSE`
- **Issue:** `Readable.from([string])` delivers all data in one chunk; readline detects EOF after first question and closes the interface, making subsequent `rl.question()` calls throw.
- **Fix:** Changed `createScriptedIo` to use `Readable.from(async function*() { yield lines... })` — a lazy async generator that emits one line at a time, so the stream appears live until all lines are consumed.
- **Files modified:** `test/wizard.test.js`
- **Commit:** ebb2086 (same commit as Task 1 GREEN)

**2. [Rule 2 - Missing functionality] Added realm prompting in keycloak path**
- **Found during:** Task 2 GREEN — keycloak test failed: `realm === undefined` instead of `"master"`
- **Issue:** `requiredFieldsFor` excludes realm (has default); `runWizard` loop only iterated `required` fields, so realm was never prompted and never defaulted.
- **Fix:** Added `isRealmForKeycloak` check in the loop — when `authChoice === "keycloak"` and realm is missing, prompt via `askText` with `defaultValue: "master"`. This preserves the plan's intent: realm has a default but users can override it.
- **Files modified:** `lib/wizard.js`
- **Commit:** b4021cd (same commit as Task 2 GREEN)

## Known Stubs

None. All prompt functions are wired to real `node:readline/promises` I/O. `runWizard` returns a complete options object from real prompts. No placeholder returns or hardcoded empty values.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes. This plan is terminal I/O only — no persistence and no process spawning.

## Self-Check: PASSED

- `lib/prompts.js` exists: FOUND
- `lib/wizard.js` exists: FOUND (contains runWizard)
- `test/wizard.test.js` exists: FOUND
- RED commit aaa47b1 exists: FOUND
- GREEN commit ebb2086 exists: FOUND
- RED commit 1e6d2c5 exists: FOUND
- GREEN commit b4021cd exists: FOUND
- All 56 tests pass: CONFIRMED
