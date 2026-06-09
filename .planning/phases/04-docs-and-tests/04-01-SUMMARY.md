---
phase: 04-docs-and-tests
plan: "01"
subsystem: docs
tags: [docs, reconciliation, claude-mcp-add, wizard, DOC-01, DOC-02, DOC-03]
dependency_graph:
  requires: []
  provides: [docs-reconciled, claude-mcp-add-documented, wizard-documented]
  affects: [README.md, docs/installation.md]
tech_stack:
  added: []
  patterns: [Markdown documentation, HTML comments]
key_files:
  created: []
  modified:
    - README.md
    - docs/installation.md
decisions:
  - "HTML comment chosen for Confluence sync reminder — no rendered content, zero risk of confusing users"
  - "Wizard section numbered 0 ('## 0. Interactive wizard') to precede '## 1. npx CLI installer' as top-of-file recommended path"
  - "Confluence comment reworded to avoid literal @omilia/mcp-server and settings.json strings (both banned by DOC-01/verification greps)"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-09T13:18:47Z"
  tasks_completed: 3
  files_modified: 2
---

# Phase 04 Plan 01: Docs Reconciliation Summary

Reconciled README.md and docs/installation.md with the behavior shipped in
Phases 1-3: GitHub distribution spec, `claude mcp add` Claude Code install path,
and the interactive wizard with prereq and smoke-test verification.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add claude mcp add path and assert GitHub spec (DOC-01, DOC-02) | a3a7f73 | docs/installation.md |
| 2 | Add interactive wizard section (DOC-03) | fce0138 | docs/installation.md, README.md |
| 3 | Flag Confluence developer guide for manual sync | becb6cc + 84ccaeb | docs/installation.md |

## What Was Built

`claude mcp add OCP --scope user --env ... -- npx -y github:omilia/mcp run`
documented as the Claude Code install path, with interactive wizard section
covering masked confirmation, node 20+ / uv prereq checks, and PASS/FAIL summary.

### DOC-01: GitHub spec maintained

`grep -rc '@omilia/mcp-server' README.md docs/` returns 0 in all files. No npm name introduced.

### DOC-02: Claude Code `claude mcp add` subsection

Added `### Claude Code (\`claude mcp add\`)` under `## 1. npx CLI installer` in
`docs/installation.md`. Documented:

- The installer invokes `claude mcp add OCP --scope user --env ... -- npx -y github:omilia/mcp run`
- Exact `--env` pairs for PAT (`OCP_BASE_URL`, `OCP_ACCESS_TOKEN`) and Keycloak
  (`OCP_BASE_URL`, `OCP_USERNAME`, `OCP_PASSWORD`, `OCP_KEYCLOAK_REALM`) — matching
  `getEnvBlock()` in `lib/config.js` and `DEFAULT_SERVER_NAME = "OCP"`
- Installer writes no JSON file for Claude Code
- Absent-CLI fallback: prints masked snippet + guidance, exits 0 (CLI-03)
- Token examples use placeholders only; wizard masks token in confirmation summary;
  config files use mode 0600

The "Manual MCP configuration" table's Claude Code row (`~/.claude.json`) is untouched —
it documents the correct manual-paste destination, not the installer behavior.

No non-VS Code `settings.json` reference appears in the doc.

### DOC-03: Interactive wizard section

Added `## 0. Interactive wizard (recommended)` before `## 1. npx CLI installer`:

- 5-step prompt sequence matching `PROMPT_FIELDS` order in `lib/wizard.js`:
  client → auth method → base URL → credentials → masked confirmation summary
- States token is never echoed while typing; secrets masked in summary (last 4 chars visible)
- Documents prereq checks (node 20+, uv) from `lib/preflight.js`
- Documents install step (claude mcp add for Claude Code; 0600 config write for Claude Desktop)
- Documents smoke test and `Result: PASS / FAIL` from `lib/verify.js`
- Mentions `--no-verify-install` to skip smoke test
- Non-interactive CI mode: supply all flags

Install-method comparison table updated with wizard as first/recommended row.

README.md `## Install` section now leads with bare `npx github:omilia/mcp init` as
recommended first command; flag-driven one-liner retained as CI alternative.

### Confluence sync reminder

HTML comment at top of `docs/installation.md` records that the internal Confluence
"OCP MCP Server — Developer Guide" needs manual sync (old npm name, flag-only init,
incorrect Claude Code config path). No Confluence URL or credentials included.
Comment reworded to avoid literal banned strings (@omilia/mcp-server, settings.json).

## Verification Results

All plan verification checks passed:

```
DOC-01: no @omilia/mcp-server in README.md or docs/   PASS
DOC-02: claude mcp add in docs/installation.md         PASS
DOC-02: ~/.claude.json manual-paste row intact         PASS
DOC-02: no spurious settings.json (non-VS Code)        PASS
DOC-02: github:omilia/mcp in README                    PASS
DOC-03: '## 0. Interactive wizard' heading             PASS
DOC-03: confirmation summary mentioned                 PASS
DOC-03: node 20+ mentioned                             PASS
DOC-03: PASS/FAIL summary mentioned                    PASS
DOC-03: npx github:omilia/mcp init in README           PASS
Confluence HTML comment present                        PASS
node --test (155 tests)                                PASS (0 fail)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] HTML comment contained banned strings**
- **Found during:** Task 3 verification
- **Issue:** Initial Confluence comment used the literal `@omilia/mcp-server` and
  `~/.claude/settings.json` strings. Both are caught by DOC-01 and the
  settings.json grep checks respectively.
- **Fix:** Rephrased comment to describe the same issues without the literal banned
  strings ("old npm package name" / "incorrect Claude Code config-file path").
- **Files modified:** docs/installation.md
- **Commit:** 84ccaeb

## Known Stubs

None — all documented commands and env pairs match the actual implementation in
`lib/install.js`, `lib/config.js`, `lib/wizard.js`, `lib/verify.js`, and
`lib/preflight.js`.

## Threat Flags

None — Markdown-only edits. No new network endpoints, auth paths, file access
patterns, or schema changes introduced.

## Self-Check: PASSED

- docs/installation.md: modified (verified via grep checks)
- README.md: modified (verified via grep checks)
- Commits a3a7f73, fce0138, becb6cc, 84ccaeb: confirmed in git log
- 155/155 node --test tests pass
