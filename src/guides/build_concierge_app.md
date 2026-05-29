# Build a Concierge App

A Concierge app is an Orchestrator application with a Concierge agent at the
top of its canvas. The Concierge can delegate to Task agents and tools.

## Prerequisites

- The user has chosen an OCP `group` for the new app and agent.
- The user has chosen a name (letters and underscores only).

## Steps

1. **Create the app**

   ```
   create_orchestrator_app(group="<group>", name="<AppName>")
   ```

   Returns `{ id, ... }`. Keep the `id` as `app_id`.

2. **Create the Concierge agent**

   ```
   create_agent(group="<group>", name="<AgentName>", agent_type="concierge")
   ```

   Returns `{ id, component_id, ... }`. Keep both — `id` is `agent_id`, and
   `component_id` is the canvas-side reference.

3. **Wire the Concierge into the app's canvas**

   ```
   add_concierge_to_orc_app(app_id="<app_id>", agent_id="<agent_id>")
   ```

   This places the Concierge as the entry node in the canvas.

4. **Set instructions (required before deploy)**

   ```
   update_agent_instructions(
       agent_id="<agent_id>",
       instructions=["You are a helpful assistant. Greet users warmly, ..."],
   )
   ```

   OCP rejects deployment of an agent with no instructions. Add at least one.

5. **(Optional) Add sub-agents or tools**

   - `add_agent_to_concierge_by_id(...)` to attach Task agents
   - `create_webservice_miniapp` + `create_webservice_agent` to give the
     Concierge a tool

6. **Deploy**

   ```
   deploy_orc_app(app_id="<app_id>")
   ```

7. **Test**

   ```
   talk_to_app(app_id="<app_id>", message="Hi")
   ```

   Returns `{ reply, greeting, session_id, app_id }`. Each call is a fresh
   chat session — `session_id` is informational only.

## Common pitfalls

- Names with spaces or hyphens are rejected by `create_orchestrator_app` —
  use CamelCase or snake_case only.
- `add_concierge_to_orc_app` must only be called once per app. Calling it
  again on an app that already has a Concierge will produce inconsistent
  canvas state.
- `deploy_orc_app` returns 400 if the Concierge has no instructions. Always
  call `update_agent_instructions` before deploying.
- `talk_to_app` requires the app to be deployed. Call `deploy_orc_app`
  first; otherwise the chat credentials endpoint will not return a
  `live_token`.
