---
phase: 01-interactive-wizard
plan: "01"
subsystem: wizard
tags: [wizard, pure-functions, tdd, security, masking]
dependency_graph:
  requires: []
  provides: [wizard-decision-layer]
  affects: [lib/wizard.js, test/wizard.test.js]
tech_stack:
  added: []
  patterns: [pure-functions, tdd-red-green, flag-over-answer-precedence, secret-masking]
key_files:
  created:
    - lib/wizard.js
    - test/wizard.test.js
  modified: []
decisions:
  - "PROMPT_FIELDS ordered array drives field ordering in missingPromptFields and buildConfirmationSummary"
  - "isMissing treats both undefined and empty string as absent (consistent with empty flag value)"
  - "realm excluded from requiredFieldsFor since its default ('master') satisfies the requirement without prompting"
  - "maskSecret uses slice of last 4 chars from original string — full secret never concatenated into return value (T-01-02)"
  - "buildNoTtyError returns string; never throws — caller controls stderr write and exit code"
metrics:
  duration_seconds: 165
  completed_date: "2026-06-09"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_written: 38
  tests_passing: 38
---

# Phase 01 Plan 01: Wizard Pure Decision Layer Summary

Pure wizard decision/transform layer with secret masking, flag-over-answer precedence, and no-TTY error generation — all implemented as zero-I/O synchronous functions tested via TDD.

## What Was Built

`lib/wizard.js` exports eight named symbols covering the full wizard decision contract:

**Field model:**
- `PROMPT_FIELDS` — ordered array of field descriptors (name, label, secret, optional default). Drives field ordering across all wizard logic.

**Decision functions (Task 1):**
- `needsPrompting(options, {isTty})` — returns false when fully-flagged or no TTY (WIZ-05)
- `requiredFieldsFor(options)` — returns ordered required field names for the resolved auth choice
- `missingPromptFields(options)` — returns fields absent from options, in PROMPT_FIELDS order; flag-supplied fields excluded (WIZ-05)

**Transform functions (Task 2):**
- `mergeFlagsAndAnswers(options, answers)` — shallow merge where flag values win over answers; never mutates input (WIZ-05)
- `maskSecret(value)` — reveals at most last 4 chars; short secrets fully masked; "(not set)" for empty/undefined (WIZ-04, T-01-02)
- `buildConfirmationSummary(options)` — multi-line summary with all secret fields routed through maskSecret; raw credentials never present (WIZ-04, T-01-01)
- `buildNoTtyError(missingFields)` — actionable error string with field-to-flag map and example invocation (WIZ-06)

## TDD Gate Compliance

| Gate | Commit | Message |
|------|--------|---------|
| RED  | 77b5bad | test(01-01): add failing tests for wizard pure functions |
| GREEN | 3d29404 | feat(01-01): implement pure wizard decision layer (lib/wizard.js) |

Both gates satisfied. No REFACTOR commit needed — implementation was clean on first pass.

## Verification Results

All acceptance criteria passed:

- `node --test test/wizard.test.js` — 38/38 tests pass
- No-I/O assertion: `grep -v '^\s*//' lib/wizard.js | grep -c 'readline\|process.stdout\|console'` → 0
- `needsPrompting({client:"claude-code",authChoice:"pat",baseUrl:"x",accessToken:"y"},{isTty:true})` → false
- `missingPromptFields({authChoice:"pat",baseUrl:"x"})` → `["client","accessToken"]`
- `maskSecret("pat-secret-12345")` does not include "pat-secret" and ends with "2345"
- `buildConfirmationSummary({...accessToken:"supersecrettoken"})` does not contain "supersecrettoken"
- `buildNoTtyError(["client","accessToken"])` contains "--client" and "--access-token"
- Export count: 4 functions (`maskSecret`, `buildConfirmationSummary`, `buildNoTtyError`, `mergeFlagsAndAnswers`) + 3 more = 8 total exports

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|------------|--------|
| T-01-01: Info Disclosure via buildConfirmationSummary | Every secret field rendered via maskSecret; unit test asserts raw secret substring absent from output | Mitigated |
| T-01-02: Info Disclosure via maskSecret | Reveal at most last 4 chars; tail sliced from original string; full secret never concatenated into return | Mitigated |
| T-01-03: Tampering via mergeFlagsAndAnswers | Pure function on shallow copy; flag-over-answer precedence; input immutable | Accepted (per threat register) |

## Deviations from Plan

### Pre-existing Out-of-Scope Failures

Two pre-existing test failures in `test/cli.test.js` exist before this plan's changes (verified by stash test):

1. `builds Cursor config with inline literal placeholders by default` — test expects `@omilia/mcp-server` but code emits `github:omilia/mcp`. Known package name mismatch documented in PROJECT.md.
2. `PAT init for claude produces byte-identical output to golden SHA` — SHA constant is stale relative to current output, consequence of the same package name discrepancy.

These are pre-existing and outside this plan's scope (CONVENTIONS.md scope boundary rule: only auto-fix issues directly caused by current task's changes). Deferred to the plan that fixes the `clientConfigPath('claude-code')` / package name defects.

## Deferred Items

None from this plan. Pre-existing `cli.test.js` failures logged in `.planning/STATE.md` as pre-existing concerns.

## Known Stubs

None. `lib/wizard.js` is fully wired to real logic; no hardcoded empty values or placeholder returns.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan is pure synchronous functions with no I/O.

## Self-Check: PASSED

- `lib/wizard.js` exists: FOUND
- `test/wizard.test.js` exists: FOUND
- RED commit 77b5bad exists: FOUND
- GREEN commit 3d29404 exists: FOUND
- All 38 tests pass: CONFIRMED
