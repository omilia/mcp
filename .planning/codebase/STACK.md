# Technology Stack

**Analysis Date:** 2026-06-09

## Languages

**Primary:**
- Python 3.10+ — All MCP server logic (`src/`)
- JavaScript (ESM) — CLI wrapper, runtime bootstrap, config generation (`bin/`, `lib/`, `scripts/`)

**Secondary:**
- TOML — Python project manifest (`pyproject.toml`)

## Runtime

**Environment:**
- Python: `>=3.10` (declared in `pyproject.toml`); `3.11+` required for sync-python build script (`scripts/sync-python.js`)
- Node.js: `>=20` (declared in `package.json`)

**Python Package Manager:**
- `uv` — used both to resolve dependencies and to launch the Python server (`uv run ... fastmcp run ...`)
- Lockfile: `vendor/python/uv.lock` (present; pinned to exact versions)

**Node Package Manager:**
- npm
- Lockfile: `package-lock.json` (present)

## Frameworks

**Core (Python):**
- `fastmcp` 3.0.0 — MCP server framework; provides `FastMCP`, `@tool`, `Depends()`, `ToolError`, and logging utilities. All tools are declared via `mcp.tool()` in `src/main.py` and `src/server.py`.

**MCP Protocol (Python):**
- `mcp` 1.26.0 — Underlying Model Context Protocol SDK (transitive, pulled in by fastmcp)

**HTTP Client (Python):**
- `httpx` 0.28.1 — Async HTTP client used by all OCP API clients in `src/ocp/`

**WebSocket Client (Python):**
- `websockets` 16.0 — Used exclusively by `src/ocp/chat.py` for real-time chat sessions with deployed Orchestrator apps

**Data Validation (Python):**
- `pydantic` 2.12.5 — Used for request/response schemas (`src/payload_schemas.py`)
- `pydantic-settings` 2.13.0 — Settings management (transitive)

**ASGI Stack (Python, transitive):**
- `starlette` 0.52.1
- `uvicorn` 0.41.0
- `sse-starlette` 3.2.0
- `anyio` 4.12.1

**Testing:**
- Node built-in test runner (`node --test`) — used in `test/cli.test.js`

**Build/Dev (Node):**
- `scripts/sync-python.js` — Copies PUBLIC-filtered Python source into `vendor/python/` for npm packaging

## Key Dependencies

**Critical:**
- `fastmcp` 3.0.0 — Primary framework; all tool registration, dependency injection, and MCP protocol handling depend on it. Pinned to `>=3.0.0,<4`.
- `httpx` 0.28.1 — All OCP REST API calls go through `src/ocp/base.py` which uses `httpx.AsyncClient`
- `websockets` 16.0 — Required for `talk_to_app` tool (chat with deployed apps via WebSocket). Not declared directly in `pyproject.toml`; resolved via `fastmcp` dependency chain.

**Infrastructure:**
- `dotenv` 0.9.9 — Loads `.env` files for local development; called in `src/ocp/base.py` and `src/ocp/authentication.py` via `load_dotenv()`
- `pydantic` 2.12.5 — Schema validation for `AgentInput`, `QueueInfo`, `AvailableAgent` models in `src/payload_schemas.py`

## Configuration

**Environment:**
- `OCP_BASE_URL` — OCP instance base URL (required). Default fallback: `https://pub.demo.ocp.ai`
- `OCP_ACCESS_TOKEN` — Personal Access Token auth (PAT mode)
- `OCP_USERNAME` / `OCP_PASSWORD` — Keycloak password-grant auth
- `OCP_KEYCLOAK_REALM` — Keycloak realm (optional; default `master`)
- No `.env` file committed; `load_dotenv()` picks up a local `.env` if present

**Build:**
- `pyproject.toml` — Python project manifest and dependency declarations
- `vendor/python/uv.lock` — Pinned Python dependency lockfile (committed; used for reproducible installs)
- `package.json` — npm package metadata; `"type": "module"` (ESM)
- `manifest.json` — MCP server manifest for client auto-configuration (Smithery-compatible)

## Platform Requirements

**Development:**
- Python 3.10+ and `uv` installed
- Node.js 20+ and npm installed

**Production:**
- Distributed via npm as `@omilia/mcp-server`
- Node.js entry point (`bin/ocp-mcp.js`) bootstraps `uv run fastmcp run src/server.py:mcp`
- Python source vendored into `vendor/python/` for offline installs (no separate Python install step needed beyond `uv`)
- Supports MCP clients: Cursor, Claude Desktop, Claude Code, VS Code, Codex

---

*Stack analysis: 2026-06-09*
