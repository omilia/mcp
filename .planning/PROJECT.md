# OCP MCP Server — Install Flow Overhaul

## What This Is

The OCP MCP Server exposes the Omilia Cloud Platform (Orchestrator, miniApps, Pathfinder, Insights, Integrations, Environments) to any Model Context Protocol client — Claude Desktop, Claude Code, Cursor, VS Code, Codex — as a stateless tool catalogue. It ships as a two-process server: a Node.js bootstrap (`npx github:omilia/mcp`) that spawns a Python FastMCP subprocess via `uv run`.

This milestone is **not** about new OCP tools. It fixes the part users hit first and that currently "works weirdly": the `npx ... init` install flow. The goal is a guided, interactive setup that installs correctly and verifiably — with **Claude Code as the priority client**.

## Core Value

A developer can run `npx github:omilia/mcp init` with no flags, answer a few prompts, and end up with a working OCP MCP server in their client — Claude Code above all — confirmed working before the command exits.

## Requirements

### Validated

<!-- Inferred from existing, working code. Locked unless explicitly revisited. -->

- ✓ Node.js bootstrap spawns the Python FastMCP server via `uv run fastmcp run` — existing (`lib/runtime.js`)
- ✓ `run` command launches the server; `--dry-run` prints the resolved command — existing (`lib/cli.js`, `lib/runtime.js`)
- ✓ `init --client <name> --print` emits a config snippet for cursor/claude/claude-code/vscode/codex — existing (`lib/cli.js`, `lib/config.js`)
- ✓ `init --client <name> --write` writes JSON config with conflict detection and `--force` override (cursor/claude/claude-code/vscode) — existing (`lib/cli.js`)
- ✓ Two auth modes supported — PAT (`OCP_ACCESS_TOKEN`) and Keycloak password grant (`OCP_USERNAME`/`OCP_PASSWORD`/`OCP_KEYCLOAK_REALM`), PAT taking priority — existing (`src/ocp/base.py`, `lib/config.js`)
- ✓ `.mcpb` bundle exists for Claude Desktop drag-and-drop install — existing (`ocp-mcp-server.mcpb`, `manifest.json`)
- ✓ GitHub-based distribution (`github:omilia/mcp`) — existing (`lib/config.js`)

### Active

<!-- This milestone's scope. Hypotheses until shipped and validated. -->

- [ ] Bare `npx github:omilia/mcp init` launches an interactive guided wizard (client → auth method → base URL → credentials → confirm → write)
- [ ] Existing flags (`--client`, `--auth`, `--base-url`, `--access-token`, etc.) continue to work as non-interactive overrides for CI / scripted use
- [ ] Claude Code install uses the official `claude mcp add` CLI (correct location and scope), replacing the wrong `~/.claude/settings.json` write path
- [ ] Claude Desktop install path verified end-to-end (config write and/or `.mcpb` bundle)
- [ ] Install verification: check `node` (20+) and `uv` are on PATH with actionable hints if missing, then smoke-test that the server starts and tools are reachable
- [ ] Developer guide doc reconciled to the actual behavior: GitHub URL (not `@omilia/mcp-server`), correct Claude Code path, the new interactive flow
- [ ] `test/cli.test.js` extended to cover the wizard, `claude mcp add` invocation, and config writing

### Out of Scope

- Publishing to npm as `@omilia/mcp-server` — user decided to stay on GitHub distribution (`github:omilia/mcp`); avoids a publish pipeline
- Interactive/wizard support for Cursor, VS Code, Codex this milestone — deferred; focus is Claude Code + Claude Desktop (their flag-driven `--print`/`--write` paths remain as-is)
- New OCP tools or changes to the Python tool catalogue — this milestone is install-flow only
- Fixing the unrelated Python bugs found during mapping (timezone offset, unawaited `search_variable_collections`, `components` default) — tracked in `.planning/codebase/CONCERNS.md` for a later milestone

## Context

- **Brownfield.** Full codebase map in `.planning/codebase/`. Architecture: Node.js CLI/bootstrap layer (`bin/`, `lib/`) + Python FastMCP server (`src/`), with `vendor/python/` a PUBLIC-filtered copy synced by `scripts/sync-python.js`.
- **The trigger:** the developer guide (Georgios Zakis) documents three install methods (manual config, CLI installer `--write`, `.mcpb` bundle) but the CLI is purely flag-driven and the Claude Code path is broken.
- **Known concrete defects in the current install flow:**
  - `clientConfigPath('claude-code')` returns `~/.claude/settings.json` (`lib/config.js:73-75`) — Claude Code reads MCP servers from `~/.claude.json` or via `claude mcp add`, not `settings.json`. A `--write` lands in a file Claude Code never reads for MCP servers.
  - Package name mismatch: code emits `github:omilia/mcp` (`lib/config.js:2`) while the guide shows `@omilia/mcp-server`.
  - No interactivity: `init` hard-requires `--client` and errors when run bare (`lib/cli.js:150-152`).
  - Codex `--write` is unimplemented (`lib/cli.js:201-203`) — out of scope this milestone but noted.
- **Distribution constraint:** `npx github:omilia/mcp` triggers a git clone + build on launch (slower than an npm package); accepted tradeoff for staying off npm.

## Constraints

- **Tech stack**: Install/CLI changes are Node.js ESM only (`bin/`, `lib/`), no new npm dependencies preferred — the CLI layer currently depends on Node stdlib alone. Any interactive prompt should use Node built-ins (`node:readline`) unless a strong case is made otherwise.
- **Compatibility**: Existing flag interface must remain backward-compatible for scripted/CI use.
- **Dependencies**: `claude mcp add` requires the Claude Code CLI on PATH — must degrade gracefully (clear guidance) when absent.
- **Security**: Per Omilia data rules, never echo or log credentials; tokens written to config files keep the existing `mode 0o600`. Smoke-test output must not surface secrets.
- **Testing**: Node built-in test runner (`node --test`) — no new test framework.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Bare `init` runs a full guided wizard; flags become overrides | Lowest-friction setup for the priority use case; keeps CI scriptable | — Pending |
| Claude Code install via `claude mcp add` CLI | Official path handles scope + correct location; avoids the `~/.claude/settings.json` bug | — Pending |
| Stay on `github:omilia/mcp`, do not publish to npm | User preference; avoids publish pipeline overhead | — Pending |
| Scope clients to Claude Code + Claude Desktop this milestone | Concentrate on the clients users actually asked about | — Pending |
| Verify install (prereqs + smoke test) before exit | "Installs correctly" is the explicit goal; verification is the proof | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-09 after initialization*
