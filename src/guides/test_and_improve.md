# Test and Improve an Agent

Run a chat against a deployed app, inspect the response, refine, redeploy,
and retest.

## Prerequisites

- The app is already deployed (`deploy_orc_app` returned success).
- You have the `app_id`.

## Single-turn smoke test

```
talk_to_app(app_id="<app_id>", message="Hi, what can you do?")
```

Returns:
```
{
  "reply": "...",
  "greeting": "..." | null,
  "session_id": "<ocp-session-id>",
  "app_id": "<app_id>"
}
```

The `greeting` is the agent's opening line for this session (if any). The
`session_id` is returned for logging/inspection only — see below.

## Multi-turn conversation

Pass `session_id` back on each follow-up call to continue the same OCP chat
session — the agent retains conversational state (history, slot values,
named entities):

```
result = talk_to_app(app_id="<app_id>", message="Let's discuss cats.")
talk_to_app(app_id="<app_id>", message="What were we just talking about?",
            session_id=result.session_id)
# → reply references cats; on a fresh session this question would return
#   "We just started our conversation."
```

Under the hood, the first call opens a WebSocket and sends `start_session_req`;
follow-up calls open a new WebSocket and send `session_resume_req` for the
same `session_id` so the agent can pick up where it left off. Replay of prior
events is suppressed so the call returns only the agent's new reply.

A note on guardrails: agents with strict customer-support instructions may
politely decline to recall arbitrary personal facts ("remember my favorite
color"). The history is preserved regardless — but the agent's behavior is
governed by its instructions. Use topic-anchored prompts ("what were we
discussing?") rather than fact-recall prompts when verifying multi-turn.

## Improve loop

1. **Identify the issue from the reply** — wrong persona, missed intent, no
   knowledge, etc.

2. **Refine** with the appropriate tool:

   - Wrong persona / instructions →
     `update_agent_instructions(agent_id=..., instructions=[...])`
   - Missing knowledge →
     `add_faq_to_agent(...)` or `add_knowledge_base_to_agent(...)`
   - Missing tool →
     `create_webservice_miniapp` + `add_tool_to_webservice_agent`
   - Wrong TTS voice →
     `get_tts_voices` + `change_tts_voice`

3. **Redeploy**:

   ```
   deploy_orc_app(app_id="<app_id>")
   ```

4. **Retest** with `talk_to_app` and compare.

## Common pitfalls

- Changes to agent config are not active until `deploy_orc_app` runs.
- Each `talk_to_app` call uses a fresh WebSocket; if you don't pass
  `session_id`, you start a new chat session and lose conversation history.
- If `talk_to_app` raises an error about missing chat credentials, the app
  is not deployed — run `deploy_orc_app` first.
- `talk_to_app` waits up to `timeout_seconds` (max 300) for the agent's
  reply. Long flows that depend on slow webservice tools may need a higher
  timeout.
