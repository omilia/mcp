# Example: Build, Deploy, and Test a Concierge App

This walks through the canonical agent-build journey using the OCP MCP
server. The trace below was captured from a live run against
`https://us1-m.ocp.ai` on 2026-05-23.

The same sequence runs from any MCP client (Claude Desktop, Claude Code,
Cursor, VS Code, Codex) once the server is attached and a PAT is set.

## Prerequisites

- An OCP Personal Access Token with permission to create apps in your group.
  See [How to test this from Claude](#how-to-test-this-from-claude) at the
  end of this doc.
- Environment variables:
  - `OCP_BASE_URL` (e.g. `https://us1-m.ocp.ai`)
  - `OCP_ACCESS_TOKEN` (your PAT)
- A target OCP group you can write to.

## Natural-language prompt that drives the whole journey

```
Read the build_concierge_app guide, then create an Orchestrator app
named SupportBot in group <your-group>. Make it a Concierge with
instructions: "You are a helpful customer support assistant. Greet
users warmly, ask clarifying questions, and explain what you can
help with." Deploy it. Then send "Let's discuss cats — what's
your favorite breed?" and follow up with "What topic were we
just discussing?" to confirm it remembers across turns.
```

An LLM client will chain the tools listed below to fulfill that prompt.

---

## Step-by-step trace

Each section shows the MCP tool call, what the server does under the hood
(HTTP method + endpoint, or WebSocket envelope), and the response shape.

### 1. Orient with the guide

```
read_guide(name="build_concierge_app")
```

Returns the canonical 7-step Concierge sequence with example arguments.
You can also call `read_guide()` (no args) to list all available guides.

### 2. Confirm authentication

```
list_agents()
```

`GET /orchestrator/api/agents/` — returns the agents in your tenant. A
non-empty result confirms PAT auth (`X-OCP-PERSONAL-ACCESS-TOKEN`) is
working.

### 3. Create the Orchestrator app

```
create_orchestrator_app(group="<group>", name="SupportBot")
```

`POST /orchestrator/api/apps/` with `{group, name, application_type: "agentic"}`.

Returns `{ id, canvas, ... }`. Keep `id` as `app_id` and `canvas` for
later steps that touch the canvas.

### 4. Create the Concierge agent

```
create_agent(group="<group>", name="SupportConcierge", agent_type="concierge")
```

`POST /orchestrator/api/agents/` with
`{name, group, type: "concierge", description: "", labels: [], input_fields: [], output_fields: []}`.

Returns `{ id, component_id, ... }`. The `component_id` field is sometimes
`null` on first response — downstream tools fetch the agent again to
resolve it.

### 5. Wire the Concierge into the app's canvas

```
add_concierge_to_orc_app(app_id="<app_id>", agent_id="<agent_id>")
```

Internally:

1. `GET /orchestrator/api/apps/{app_id}/` to read the canvas_id
2. `GET /orchestrator/api/agents/{agent_id}/` to resolve component_id
3. `PUT /orchestrator/api/canvases/{canvas_id}/` to write a canvas that
   places the Concierge as the entry node

The response may include a warning `AGENT_WITHOUT_INSTRUCTIONS` — that's
your cue to set instructions before deploying.

### 6. Set instructions (required before deploy)

```
update_agent_instructions(
    agent_id="<agent_id>",
    instructions=[
        "You are a helpful customer support assistant. Greet users "
        "warmly, ask clarifying questions, and explain what you can "
        "help with. Keep responses concise and friendly.",
    ],
)
```

`PATCH /orchestrator/api/agents/{agent_id}/`. Without this step,
`deploy_orc_app` returns 400 with:

> Your App can not be deployed because it contains problems: Agent
> 'SupportConcierge' has no instructions.

### 7. (Optional) Add sub-agents, tools, or knowledge

- `add_agent_to_concierge_by_id(...)` — attach Task agents
- `create_webservice_miniapp` + `create_webservice_agent` — give the
  Concierge an HTTP tool
- `add_faq_to_agent(url=..., pathfinder_project_id=..., agent_id=...)`
  — attach a Pathfinder-ingested FAQ

### 8. Deploy

```
deploy_orc_app(app_id="<app_id>")
```

`POST /orchestrator/api/apps/{app_id}/deploy/`. Returns `{detail: "..."}`
on success. Wait ~5–10 seconds for the deployment to settle before
chatting (the orchestrator needs to provision the chat WebSocket
endpoint).

### 9. Chat — first turn (new session)

```
talk_to_app(app_id="<app_id>", message="Let's discuss cats — what's your favorite breed?")
```

Internally:

1. `GET /orchestrator/api/apps/{app_id}/web_chat/` returns `chat_url` and
   `live_token`
2. WebSocket connects to `chat_url`
3. Sends `start_session_req`:
   ```json
   {
     "type": "start_session_req",
     "api_key": "<live_token>",
     "session_id": null,
     "client_message_id": "<uuid>",
     "utterance": "",
     "input_fields": null,
     "semantics": null
   }
   ```
4. Receives `start_session_resp` with `session_id`
5. Receives `dialog_message_event` (source=BOT) — captured as **greeting**
6. Sends `dialog_req`:
   ```json
   {
     "type": "dialog_req",
     "api_key": "<live_token>",
     "session_id": "<session_id>",
     "client_message_id": "<uuid>",
     "utterance": "Let's discuss cats — what's your favorite breed?"
   }
   ```
7. Receives `dialog_message_event` (source=BOT) — captured as **reply**

Returns:

```json
{
  "app_id": "<app_id>",
  "session_id": "7efd6a83-a746-4108-b98a-8c195fd4339c",
  "greeting": "Hi there! How can I help you today?",
  "reply": "That's a fun question, but I'm here to help with customer support. Is there something I can assist you with today?"
}
```

### 10. Chat — second turn (resume the same session)

```
talk_to_app(
    app_id="<app_id>",
    message="What topic were we just discussing?",
    session_id="7efd6a83-a746-4108-b98a-8c195fd4339c",
)
```

Opens a **new** WebSocket (each MCP call is stateless on the server side)
and:

1. Sends `session_resume_req`:
   ```json
   {
     "type": "session_resume_req",
     "api_key": "<live_token>",
     "session_id": "7efd6a83-a746-4108-b98a-8c195fd4339c",
     "from_sequence_id": 2147483647,
     "client_message_id": "<uuid>"
   }
   ```
   The high `from_sequence_id` (int32 max) suppresses replay of prior
   events. Larger values like `2**63 - 1` cause OCP to return `BAD_REQUEST`.
2. Briefly drains any stray events with a 2 s window
3. Sends `dialog_req` with the same session_id and the new utterance
4. Receives `dialog_message_event` — **reply**

Returns:

```json
{
  "app_id": "<app_id>",
  "session_id": "7efd6a83-a746-4108-b98a-8c195fd4339c",
  "greeting": null,
  "reply": "We were just talking about cats and cat breeds. But that's outside what I'm here to help with — is there something else I can assist you with?"
}
```

The resumed agent recalls the prior topic. On a fresh session without
`session_id`, the same question returns *"We just started our
conversation, so we haven't discussed anything yet."*

---

## Improve loop

Once you can chat with the agent, the standard refinement cycle is:

1. Run a few `talk_to_app` calls to probe behavior
2. Pick a refinement:
   - `update_agent_instructions` for persona/scope changes
   - `add_faq_to_agent` or `add_knowledge_base_to_agent` for knowledge gaps
   - `create_webservice_miniapp` + `add_tool_to_webservice_agent` for new
     tool capabilities
3. `deploy_orc_app` to make changes live
4. Repeat `talk_to_app` to compare

---

## How to run this from Claude (or any MCP client)

Install the server in your client first — see [installation.md](../installation.md)
for the three install paths (manual config, CLI, `.mcpb` bundle).

Once the server is connected, drive the journey from a chat prompt:

```
Read the build_concierge_app guide. Then create a Concierge app
called SupportBot in group <your-group> with friendly customer-support
instructions, deploy it, send the message "Let's discuss cats",
and in a follow-up turn ask "What were we just talking about?"
to confirm the agent remembers across turns.
```

Claude will call the MCP tools in sequence (`read_guide` →
`create_orchestrator_app` → `create_agent` → `add_concierge_to_orc_app` →
`update_agent_instructions` → `deploy_orc_app` → `talk_to_app` × 2) and
report the agent's replies inline.

For installation issues, see the
[Troubleshooting section of installation.md](../installation.md#troubleshooting).
