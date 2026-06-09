# Requirements: OCP MCP Server — Install Flow Overhaul

**Defined:** 2026-06-09
**Core Value:** A developer can run `npx github:omilia/mcp init` with no flags, answer a few prompts, and end up with a working OCP MCP server in their client — Claude Code above all — confirmed working before the command exits.

## v1 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### Interactive Wizard

- [x] **WIZ-01**: Running `init` with no arguments launches an interactive prompt flow instead of erroring
- [x] **WIZ-02**: Wizard prompts the user to select a client (Claude Code, Claude Desktop)
- [x] **WIZ-03**: Wizard prompts for auth method (PAT or Keycloak) and collects the matching credentials (base URL + token, or base URL + username/password/realm)
- [x] **WIZ-04**: Wizard shows a confirmation summary of what will be written/run before making any change, with secrets masked
- [x] **WIZ-05**: Any value supplied via an existing flag (`--client`, `--auth`, `--base-url`, `--access-token`, etc.) is used as-is and not re-prompted; fully-flagged invocations run non-interactively (CI-safe)
- [x] **WIZ-06**: Wizard exits cleanly with a clear message when run in a non-interactive/no-TTY environment without sufficient flags

### Client Install

- [ ] **CLI-01**: Claude Code install invokes the official `claude mcp add` CLI with the correct server name, command, and env
- [ ] **CLI-02**: The broken `~/.claude/settings.json` write path for claude-code is removed/replaced so config lands where Claude Code actually reads MCP servers
- [ ] **CLI-03**: When the `claude` CLI is not on PATH, the tool degrades gracefully with actionable guidance (printable config + instructions)
- [ ] **CLI-04**: Claude Desktop install path is verified end-to-end (config write to the correct location and/or `.mcpb` bundle install)
- [ ] **CLI-05**: Generated/written config uses the GitHub distribution spec (`npx -y github:omilia/mcp run`), consistently across clients

### Install Verification

- [ ] **VER-01**: Before finishing, init checks that `node` (20+) and `uv` are on PATH and reports missing prerequisites with install hints
- [ ] **VER-02**: After writing config, init runs a smoke test confirming the server starts and tools are reachable
- [ ] **VER-03**: Verification reports a clear pass/fail summary and never prints credentials in its output

### Documentation

- [ ] **DOC-01**: Developer guide reconciled to use the GitHub URL (`github:omilia/mcp`), not `@omilia/mcp-server`
- [ ] **DOC-02**: Developer guide documents the correct Claude Code install path (`claude mcp add` / `~/.claude.json`)
- [ ] **DOC-03**: Developer guide documents the new interactive wizard flow

### Tests

- [ ] **TST-01**: `test/cli.test.js` covers the interactive wizard prompt flow (client/auth/credential collection)
- [ ] **TST-02**: Tests cover the `claude mcp add` invocation for Claude Code (including the CLI-absent fallback)
- [ ] **TST-03**: Tests cover config writing to the correct location for each supported client
- [ ] **TST-04**: Tests cover flag-driven (non-interactive) invocations remaining backward-compatible

## v2 Requirements

Deferred to a future milestone.

### Additional Clients

- **NEXT-01**: Interactive wizard support for Cursor
- **NEXT-02**: Interactive wizard support for VS Code
- **NEXT-03**: Interactive wizard support for Codex (incl. implementing `--write`)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Publish `@omilia/mcp-server` to npm | User chose to stay on GitHub distribution; avoids a publish pipeline |
| Interactive wizard for Cursor / VS Code / Codex | Deferred to v2; this milestone focuses on Claude Code + Claude Desktop |
| New OCP tools / Python tool catalogue changes | This milestone is install-flow only |
| Fixing unrelated Python bugs (timezone offset, unawaited `search_variable_collections`, `components` default) | Tracked in `.planning/codebase/CONCERNS.md` for a later milestone |
| Codex `--write` implementation | Part of the deferred additional-clients work (NEXT-03) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WIZ-01 | Phase 1 | Complete |
| WIZ-02 | Phase 1 | Complete |
| WIZ-03 | Phase 1 | Complete |
| WIZ-04 | Phase 1 | Complete |
| WIZ-05 | Phase 1 | Complete |
| WIZ-06 | Phase 1 | Complete |
| CLI-01 | Phase 2 | Pending |
| CLI-02 | Phase 2 | Pending |
| CLI-03 | Phase 2 | Pending |
| CLI-04 | Phase 2 | Pending |
| CLI-05 | Phase 2 | Pending |
| VER-01 | Phase 3 | Pending |
| VER-02 | Phase 3 | Pending |
| VER-03 | Phase 3 | Pending |
| DOC-01 | Phase 4 | Pending |
| DOC-02 | Phase 4 | Pending |
| DOC-03 | Phase 4 | Pending |
| TST-01 | Phase 4 | Pending |
| TST-02 | Phase 4 | Pending |
| TST-03 | Phase 4 | Pending |
| TST-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-09*
*Last updated: 2026-06-09 after roadmap creation*
