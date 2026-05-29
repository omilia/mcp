# Status — omilia/mcp public mirror

This repository is the **public mirror** of the internal Omilia MCP
server source, auto-generated from the source-of-truth GitLab repo on
every push to master. Humans only commit to the internal repo; this
mirror is fully derived.

## Install paths

Today (recommended):

```bash
# Run directly from this GitHub repo — no npm-registry publish required.
npx github:omilia/mcp init --client claude --print
```

By default `npx github:omilia/mcp` resolves to the repository's default
branch (`main`). If you need a specific snapshot or preview branch,
pass it explicitly: `npx github:omilia/mcp#<branch> init ...`.

Future (not yet enabled):

```bash
# Will work once @omilia/mcp-server is published to https://www.npmjs.com/.
# The package shape is finalised; only the publish step is gated.
npx @omilia/mcp-server init --client claude --print
```

## What this mirror contains

- `src/` — the Python MCP server (filtered to PUBLIC-tagged tools only)
- `bin/`, `lib/` — the Node CLI wrapper that drives the Python server
- `vendor/python/` — vendored Python runtime sources for the Node CLI
- `docs/` — installation guide + example walkthroughs
- `ocp-mcp-server.mcpb` — Anthropic Claude Desktop install bundle
- `pyproject.toml` — filtered to only the dependencies reachable from
  PUBLIC-tagged tools

## Authentication

Two paths, autodiscovered at runtime — see [`docs/installation.md`](docs/installation.md)
for the per-environment realm table.

| Set in env | Path |
|---|---|
| `OCP_ACCESS_TOKEN` | Personal Access Token (recommended) |
| `OCP_USERNAME` + `OCP_PASSWORD` (no PAT) | Keycloak password grant |

Token-related secrets never persist to disk — both flows hold tokens
in-process memory only.
