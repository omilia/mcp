# Roadmap: OCP MCP Server — Install Flow Overhaul

## Overview

This milestone fixes the install-flow of the OCP MCP Server CLI. Starting from a broken, flag-only `init` command, four phases deliver: a guided interactive wizard, correct client install paths (Claude Code via `claude mcp add`, Claude Desktop end-to-end), prerequisite and smoke-test verification, and docs/tests that lock in the new behavior.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Interactive Wizard** - Replace bare `init` error with a guided prompt flow (client → auth → credentials → confirm)
- [ ] **Phase 2: Client Install Paths** - Fix Claude Code (`claude mcp add`), verify Claude Desktop, standardize config spec
- [ ] **Phase 3: Install Verification** - Prereq checks (node 20+, uv) and post-install smoke test with pass/fail summary
- [ ] **Phase 4: Docs & Tests** - Reconcile developer guide and extend `test/cli.test.js` to cover all new behavior

## Phase Details

### Phase 1: Interactive Wizard
**Goal**: Running `npx github:omilia/mcp init` with no flags launches a guided prompt flow instead of erroring
**Depends on**: Nothing (first phase)
**Requirements**: WIZ-01, WIZ-02, WIZ-03, WIZ-04, WIZ-05, WIZ-06
**Success Criteria** (what must be TRUE):
  1. `npx github:omilia/mcp init` (no flags) launches prompts; it does not error out
  2. User is prompted to select a client (Claude Code, Claude Desktop) and an auth method, then collected credentials — secrets are not echoed
  3. A confirmation summary is shown before any file or process change is made, with secrets masked
  4. Running with all flags (e.g., `--client claude-code --auth pat --base-url ... --access-token ...`) runs non-interactively with no prompts
  5. Running with no TTY and insufficient flags exits with a clear, actionable message rather than crashing
**Plans**: TBD

### Phase 2: Client Install Paths
**Goal**: Claude Code installs via `claude mcp add` to the correct location; Claude Desktop installs end-to-end; all emitted config uses the GitHub distribution spec
**Depends on**: Phase 1
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. After wizard completes for Claude Code, `claude mcp add` is invoked with the correct server name, command (`npx -y github:omilia/mcp run`), and env vars — not a write to `~/.claude/settings.json`
  2. When `claude` is not on PATH, the tool prints an installable config snippet and actionable instructions instead of failing silently
  3. Claude Desktop install path writes config to the correct platform location and/or uses the `.mcpb` bundle — verified end-to-end
  4. Every generated or written config block uses `npx -y github:omilia/mcp run` as the command, consistently across all clients
**Plans**: TBD
**UI hint**: yes

### Phase 3: Install Verification
**Goal**: Before `init` exits, prerequisite tools are checked and the installed server is smoke-tested
**Depends on**: Phase 2
**Requirements**: VER-01, VER-02, VER-03
**Success Criteria** (what must be TRUE):
  1. If `node` (< 20) or `uv` is missing from PATH, the command reports exactly what is missing with a concrete install hint before proceeding
  2. After config is written, a smoke test starts the server and confirms tools are reachable
  3. `init` exits with a clear PASS or FAIL summary; no credentials appear in any output line
**Plans**: TBD

### Phase 4: Docs & Tests
**Goal**: Developer guide reflects actual behavior; `test/cli.test.js` covers wizard, install paths, config writing, and CI-mode invocations
**Depends on**: Phase 3
**Requirements**: DOC-01, DOC-02, DOC-03, TST-01, TST-02, TST-03, TST-04
**Success Criteria** (what must be TRUE):
  1. Developer guide uses `github:omilia/mcp` (not `@omilia/mcp-server`) in every install example
  2. Developer guide documents `claude mcp add` as the Claude Code install path (not `~/.claude/settings.json`)
  3. Developer guide includes a section describing the interactive wizard flow
  4. `test/cli.test.js` has passing tests for: wizard prompt flow, `claude mcp add` invocation (including absent-CLI fallback), config writes to correct locations per client, and fully-flagged non-interactive invocations
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Interactive Wizard | 0/? | Not started | - |
| 2. Client Install Paths | 0/? | Not started | - |
| 3. Install Verification | 0/? | Not started | - |
| 4. Docs & Tests | 0/? | Not started | - |
