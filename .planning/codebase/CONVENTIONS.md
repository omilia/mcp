# Coding Conventions

**Analysis Date:** 2026-06-09

## Languages and Layers

This is a dual-language codebase:
- **JavaScript (ESM):** CLI entrypoint, config builders, runtime launcher — `bin/`, `lib/`
- **Python (async):** MCP server tools and OCP API clients — `src/`, `vendor/python/src/`

Conventions differ by language layer. Follow the conventions of the layer you are modifying.

---

## JavaScript Conventions (`lib/`, `bin/`)

### Naming Patterns

**Files:**
- `camelCase.js` — all JS source files use camelCase (`cli.js`, `config.js`, `runtime.js`)
- No index barrel files; each module exports named functions directly

**Functions:**
- `camelCase` for all exported and internal functions
- Exported: `runCli`, `buildClientConfig`, `buildCursorConfig`, `clientConfigPath`, `serializeClientConfig`, `runMcpServer`, `buildRunCommand`
- Internal (non-exported): `runInit`, `runRun`, `parseInitOptions`, `writeClientConfig`, `resolveWritePath`, `helpText`

**Variables:**
- `camelCase` for local variables and options objects
- `SCREAMING_SNAKE_CASE` for module-level constants: `DEFAULT_SERVER_NAME`, `PACKAGE_NAME`, `DEFAULT_BASE_URL_PLACEHOLDER`, `PAT_INIT_GOLDEN_SHA256`

**Types/Sets:**
- `Set` literals named in `SCREAMING_SNAKE_CASE`: `JSON_MCP_CLIENTS`, `SUPPORTED_CLIENTS`, `ENTRYPOINTS`

### Module System

**ESM throughout.** The package declares `"type": "module"` in `package.json`. All files use `import`/`export`, no `require()`.

**Import order:**
1. Node built-ins with `node:` prefix (`import { existsSync } from "node:fs"`)
2. Local relative imports (`import { runCli } from "../lib/cli.js"`)

Always use the `node:` prefix for Node built-ins:
```js
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
```

**Explicit `.js` extensions** on all local imports:
```js
import { buildClientConfig } from "./config.js";
```

### Code Style

**Formatting:** No formatter config file detected (no `.prettierrc`, `biome.json`, etc.). The existing code uses:
- 2-space indentation
- Double quotes for strings
- Semicolons present
- Trailing commas in multi-line object/array literals

**No linting config detected** (no `.eslintrc*`). Follow existing patterns when writing new code.

### Function Design

**Size:** Functions are focused and small. `parseInitOptions` in `lib/cli.js` is the longest at ~80 lines due to argument parsing loop — acceptable for a hand-rolled parser.

**Parameters:** Options objects are destructured inline:
```js
export function buildClientConfig(client, options = {}) {
  const { serverName = DEFAULT_SERVER_NAME, baseUrl = ..., useEnvVars = false } = options;
```

**Return values:** All CLI functions return integer exit codes (0 for success, 1 for error, 2 for usage error). Never throw from exported CLI functions — catch and return a code.

**Dependency injection via `io` parameter:** The `io` object (defaulting to `process`) carries `stdout.write` and `stderr.write`. This enables testability without mocking globals:
```js
export function runCli(argv, io = process) { ... }
```

### Error Handling

**JavaScript pattern — errors carry exit codes:**
```js
const err = new Error("Unsupported --auth value: ...");
err.exitCode = 2;
throw err;
```

**Callers check `error.exitCode`:**
```js
} catch (error) {
  io.stderr.write(`${error.message}\n`);
  return error.exitCode ?? 1;
}
```

**All errors go to `io.stderr`**, never `io.stdout`. Stdout is reserved for structured output (JSON, TOML).

**Never throw from public API:** catch inside `runInit`/`runRun`, write to stderr, return exit code.

### Comments

**Inline comments explain non-obvious decisions**, especially security and contract rationale:
```js
// Regression gate: SHA-256 of `init --client claude --print` output
// Updating this value is a deliberate API change — it is the contract...
```

**No JSDoc/TSDoc** — the codebase uses plain inline comments instead.

---

## Python Conventions (`src/`, `vendor/python/src/`)

### Naming Patterns

**Files:**
- `snake_case.py` for all modules (`tool_decorators.py`, `payload_schemas.py`, `dependencies.py`)
- Sub-package for OCP client modules: `ocp/` directory with `base.py`, `authentication.py`, `orchestrator.py`, etc.

**Functions:**
- `snake_case` for all functions: `get_authorization`, `build_run_command`, `validate_available_locales`
- Private helpers prefixed with `_`: `_get_auth_headers`, `_translate_http_error`, `_store_tokens`, `_url`, `_ensure_client`
- `snake_case` for tool functions registered with FastMCP: `search_miniapps`, `create_webservice_miniapp`, `add_faq_to_agent`

**Classes:**
- `PascalCase`: `BaseClient`, `OrchestratorClient`, `Authentication`, `ToolWrapper`, `AgentInput`, `GroupAccessError`

**Constants:**
- `SCREAMING_SNAKE_CASE`: `DEFAULT_SERVER_NAME`, `AUTOMATION_LVL_1`, `PUBLIC`, `TOKEN_REFRESH_SKEW_SECONDS`, `WS_RESPONSE_BODY`
- Module-level constants grouped and commented by category (see `tags.py`)

**Type aliases for injected dependencies** use `PascalCase` suffixed with `Dep`:
```python
AuthorizationDep = Annotated[str | None, Depends(get_authorization)]
ExecutionModeDep = Annotated[str, Depends(get_execution_mode)]
AllowedGroupsDep = Annotated[list[str] | None, Depends(get_allowed_groups)]
```

### Import Organization

**Order:**
1. Standard library: `import os`, `import time`, `from typing import ...`
2. Third-party: `import httpx`, `from fastmcp import FastMCP`, `from pydantic import BaseModel`
3. Local/relative: `from dependencies import AuthorizationDep`, `from .base import BaseClient`

Relative imports used within the `ocp/` package:
```python
from .base import BaseClient, AuthenticationError
```

Absolute imports used for top-level modules from `src/`:
```python
from dependencies import AllowedGroupsDep, AuthorizationDep, ExecutionModeDep
from utils import GroupAccessError, validate_available_locales
```

### Module Docstrings

**Module-level docstrings** explain purpose and structural decisions for non-trivial modules:
```python
"""Keycloak password-grant authentication for the OCP MCP server.

Structural notes:
1. Uses httpx.AsyncClient ...
2. Realm is parameterized via OCP_KEYCLOAK_REALM ...
3. Log-safe: no stdout writes, no response bodies in log lines ...
"""
```

Simple modules (`tags.py`, `dependencies.py`, `payload_schemas.py`) use brief one-line docstrings.

### Async Design

**All MCP tool functions are `async def`.** All OCP client methods are `async def`.

**Clients are async context managers** — always use `async with`:
```python
async with OrchestratorClient(auth_header=Authorization) as client:
    return await client.get_agent(agent_id)
```

Never instantiate a client outside `async with` — the `httpx.AsyncClient` is created in `__aenter__` and closed in `__aexit__`.

### Type Annotations

**Consistent use of Python 3.10+ union syntax** (`str | None`, `list[str] | None`).

**`Annotated` for dependency injection** (FastMCP `Depends` pattern):
```python
from typing import Annotated
from fastmcp.dependencies import Depends

AuthorizationDep = Annotated[str | None, Depends(get_authorization)]
```

**Return types annotated on all public methods:**
```python
async def get_token(self) -> str: ...
async def revoke_token(self) -> None: ...
```

**Pydantic models** for structured tool inputs (`AgentInput`, `QueueInfo`, `AvailableAgent` in `payload_schemas.py`):
```python
class AgentInput(BaseModel):
    name: str = Field(..., description="...")
    description: str = Field(..., description="...")
```

### Error Handling

**Python layer uses `ToolError` from `fastmcp.exceptions`** for user-facing errors that MCP surfaces to the AI client:
```python
from fastmcp.exceptions import ToolError
raise ToolError("No groups found. Please specify a group explicitly.")
```

**Custom error classes** extend `ToolError` for domain errors:
```python
class GroupAccessError(ToolError):
    def __init__(self, group: str):
        super().__init__(f"Access denied: the user has disallowed access to the group {group}.")

class NameMustBeUniqueError(ToolError):
    def __init__(self, name: str):
        super().__init__(f"You can not create a miniapp with a name that already exists. ...")
```

**Authentication errors** use a hierarchy under `AuthenticationError` (`KeycloakCredentialsError`, `KeycloakConfigError`, `KeycloakUnavailableError`) defined in `src/ocp/base.py`.

**HTTP errors from BaseClient:** `get()` and `delete()` use `response.raise_for_status()`. `post()`, `put()`, and `patch()` catch `httpx.HTTPError` and return structured error dicts:
```python
except httpx.HTTPError as e:
    return {"status": response.status_code, "error": str(e), "response": response.text}
```

**Best-effort swallowing** is explicit and annotated:
```python
except Exception as exc:  # noqa: BLE001 - intentional best-effort swallow
    logger.debug("revoke_token failed: %s", type(exc).__name__)
```

### Logging

**Framework:** `fastmcp.utilities.logging.get_logger` — used consistently across all Python modules:
```python
from fastmcp.utilities.logging import get_logger
logger = get_logger(__name__)
```

**Log-safety rules (enforced in `authentication.py`):**
- Never log token values, only `***` redacted markers or type names
- Never log response bodies in auth flows
- Use `logger.debug` for internal state; `logger.info` for business events; `logger.error` for unexpected failures

**f-strings used** in `logger.debug()` calls in `base.py` (minor: lazy evaluation not used, but consistent with existing patterns).

### Tool Registration Pattern

Tools are registered via `tool_with_callbacks` factory, not `mcp.tool` directly:
```python
mcp = FastMCP('OCP')
tool = tool_with_callbacks(mcp)

@tool(tags=[PUBLIC, APPROVAL], meta={'ui_label': 'Human-readable label'})
async def my_tool(param: str, Authorization: AuthorizationDep = None, ...) -> dict:
    """Docstring explains what the tool does and its Args."""
```

**Tag constants from `tags.py`** — never use raw strings for known tags.

**Group access check pattern** — must appear at start of tool body when `allowed_groups` is non-null:
```python
if allowed_groups:
    if group not in allowed_groups:
        raise GroupAccessError(group)
```

---

*Convention analysis: 2026-06-09*
