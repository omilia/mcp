<!-- refreshed: 2026-06-09 -->
# Architecture

**Analysis Date:** 2026-06-09

## System Overview

```text
┌────────────────────────────────────────────────────────────────────┐
│                     MCP Client (Claude, Cursor, etc.)              │
│                  (invokes tools via MCP protocol)                  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ MCP tool calls
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                  Node.js Bootstrap Layer                           │
│   `bin/ocp-mcp.js`  →  `lib/cli.js`  →  `lib/runtime.js`         │
│   (npx entry point; spawns uv/Python subprocess)                  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ subprocess: uv run fastmcp run server.py:mcp
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                  FastMCP Server Layer (Python)                     │
│   `src/server.py`  (mounts `main.py` MCP instance via lifespan)   │
│   `src/main.py`    (primary tool registry — PUBLIC tools)          │
└──────┬──────────────────┬──────────────────┬────────────┬──────────┘
       │                  │                  │            │
       ▼                  ▼                  ▼            ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌────────────────┐
│  Tool        │  │  Dependency  │  │  Tags    │  │  Payload       │
│  Decorators  │  │  Injection   │  │  System  │  │  Schemas       │
│`tool_decora- │  │`dependencies │  │`tags.py` │  │`payload_       │
│  tors.py`    │  │  .py`        │  │          │  │  schemas.py`   │
└──────┬───────┘  └──────────────┘  └──────────┘  └────────────────┘
       │ async with XxxClient(auth_header=...)
       ▼
┌────────────────────────────────────────────────────────────────────┐
│                  OCP API Client Layer (`src/ocp/`)                 │
│  OrchestratorClient  MiniAppsClient  PathfinderClient  ChatClient  │
│  InsightsClient  IntegrationsClient  EnvironmentsManagerClient     │
│  (all inherit BaseClient — `src/ocp/base.py`)                      │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ httpx async HTTP / WebSocket
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                  OCP REST APIs & WebSocket                         │
│  orchestrator/api/*   miniapps/api/*   pathfinder/api/v1/*         │
│  dialogs-api/*   integrations/api/*   envs-manager/api/v1/*        │
│  Keycloak token endpoint (auth/realms/{realm}/...)                 │
└────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `bin/ocp-mcp.js` | CLI entry point; delegates to `runCli` | `bin/ocp-mcp.js` |
| `lib/cli.js` | Parses `init` / `run` subcommands and options | `lib/cli.js` |
| `lib/config.js` | Builds MCP client config JSON/TOML for Cursor, Claude, VSCode, Codex | `lib/config.js` |
| `lib/runtime.js` | Resolves Python project root, spawns `uv run fastmcp run` | `lib/runtime.js` |
| `src/server.py` | Root FastMCP instance; mounts `main.py` MCP sub-instance | `src/server.py` |
| `src/main.py` | Defines all PUBLIC MCP tools (miniapps, orchestrator, pathfinder, insights, etc.) | `src/main.py` |
| `src/tool_decorators.py` | `ToolWrapper` / `tool_with_callbacks` — before/after/override hooks | `src/tool_decorators.py` |
| `src/dependencies.py` | FastMCP `Depends()` providers: `Authorization`, `execution_mode`, `allowed_groups` | `src/dependencies.py` |
| `src/tags.py` | Tag constants controlling tool visibility and behavior | `src/tags.py` |
| `src/payload_schemas.py` | Pydantic models for structured tool inputs (`AgentInput`, `QueueInfo`, `AvailableAgent`) | `src/payload_schemas.py` |
| `src/utils.py` | Canvas helpers, locale validators, shared error types (`GroupAccessError`, `NameMustBeUniqueError`) | `src/utils.py` |
| `src/ocp/base.py` | `BaseClient` — async HTTP client with three-tier auth resolution | `src/ocp/base.py` |
| `src/ocp/authentication.py` | `Authentication` — Keycloak password-grant with in-memory token cache | `src/ocp/authentication.py` |
| `src/ocp/orchestrator.py` | `OrchestratorClient` — apps, agents, canvases, flows, TTS | `src/ocp/orchestrator.py` |
| `src/ocp/miniapps.py` | `MiniAppsClient` — miniapp CRUD, prompt setting | `src/ocp/miniapps.py` |
| `src/ocp/pathfinder.py` | `PathfinderClient` — FAQ/knowledge base projects and vector stores | `src/ocp/pathfinder.py` |
| `src/ocp/chat.py` | `ChatClient` — WebSocket chat against deployed apps (single-turn and multi-turn) | `src/ocp/chat.py` |
| `src/ocp/insights.py` | `InsightsClient` — dialog log search and retrieval (different base URL per env) | `src/ocp/insights.py` |
| `src/ocp/integrations.py` | `IntegrationsClient` — phone number search | `src/ocp/integrations.py` |
| `src/ocp/environments_manager.py` | `EnvironmentsManagerClient` — variable collections | `src/ocp/environments_manager.py` |
| `src/guides/` | Markdown workflow guides served via the `read_guide` tool | `src/guides/` |
| `vendor/python/` | Filtered PUBLIC-only copy of `src/` bundled into the npm package | `vendor/python/` |
| `scripts/sync-python.js` | Syncs filtered Python sources into `vendor/python/` for npm packaging | `scripts/sync-python.js` |

## Pattern Overview

**Overall:** Two-process MCP server — Node.js bootstrap + Python FastMCP subprocess

**Key Characteristics:**
- Node.js (`npx`) is the install/run surface; it spawns the Python MCP server via `uv run fastmcp run`
- All MCP tools are async Python functions registered with FastMCP using a custom `tool_with_callbacks` decorator
- Tool inputs carry injected dependencies (`Authorization`, `execution_mode`, `allowed_groups`) via FastMCP's `Depends()` mechanism — they are not passed by the caller
- Each tool opens an OCP API client as an async context manager (`async with XxxClient(...) as client`), making one or more HTTP calls, then closes it
- Two FastMCP instances exist: `main.py` defines the PUBLIC surface; `server.py` mounts it and adds server-only tools (e.g., `add_faq_to_agent`)
- Tags on tools control which agent modes can invoke them (`PUBLIC`, `APPROVAL`, `GROUP_FILTER`, `AUTOMATION_LVL_1/4`, etc.)
- `vendor/python/` is a PUBLIC-tag-filtered copy of `src/` produced by `scripts/sync-python.js` and shipped inside the npm tarball

## Layers

**Node.js CLI / Bootstrap Layer:**
- Purpose: Package distribution, config generation, Python subprocess management
- Location: `bin/`, `lib/`
- Contains: CLI argument parsing, MCP client config builders, process spawning
- Depends on: Node.js stdlib only (no npm dependencies)
- Used by: End users via `npx github:omilia/mcp`

**FastMCP Tool Layer:**
- Purpose: Defines MCP tools as async Python functions, enforces access control, executes tool logic
- Location: `src/server.py`, `src/main.py`
- Contains: All `@tool(...)` decorated functions, guide reader, group resolver helper
- Depends on: `src/ocp/`, `src/tool_decorators.py`, `src/dependencies.py`, `src/tags.py`, `src/payload_schemas.py`
- Used by: MCP clients (Claude, Cursor, etc.) via the MCP protocol

**Decorator / Middleware Layer:**
- Purpose: Wraps tool functions with before/after/override lifecycle hooks and mock execution support
- Location: `src/tool_decorators.py`, `src/dependencies.py`
- Contains: `ToolWrapper`, `tool_with_callbacks`, `Depends()` providers
- Depends on: `fastmcp`
- Used by: `src/main.py`, `src/server.py`

**OCP API Client Layer:**
- Purpose: Abstracts all HTTP communication with OCP backend services
- Location: `src/ocp/`
- Contains: One `*Client` class per OCP service, all inheriting `BaseClient`
- Depends on: `httpx`, `websockets`, `src/ocp/authentication.py`
- Used by: Tool functions in `src/main.py` and `src/server.py`

**Authentication Layer:**
- Purpose: Resolves credentials and manages token lifecycle
- Location: `src/ocp/base.py` (resolution logic), `src/ocp/authentication.py` (Keycloak)
- Contains: Three-tier auth resolution (Bearer > PAT > Keycloak password-grant), token refresh, token revocation
- Depends on: `httpx`, environment variables
- Used by: `BaseClient.__init__` and `_get_auth_headers`

## Data Flow

### Primary Tool Execution Path

1. MCP client calls a tool (e.g., `create_agent`) → FastMCP dispatches to `server.py:mcp` (`src/server.py`)
2. FastMCP resolves `Depends()` values — `Authorization`, `execution_mode`, `allowed_groups` — via providers in `src/dependencies.py`
3. `ToolWrapper._create_wrapped_function` runs: checks `execution_mode`; calls `_before` hook if set; calls the tool function (`src/main.py`)
4. Tool function opens `async with OrchestratorClient(auth_header=Authorization)` → `src/ocp/orchestrator.py`
5. `BaseClient.__init__` selects auth branch; `_get_auth_headers()` returns headers (may call `Authentication.get_token()` for Keycloak)
6. `httpx.AsyncClient` sends HTTP request to `OCP_BASE_URL/orchestrator/api/agents/`
7. Response returned up through `OrchestratorClient` → tool function → FastMCP → MCP client
8. `_after` hook fires if registered

### WebSocket Chat Flow (`talk_to_app`)

1. `ChatClient._get_chat_credentials` fetches `chat_url` and `live_token` via REST (`orchestrator/api/apps/{id}/web_chat/`)
2. WebSocket opened to `chat_url` using `websockets` library
3. `start_session_req` sent; server responds with `start_session_resp` + session ID
4. `start_dialog_req` (new session) or `session_resume_req` (existing session) sent with user message
5. Client collects `dialog_message_event` frames until `state_event` with `DIALOG_END` or timeout
6. Session ID returned to tool caller for multi-turn use

### Auth Resolution (per `BaseClient.__init__`)

1. `auth_header` constructor argument → `Authorization: Bearer <token>` (passthrough from MCP client session)
2. `OCP_ACCESS_TOKEN` env var → `X-OCP-PERSONAL-ACCESS-TOKEN: <pat>`
3. `OCP_USERNAME` + `OCP_PASSWORD` env vars → Keycloak password grant via `Authentication.get_token()` with in-memory cache and refresh

**State Management:**
- No shared mutable state across tool invocations; each tool creates a new client instance
- Authentication token cache lives in `Authentication` instances, which are per-`BaseClient` (not module-level singletons)
- Session IDs for multi-turn chat are passed by the MCP caller between tool invocations

## Key Abstractions

**`BaseClient` (async context manager):**
- Purpose: Shared authenticated HTTP client for all OCP services
- Examples: `src/ocp/orchestrator.py`, `src/ocp/miniapps.py`, `src/ocp/pathfinder.py`
- Pattern: `async with XxxClient(auth_header=Authorization) as client:` opens `httpx.AsyncClient`, closes on exit

**`ToolWrapper` (decorator pattern):**
- Purpose: Attaches before/after/override callbacks to a tool function without changing its signature
- Examples: `src/tool_decorators.py`
- Pattern: `@tool(tags=[...])` wraps function; `@my_tool.before`, `@my_tool.after`, `@my_tool.override` register hooks

**`Depends()` injection:**
- Purpose: Supplies `Authorization`, `execution_mode`, `allowed_groups` to every tool without the caller passing them
- Examples: `src/dependencies.py`, used as type annotations in `src/main.py` and `src/server.py`
- Pattern: `Authorization: AuthorizationDep = None` in function signature

**Tag system:**
- Purpose: Controls which tools are available to which agent modes and whether they require approval
- Examples: `src/tags.py`, applied via `@tool(tags=[PUBLIC, APPROVAL, GROUP_FILTER, ...])`
- Pattern: Tags are strings; `PUBLIC` marks tools included in the GitHub mirror and npm package

## Entry Points

**`bin/ocp-mcp.js` (npm CLI entry):**
- Location: `bin/ocp-mcp.js`
- Triggers: `npx github:omilia/mcp <command>`
- Responsibilities: Delegates to `runCli(process.argv.slice(2))`

**`src/server.py` (Python MCP server root):**
- Location: `src/server.py`
- Triggers: Spawned by `lib/runtime.js` via `uv run fastmcp run src/server.py:mcp`
- Responsibilities: Creates root `FastMCP('OCP')` instance, mounts `main.py` sub-instance in lifespan, registers server-specific tools

**`src/main.py` (PUBLIC tool registry):**
- Location: `src/main.py`
- Triggers: Mounted by `server.py` via `app.mount(public_orc_mcp)` in lifespan; also runnable standalone (`python main.py`)
- Responsibilities: Registers all PUBLIC-tagged MCP tools across miniapps, orchestrator, insights, pathfinder, integrations, envs-manager domains

## Architectural Constraints

- **Threading:** Single-threaded async event loop (Python asyncio). No worker threads. All I/O is non-blocking via `httpx.AsyncClient` and `websockets`.
- **Global state:** `mcp` FastMCP instances in `src/main.py` (line 31) and `src/server.py` (line 19) are module-level. `_GUIDES_DIR` and `_AVAILABLE_GUIDES` in `src/main.py` (lines 18–19) are module-level constants. No shared mutable state.
- **Circular imports:** `src/ocp/base.py` lazy-imports `Authentication` from `src/ocp/authentication.py` inside `__init__` to avoid a circular import (authentication.py imports error classes from base.py).
- **Two-server mount pattern:** `server.py` creates its own `FastMCP` and mounts `main.py`'s `FastMCP` instance during lifespan. Tools defined in `server.py` are NOT in `main.py` and are not in the PUBLIC filter.
- **Vendor sync:** `vendor/python/src/` must always be regenerated by `scripts/sync-python.js` before publishing to npm. Editing `vendor/` directly will be overwritten.

## Anti-Patterns

### Direct `vendor/python/src/` edits

**What happens:** Modifying files under `vendor/python/src/` directly.
**Why it's wrong:** `scripts/sync-python.js` overwrites `vendor/python/` entirely on each run; any direct edits are lost.
**Do this instead:** Edit `src/` at the repo root; run `node scripts/sync-python.js` to propagate changes.

### Module-level `BaseClient` or `Authentication` singletons

**What happens:** Creating a shared `BaseClient` or `Authentication` at module level and reusing it across tool calls.
**Why it's wrong:** Token state would be shared across concurrent requests; the design explicitly creates per-call instances.
**Do this instead:** Always use `async with XxxClient(auth_header=Authorization) as client:` inside the tool function body (as done in `src/main.py`).

### Adding tools to `main.py` without the `PUBLIC` tag

**What happens:** A tool is added to `main.py` but not tagged with `PUBLIC`.
**Why it's wrong:** `main.py` is the module mounted as the public surface and filtered into `vendor/python/`; non-PUBLIC tools belong in `server.py`.
**Do this instead:** Add internal-only tools to `src/server.py`; add PUBLIC tools to `src/main.py` with the `PUBLIC` tag.

## Error Handling

**Strategy:** Raise `fastmcp.exceptions.ToolError` for user-facing errors; let unexpected exceptions propagate to FastMCP's default handler.

**Patterns:**
- `GroupAccessError(group)` — raised in tool functions when `allowed_groups` check fails (`src/utils.py`)
- `NameMustBeUniqueError(name)` — raised by miniapp creation on name conflicts (`src/utils.py`)
- `ChatError` — raised by `ChatClient` when WebSocket session fails (`src/ocp/chat.py`)
- `AuthenticationError` and subclasses (`KeycloakCredentialsError`, `KeycloakConfigError`, `KeycloakUnavailableError`) — raised by `BaseClient._get_auth_headers` and `Authentication.get_token` (`src/ocp/base.py`, `src/ocp/authentication.py`)
- HTTP 4xx/5xx from `httpx` are suppressed for POST/PUT (returned as error dicts) but raised via `raise_for_status()` for GET/DELETE

## Cross-Cutting Concerns

**Logging:** `fastmcp.utilities.logging.get_logger(__name__)` used in all modules. No stdout writes. Credentials and response bodies never logged.
**Validation:** Tool parameter validation via Python type annotations and Pydantic models in `src/payload_schemas.py`. Locale availability validated via `validate_available_locales` in `src/utils.py`.
**Authentication:** Handled exclusively in `src/ocp/base.py` and `src/ocp/authentication.py`; tool functions receive `Authorization` header via dependency injection and pass it to client constructors.

---

*Architecture analysis: 2026-06-09*
