# Codebase Structure

**Analysis Date:** 2026-06-09

## Directory Layout

```
mcp/                              # Repo root
├── bin/                          # npm CLI entry point
│   └── ocp-mcp.js                # Executable: delegates to lib/cli.js
├── lib/                          # Node.js bootstrap logic
│   ├── cli.js                    # init / run command parsing
│   ├── config.js                 # MCP client config builders (Cursor, Claude, VSCode, Codex)
│   └── runtime.js                # Python subprocess spawner (uv run fastmcp run)
├── scripts/                      # Build/maintenance scripts
│   └── sync-python.js            # Copies filtered PUBLIC src/ into vendor/python/
├── src/                          # Python MCP server — primary source of truth
│   ├── server.py                 # Root FastMCP instance; mounts main.py; server-only tools
│   ├── main.py                   # All PUBLIC MCP tools (30+ tools across 6 OCP domains)
│   ├── dependencies.py           # FastMCP Depends() providers for Authorization, execution_mode, allowed_groups
│   ├── tags.py                   # Tag constants: PUBLIC, APPROVAL, GROUP_FILTER, AUTOMATION_LVL_*, etc.
│   ├── tool_decorators.py        # ToolWrapper / tool_with_callbacks (before/after/override hooks)
│   ├── payload_schemas.py        # Pydantic models: AgentInput, QueueInfo, AvailableAgent
│   ├── utils.py                  # Canvas helpers, GroupAccessError, NameMustBeUniqueError, locale validation
│   ├── guides/                   # Markdown workflow guides served by read_guide tool
│   │   ├── index.md
│   │   ├── build_concierge_app.md
│   │   ├── add_knowledge.md
│   │   └── test_and_improve.md
│   └── ocp/                      # OCP API client layer
│       ├── base.py               # BaseClient: auth resolution, httpx methods (get/post/put/delete/patch)
│       ├── authentication.py     # Authentication: Keycloak password-grant, in-memory token cache
│       ├── orchestrator.py       # OrchestratorClient: apps, agents, canvases, flows, TTS
│       ├── miniapps.py           # MiniAppsClient: miniapp CRUD, prompt setting
│       ├── pathfinder.py         # PathfinderClient: FAQ/knowledge base projects and vector stores
│       ├── chat.py               # ChatClient: WebSocket chat against deployed apps
│       ├── insights.py           # InsightsClient: dialog log search and retrieval
│       ├── integrations.py       # IntegrationsClient: phone number search
│       └── environments_manager.py  # EnvironmentsManagerClient: variable collections
├── vendor/                       # Vendored dependencies for npm packaging
│   └── python/                   # PUBLIC-filtered copy of src/ (generated — do not edit directly)
│       ├── pyproject.toml
│       ├── uv.lock
│       └── src/                  # Mirror of src/ with non-PUBLIC tools removed
├── test/                         # Tests
│   └── cli.test.js               # Node.js built-in test runner tests for lib/cli.js
├── docs/                         # Documentation
│   ├── installation.md
│   └── examples/
├── .planning/                    # GSD planning artifacts (not shipped)
│   └── codebase/
├── manifest.json                 # MCP package manifest (server entry point, user_config schema)
├── package.json                  # npm package metadata; bin: ./bin/ocp-mcp.js
├── pyproject.toml                # Python project (uv/PEP 517); dependencies: fastmcp, httpx, dotenv
├── ocp-mcp-server.mcpb           # Pre-built binary bundle (generated artifact)
├── .mcpbignore                   # Files excluded from .mcpb bundle
├── .mirror-manifest.json         # Tracks public mirror sync state
└── README.md
```

## Directory Purposes

**`bin/`:**
- Purpose: npm package executable
- Contains: Single entry script `ocp-mcp.js`
- Key files: `bin/ocp-mcp.js` — shebang script, calls `runCli(process.argv.slice(2))`

**`lib/`:**
- Purpose: All Node.js logic — CLI parsing, config generation, Python subprocess management
- Contains: Three modules with no npm dependencies (Node.js stdlib only)
- Key files: `lib/cli.js`, `lib/config.js`, `lib/runtime.js`

**`scripts/`:**
- Purpose: Build/maintenance tooling not shipped in the npm package
- Contains: `sync-python.js` — invoked before `npm publish` to populate `vendor/python/`
- Key files: `scripts/sync-python.js`

**`src/`:**
- Purpose: Python MCP server — the sole source of truth for all tool logic
- Contains: FastMCP server files, OCP API clients, tag constants, decorators, Pydantic models, guide markdown files
- Key files: `src/server.py` (root MCP instance), `src/main.py` (all PUBLIC tools)

**`src/ocp/`:**
- Purpose: One client class per OCP backend service, all inheriting `BaseClient`
- Contains: `BaseClient`, `Authentication`, and one `*Client` per service
- Key files: `src/ocp/base.py` (shared auth + HTTP), `src/ocp/orchestrator.py` (largest client)

**`src/guides/`:**
- Purpose: Markdown files returned by the `read_guide` MCP tool
- Contains: Four `.md` files (index, build_concierge_app, add_knowledge, test_and_improve)
- Generated: No — hand-authored
- Committed: Yes

**`vendor/python/`:**
- Purpose: PUBLIC-tag-filtered copy of `src/` bundled into the npm tarball so `npx` users don't need the repo
- Contains: Same structure as `src/` but with non-PUBLIC tools stripped
- Generated: Yes — by `scripts/sync-python.js`
- Committed: Yes (so npm install works without a build step)
- **Do not edit directly** — changes are overwritten by `sync-python.js`

**`test/`:**
- Purpose: Automated tests
- Contains: `cli.test.js` — Node.js built-in test runner tests for `lib/cli.js` and `lib/config.js`
- Key files: `test/cli.test.js`

**`docs/`:**
- Purpose: User-facing documentation and examples
- Contains: `installation.md`, `examples/` subdirectory

## Key File Locations

**Entry Points:**
- `bin/ocp-mcp.js`: npm CLI entry; `npx github:omilia/mcp <command>`
- `src/server.py`: Python MCP root server; spawned via `uv run fastmcp run src/server.py:mcp`
- `src/main.py`: PUBLIC MCP tool registry; also runnable standalone (`python main.py`)

**Configuration:**
- `pyproject.toml`: Python dependencies (`fastmcp>=3.0.0,<4`, `httpx`, `dotenv`), requires Python >=3.10
- `package.json`: npm metadata; no runtime dependencies; `bin` points to `bin/ocp-mcp.js`
- `manifest.json`: MCP package manifest with `user_config` schema for `OCP_BASE_URL` and `OCP_ACCESS_TOKEN`
- `.mcpbignore`: Files excluded from the `.mcpb` bundle

**Core Logic:**
- `src/main.py`: All PUBLIC tool definitions (~550 lines)
- `src/server.py`: Root MCP instance + server-only tools (~215 lines)
- `src/ocp/base.py`: Shared HTTP client and auth resolution (~310 lines)
- `src/ocp/orchestrator.py`: OCP Orchestrator API client (~325 lines)
- `src/utils.py`: Canvas payload builders and shared error classes (~237 lines)

**Testing:**
- `test/cli.test.js`: CLI tests using Node.js built-in `node:test` runner

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `tool_decorators.py`, `environments_manager.py`)
- JavaScript modules: `camelCase.js` (e.g., `cli.js`, `config.js`, `runtime.js`)
- Guide files: `snake_case.md` (e.g., `build_concierge_app.md`)
- Test files: `<module>.test.js` (e.g., `cli.test.js`)

**Directories:**
- Python source: `src/` at root; service clients grouped in `src/ocp/`
- Node.js source: `lib/` for logic, `bin/` for executables
- All lowercase with hyphens for multi-word directories: `vendor/python/`

**Python Classes:**
- API clients: `<ServiceName>Client` (e.g., `OrchestratorClient`, `MiniAppsClient`, `PathfinderClient`)
- Error types: Descriptive `*Error` suffix (e.g., `GroupAccessError`, `KeycloakCredentialsError`)
- Pydantic models: `PascalCase` nouns (e.g., `AgentInput`, `QueueInfo`, `AvailableAgent`)

**Python Functions (tools):**
- Tool functions: `snake_case` verb phrases (e.g., `create_agent`, `search_miniapps`, `talk_to_app`)
- Private helpers: `_snake_case` with leading underscore (e.g., `_resolve_group`, `_deploy_app`, `_get_auth_headers`)

**Tag Constants:**
- All uppercase with underscores: `PUBLIC`, `APPROVAL`, `GROUP_FILTER`, `AUTOMATION_LVL_1`

## Where to Add New Code

**New MCP Tool (public-facing):**
- Tool function: `src/main.py` — add `@tool(tags=[..., PUBLIC])` decorated async function
- If it uses a new OCP service: create `src/ocp/<service>.py` with a new `*Client(BaseClient)` subclass
- Tests: `test/cli.test.js` (JS only); Python tool tests have no established location yet
- After adding: run `node scripts/sync-python.js` to sync to `vendor/python/`

**New MCP Tool (internal only, not PUBLIC):**
- Tool function: `src/server.py` — add `@tool(tags=[...])` decorated async function (no `PUBLIC` tag)
- These are NOT synced to `vendor/python/` and NOT exposed via `npx`

**New OCP API Client:**
- Implementation: `src/ocp/<service_name>.py`
- Inherit from `BaseClient` in `src/ocp/base.py`
- Import and instantiate in the relevant tool function in `src/main.py` or `src/server.py`

**New Pydantic Input Model:**
- Add to `src/payload_schemas.py`

**New Tag Constant:**
- Add to `src/tags.py` with a docstring explaining its purpose

**New Workflow Guide:**
- Add `<name>.md` to `src/guides/`
- Add the name string to `_AVAILABLE_GUIDES` tuple in `src/main.py` (line 19)

**New CLI Config Target (new MCP client type):**
- Add client name to `SUPPORTED_CLIENTS` in `lib/config.js`
- Add builder function following the pattern of `buildMcpServersConfig` or `buildVsCodeConfig`
- Add `clientConfigPath` branch in `lib/config.js` if a known default path exists
- Add handling in `writeClientConfig` in `lib/cli.js`

**Utilities:**
- Shared Python helpers: `src/utils.py`
- Shared Node.js helpers: `lib/config.js` (config-related) or a new `lib/*.js` module

## Special Directories

**`.planning/`:**
- Purpose: GSD planning artifacts (codebase maps, phase plans)
- Generated: By GSD commands
- Committed: Yes (serves as project memory)

**`vendor/python/`:**
- Purpose: npm-bundled Python sources (PUBLIC-filtered copy of `src/`)
- Generated: Yes — by `node scripts/sync-python.js`
- Committed: Yes (enables `npx` without a separate Python install step)
- **Never edit directly**

**`.git/`:**
- Purpose: Git repository data
- Generated: Yes
- Committed: N/A

---

*Structure analysis: 2026-06-09*
