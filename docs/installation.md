# Installation

The OCP MCP Server can be installed three ways. Pick the one that fits
your client and how often you upgrade.

| Method | Best for | Friction | Updates |
|---|---|---|---|
| **`npx` CLI installer** | Developers who already have `npx` available; writes the client config for you | Single command | Re-run the CLI |
| **`.mcpb` bundle** | Claude Desktop users; non-technical users; environments without `npx` | Drag-and-drop install with a GUI prompt for secrets | Download the new bundle and reinstall |
| **Manual MCP configuration** | Anyone comfortable editing JSON; works in all 5 supported clients | Lowest setup, no install step | Manual JSON edit per upgrade |

> Common to all methods: provide `OCP_BASE_URL` and `OCP_ACCESS_TOKEN`.
> Get a PAT from your OCP environment's IAM frontend ("Personal Access
> Tokens"). By default the generated config carries literal values
> you paste in directly (inline literal placeholders, no `${VAR}`
> indirection) — no shell-env propagation needed, which avoids the
> macOS GUI-apps-don't-inherit-zshrc problem entirely.
>
> If you'd rather not embed the PAT in a config file, see the
> `--use-env-vars` mode below — it emits `${OCP_ACCESS_TOKEN}`
> placeholders that the MCP client resolves from the launching shell.
> On macOS GUI apps, you'd then need to set the variables in
> `~/.zshenv` or launch the client from a terminal.

The package is distributed directly from the public GitHub mirror —
no npm registry account or login required. The bare `github:omilia/mcp`
URL resolves to the default branch (`main`).

---

## 1. `npx` CLI installer

```bash
npx github:omilia/mcp init --client claude --write
```

Supported clients: `cursor`, `claude`, `claude-code`, `vscode`, `codex`.

> Note: `--write` is not implemented for `codex`. The CLI will tell you
> to re-run with `--print` and paste the TOML into `~/.codex/config.toml`
> yourself. The other four clients accept `--write`.

Flags:

- `--write` — write to the default path for that client (not codex)
- `--path FILE` — write to a specific path
- `--force` — overwrite an existing `OCP` entry
- `--server-name NAME` — rename the server (default: `OCP`)
- `--base-url URL` — inject literal OCP base URL into the config
- `--access-token PAT` — inject literal PAT into the config
- `--use-env-vars` — emit `${VAR}` placeholders the MCP client must
  resolve from the launching shell env (opt into the older indirection
  pattern; mutually exclusive with `--base-url` / `--access-token`)

### Token placement modes

The default emits **literal placeholders** (`your-ocp-base-url`,
`your-ocp-access-token`) inline in the config — no `${VAR}` indirection
— so the user can paste real values directly into the config file.
Example default:

```json
"env": {
  "OCP_BASE_URL": "your-ocp-base-url",
  "OCP_ACCESS_TOKEN": "your-ocp-access-token"
}
```

For one-shot install with the values baked in, pass `--base-url` and
`--access-token`:

```bash
npx github:omilia/mcp init --client claude --write \
  --base-url "https://us1-m.ocp.ai" \
  --access-token "$OCP_ACCESS_TOKEN"
```

For indirection mode, pass `--use-env-vars`:

```bash
npx github:omilia/mcp init --client claude --write --use-env-vars
```

…produces:

```json
"env": {
  "OCP_BASE_URL": "${OCP_BASE_URL}",
  "OCP_ACCESS_TOKEN": "${OCP_ACCESS_TOKEN}"
}
```

Only use indirection if the MCP client supports `${VAR}` expansion AND
the launching shell has the env vars set.

The CLI merges into the existing config under `mcpServers.OCP` (or the
client-specific equivalent). Re-run with `--force` to upgrade.

The emitted client config invokes the same `npx github:omilia/mcp`
URL at startup, so updates are pulled automatically on the next launch
(npm caches per-ref, so re-running after a mirror push fetches the new
commit).

## 2. `.mcpb` bundle (drag-and-drop into Claude Desktop)

The `.mcpb` (MCP Bundle) is a self-contained zip that includes the
Node CLI, the vendored Python source, and a `manifest.json` describing
the user-facing config prompts. Claude Desktop installs it via the
**Settings → Connectors** UI or by opening the file directly.

### Download the bundle

The current bundle is committed to the mirror at the root of the
`main` branch:

```bash
curl -LO https://github.com/omilia/mcp/raw/main/ocp-mcp-server.mcpb
```

Or download it via the GitHub UI at
<https://github.com/omilia/mcp/blob/main/ocp-mcp-server.mcpb>.

### Install in Claude Desktop

1. Open Claude Desktop → **Settings** → **Connectors** (or **Extensions**)
2. Click **Install Extension** and select `ocp-mcp-server.mcpb`
   *(or just double-click the `.mcpb` file in Finder)*
3. Claude Desktop prompts you for `OCP_BASE_URL` and `OCP_ACCESS_TOKEN`
   (the PAT input is masked — `sensitive: true` in the manifest)
4. Click **Install**, then restart the conversation

The bundle's `manifest.json` declares both fields as `required: true`,
so install won't proceed without them.

### Requirements

The bundle ships its own Node CLI, but the Python entrypoint still needs
**`uv`** on `$PATH`. If `uv` isn't installed:

```bash
brew install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

Without `uv`, the server will fail to start with a clear error pointing
to installation instructions.

To upgrade, download the latest `ocp-mcp-server.mcpb` from the link
above and reinstall — the Connectors UI replaces the previous version.

## 3. Manual MCP configuration (copy-paste JSON)

Print the canonical config snippet for your client and paste it into
the client's MCP config file.

```bash
npx github:omilia/mcp init --client claude --print
# also: cursor, claude-code, vscode, codex
```

The output is the exact JSON to merge into your client's MCP config
file:

| Client | Config file |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code | `~/.claude.json` (or per-project `.claude/mcp.json`) |
| Cursor | `~/.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` (workspace) or user `settings.json` |
| Codex | `~/.codex/config.toml` |

Replace the literal placeholders (`your-ocp-base-url`,
`your-ocp-access-token`) with the real values, then restart the
client.

If you can't run `npx` locally, the equivalent JSON is:

```json
{
  "mcpServers": {
    "OCP": {
      "command": "npx",
      "args": ["-y", "github:omilia/mcp", "run"],
      "env": {
        "OCP_BASE_URL": "your-ocp-base-url",
        "OCP_ACCESS_TOKEN": "your-ocp-access-token"
      }
    }
  }
}
```

(VS Code uses `servers` instead of `mcpServers`; Codex uses TOML.
Run the `--print` command above to get the exact shape for your client.)

## Verifying the install

In any client, after install + restart, a fresh chat should show OCP as
a connected tool (hammer icon, "Manage connectors" panel, etc.).

Smoke-test by typing:

```
Use the read_guide tool to show me the index of available OCP guides.
```

You should see the four guides listed (`index`, `build_concierge_app`,
`add_knowledge`, `test_and_improve`). If you don't, see Troubleshooting
below.

## Authentication

The OCP MCP server supports two authentication paths and selects
between them at runtime based on which environment variables are set.
**Keycloak password grant is the recommended default**; a Personal
Access Token (PAT) is the faster alternative when you already have one
issued.

### Keycloak password grant

Set the following environment variables (or paste them into the
generated MCP client config under `env`):

- `OCP_USERNAME` — your OCP account username
- `OCP_PASSWORD` — your OCP account password
- `OCP_KEYCLOAK_REALM` — Keycloak realm name (default `master`; see the
  table below for the value to use on each deployment kind)

Use this path when your account is provisioned through Keycloak and you
do not have (or do not want to create) a long-lived PAT. The server
exchanges the credentials for an access token on first use and refreshes
proactively before expiry.

### Personal Access Token (PAT)

Set `OCP_ACCESS_TOKEN` (and `OCP_BASE_URL`). This is the path the
top-level "Common to all methods" note above documents: get a PAT from
your OCP environment's IAM frontend ("Personal Access Tokens"). The PAT
is sent as `X-OCP-PERSONAL-ACCESS-TOKEN`. When both `OCP_ACCESS_TOKEN`
and Keycloak credentials are set, the PAT wins (no Keycloak call is
made).

### Keycloak realm by environment

The Keycloak realm depends on which OCP deployment you point the MCP
server at:

| Deployment | Realm | Notes |
|---|---|---|
| Swarm (legacy OCP) | `master` | Default; `OCP_KEYCLOAK_REALM` env unset |
| Kubernetes (new OCP) | `ocp` | Set `OCP_KEYCLOAK_REALM=ocp` explicitly |

If you target the wrong realm, Keycloak returns a 404 — the server
surfaces this as a configuration error pointing at `OCP_BASE_URL` and
`OCP_KEYCLOAK_REALM` (no credentials in the message).

Tokens are held in-process memory only and are never written to disk.

## Troubleshooting

**Tool list is empty.**
The MCP client either didn't see env vars or can't reach OCP. Check:
- `OCP_BASE_URL` and `OCP_ACCESS_TOKEN` are set in the launching shell
- `npx` / `uv` are on `$PATH`
- `OCP_BASE_URL` is reachable: `curl -I "$OCP_BASE_URL"`

**`npx` clone fails or 404.**
`npx github:omilia/mcp` requires network access to GitHub and
a working `git` on `$PATH`. If you're behind a proxy, set
`HTTPS_PROXY` and `https_proxy` before invoking npx. If `main` is
reported missing or empty, no mirror has been promoted yet — use the
`.mcpb` bundle.

**`Agent has no instructions` on deploy.**
Call `update_agent_instructions` before `deploy_orc_app`. The OCP
backend rejects deployments of empty Concierge agents. See
[examples/build-and-test-concierge-app.md](examples/build-and-test-concierge-app.md).

**`UNAUTHORIZED` from `talk_to_app`.**
The app isn't deployed yet, or the chat endpoint hasn't returned a
`live_token` yet. Wait ~10 s after `deploy_orc_app` succeeds.

**Pathfinder tools return 401 with a PAT.**
Known limitation — the Pathfinder service does not yet accept PAT
authentication. Until the fix ships, the `create_pathfinder_project`,
`list_pathfinder_projects`, `add_faq_to_agent`, `list_knowledge_bases`,
and `add_knowledge_base_to_agent` tools require a Keycloak Bearer
token instead of a PAT.
