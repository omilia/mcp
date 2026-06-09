# Omilia MCP Server

> **Documentation:** [learn.ocp.ai](https://learn.ocp.ai)

A Model Context Protocol server that lets MCP-aware LLM clients build,
deploy, and operate conversational AI agents on the **Omilia Cloud
Platform (OCP)** through natural language. Create an orchestrator app,
spin up an autonomous agent, attach a knowledge base from a URL, wire a
webservice tool, deploy, and smoke-test the result — all from a chat
prompt in your editor or desktop app.

The server runs locally and talks to OCP over authenticated HTTPS. No
data leaves your machine except the requests your MCP client makes on
your behalf.

## Supported MCP clients

Claude Desktop, Claude Code, Cursor, VS Code (with Copilot), and Codex.

## Install

**Recommended — interactive wizard (answers a few prompts, then confirms before writing anything):**

```bash
npx github:omilia/mcp init
```

The wizard selects your client, collects credentials with masked input,
runs prereq checks (Node 20+, `uv`), installs the config, and prints a
PASS/FAIL smoke-test summary before exiting. See the
[Interactive wizard section](docs/installation.md#0-interactive-wizard-recommended)
in the installation guide for the full prompt sequence.

**Non-interactive / CI — supply all flags to skip prompts:**

```bash
npx github:omilia/mcp init --client <claude|claude-code|cursor|vscode|codex>
```

See the full installation guide at [docs/installation.md](docs/installation.md)
for the `.mcpb` one-click bundle (Claude Desktop) and manual configuration
alternatives.

## Authentication

Recommended: Keycloak password grant — set `OCP_USERNAME`, `OCP_PASSWORD`, and `OCP_KEYCLOAK_REALM` (default `master`).
Faster path: a Personal Access Token via `OCP_ACCESS_TOKEN`.
Both run in-memory only — credentials never persist. See [docs/installation.md](docs/installation.md) for the realm-by-environment table.

## Tools (31)

The MCP surface, grouped by area. Each row is one tool your MCP-aware
LLM can invoke through `tools/call`.

### Discovery & guides

| Tool | Description |
|---|---|
| `read_guide` | Return a markdown guide for a canonical OCP MCP workflow |
| `list_groups` | List OCP groups the current user has access to |
| `list_agents` | List all agents in scope |
| `list_knowledge_bases` | List knowledge bases (FAQ vector stores) |
| `list_pathfinder_projects` | List Pathfinder projects (search filterable) |
| `search_orchestrator_apps` | Search Orchestrator apps |
| `search_miniapps` | Search miniapps |
| `search_numbers` | Search phone numbers attached to apps |
| `search_variable_collections` | Search variable collections |
| `search_dialog_logs` | Search dialog logs by group / app / date |

### Orchestrator apps

| Tool | Description |
|---|---|
| `create_orchestrator_app` | Create a new Orchestrator app |
| `get_orchestrator_app` | Fetch an app's canvas |
| `add_concierge_to_orc_app` | Wire a Concierge into an app's canvas |
| `deploy_orc_app` | Deploy an Orchestrator app |
| `talk_to_app` | Send a message to a deployed app and receive the agent's reply |

### Agents (Concierge & Task)

| Tool | Description |
|---|---|
| `create_agent` | Create a Concierge or Task agent |
| `update_agent_instructions` | Update an agent's instructions |
| `update_concierge` | Update the Concierge's sub-agent list |
| `add_agent_to_concierge` | Add a sub-agent to a Concierge |
| `add_escalation_queue_to_agent` | Add escalation queue(s) to an agent |

### WebService miniapps & agents

| Tool | Description |
|---|---|
| `create_webservice_miniapp` | Create a WebService miniapp (HTTP tool) |
| `get_miniapp` | Fetch a miniapp's configuration |
| `edit_webservice_miniapp` | Edit a WebService miniapp's request config |
| `set_miniapp_prompt` | Set welcome / initial / error prompts on a miniapp |
| `create_webservice_agent` | Create a Task agent that uses a WebService miniapp |
| `add_tool_to_webservice_agent` | Add another WebService tool to a Task agent |

### Pathfinder (knowledge)

| Tool | Description |
|---|---|
| `create_pathfinder_project` | Create a Pathfinder project |
| `add_faq_to_agent` | Crawl a URL into a Pathfinder FAQ and attach it to an agent |
| `add_knowledge_base_to_agent` | Attach an existing knowledge base to an agent |

### Variables & dialogs

| Tool | Description |
|---|---|
| `get_collection_variables` | List variables in a collection |
| `get_dialog_logs` | Fetch the full dialog log for a dialog ID |

## Examples

End-to-end walkthroughs of the canonical journeys (build, deploy, test,
extend) live at [docs/examples/](docs/examples/).

## License

MIT. See [LICENSE](LICENSE).

## Provenance

This repository is auto-generated from an internal source on every
release. Generated from internal commit `333d04b1f44b7f54b0803eba5c1631dd8b101444` on branch
`mirror/333d04b1f44b`. This release exposes 31 tools
across src/main.py, src/server.py. PRs against this repository cannot be merged
back upstream — open issues for visibility and feedback; bug fixes are
tracked in the internal source.
