"""OCP chat WebSocket client.

Provides single-turn and resumable chat against a deployed Orchestrator app.
The OCP chat backend uses a WebSocket protocol with JSON envelopes
discriminated by a ``type`` field; this client wraps the protocol so that
MCP tools can send a message and collect the agent's reply without
managing the WebSocket lifecycle themselves.

"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import websockets
from fastmcp.utilities.logging import get_logger
from websockets.exceptions import ConnectionClosed

from .base import BaseClient

logger = get_logger(__name__)


WS_MESSAGE_TYPES = {
    "START_SESSION_REQUEST": "start_session_req",
    "START_SESSION_RESPONSE": "start_session_resp",
    "START_DIALOG_REQUEST": "start_dialog_req",
    "DIALOG_REQUEST": "dialog_req",
    "DIALOG_MESSAGE_EVENT": "dialog_message_event",
    "SESSION_RESUME_REQUEST": "session_resume_req",
    "TYPING_EVENT": "typing_event",
    "STATE_EVENT": "state_event",
    "ERROR_EVENT": "error_event",
    "STOP_SESSION_REQUEST": "stop_session_req",
}

# Sentinel sequence ID to suppress replay during resume. The server only sends
# events with sequence_id > from_sequence_id; this value is the int32 max,
# which OCP accepts (larger values like 2**63-1 trigger BAD_REQUEST).
_NO_REPLAY_SEQUENCE = 2**31 - 1

WS_STATE_EVENTS = {
    "DIALOG_END": "DIALOG_END",
    "SESSION_EXPIRED": "SESSION_EXPIRED",
}


class ChatError(Exception):
    """Raised when the chat WebSocket session cannot complete a turn."""


class ChatClient(BaseClient):
    """Open a WebSocket against a deployed app and exchange one or more turns.

    Stateless from the server's perspective: each ``start_session`` or
    ``send_message`` call opens a fresh WebSocket. Callers thread the
    returned ``session_id`` through subsequent calls to continue a dialog.
    """

    async def _get_chat_credentials(self, app_id: str) -> tuple[str, str]:
        """Fetch chat_url and live_token via the OCP web_chat endpoint."""
        endpoint = f"orchestrator/api/apps/{app_id}/web_chat/"
        response = await self.get(endpoint)
        chat_url = response.get("chat_url")
        chat_token = response.get("live_token") or response.get("deployed_token")
        if not chat_url or not chat_token:
            raise ChatError(
                f"App {app_id} did not return chat credentials. "
                "Make sure the app is deployed."
            )
        return chat_url, chat_token

    async def start_session(
        self,
        app_id: str,
        message: str | None = None,
        timeout_seconds: int = 60,
    ) -> dict:
        """Start a new chat session and optionally send the first user message.

        Returns a dict with ``session_id``, ``greeting`` (the app's opening line
        if any), and ``reply`` (the agent's response to ``message``, or None
        if no message was supplied).
        """
        chat_url, chat_token = await self._get_chat_credentials(app_id)
        async with websockets.connect(chat_url) as ws:
            session_id, greeting = await self._do_start_session(
                ws, chat_token, timeout_seconds
            )
            reply = None
            if message:
                reply = await self._do_dialog(
                    ws, chat_token, session_id, message, timeout_seconds
                )
            return {
                "session_id": session_id,
                "greeting": greeting,
                "reply": reply,
            }

    async def send_message(
        self,
        app_id: str,
        message: str,
        session_id: str | None = None,
        timeout_seconds: int = 60,
    ) -> dict:
        """Open a chat session (or resume one) and exchange one turn.

        If ``session_id`` is ``None``, a new session is started via
        ``start_session_req``; the greeting (if any) is captured and returned.
        If ``session_id`` is provided, the existing session is resumed via
        ``session_resume_req`` so that the agent retains conversational state
        across separate WebSocket connections. Replay of prior events is
        suppressed by sending a high ``from_sequence_id``.

        After the session is established (new or resumed), a single
        ``dialog_req`` is sent and the agent's reply is returned.
        """
        chat_url, chat_token = await self._get_chat_credentials(app_id)
        async with websockets.connect(chat_url) as ws:
            if session_id is None:
                session_id, greeting = await self._do_start_session(
                    ws, chat_token, timeout_seconds
                )
            else:
                await self._do_resume_session(
                    ws, chat_token, session_id, timeout_seconds
                )
                greeting = None
            reply = await self._do_dialog(
                ws, chat_token, session_id, message, timeout_seconds
            )
            return {
                "session_id": session_id,
                "greeting": greeting,
                "reply": reply,
            }

    async def _do_resume_session(
        self,
        ws: Any,
        chat_token: str,
        session_id: str,
        timeout_seconds: int,
    ) -> None:
        """Resume an existing OCP chat session on this WebSocket.

        Suppresses replay by passing a high ``from_sequence_id`` and absorbs
        any incidental events (typing, errors) before returning. Raises
        ``ChatError`` if OCP rejects the resume.
        """
        envelope = {
            "type": WS_MESSAGE_TYPES["SESSION_RESUME_REQUEST"],
            "api_key": chat_token,
            "session_id": session_id,
            "from_sequence_id": _NO_REPLAY_SEQUENCE,
            "client_message_id": str(uuid.uuid4()),
        }
        await ws.send(json.dumps(envelope))

        # OCP doesn't ack resume explicitly — drain any incidental messages
        # with a short timeout, then proceed. Errors raise immediately.
        drain_seconds = min(2.0, float(timeout_seconds))
        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=drain_seconds)
                data = json.loads(raw)
                msg_type = data.get("type")
                if msg_type == WS_MESSAGE_TYPES["ERROR_EVENT"]:
                    raise ChatError(f"OCP error during session_resume: {data}")
                # Silently absorb replay events and typing events
                if msg_type in (
                    WS_MESSAGE_TYPES["DIALOG_MESSAGE_EVENT"],
                    WS_MESSAGE_TYPES["STATE_EVENT"],
                    WS_MESSAGE_TYPES["TYPING_EVENT"],
                ):
                    continue
        except asyncio.TimeoutError:
            # No more events — resume is complete (or no replay needed).
            return
        except ConnectionClosed as exc:
            raise ChatError(
                f"OCP closed the WebSocket during session_resume: {exc}"
            ) from exc

    async def _do_start_session(
        self,
        ws: Any,
        chat_token: str,
        timeout_seconds: int,
    ) -> tuple[str, str | None]:
        envelope = {
            "type": WS_MESSAGE_TYPES["START_SESSION_REQUEST"],
            "api_key": chat_token,
            "session_id": None,
            "client_message_id": str(uuid.uuid4()),
            "utterance": "",
            "input_fields": None,
            "semantics": None,
        }
        await ws.send(json.dumps(envelope))

        session_id: str | None = None
        greeting: str | None = None

        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == WS_MESSAGE_TYPES["START_SESSION_RESPONSE"]:
                    session_id = data.get("session_id")
                    if greeting is not None or not self._expects_greeting(data):
                        break
                elif msg_type == WS_MESSAGE_TYPES["DIALOG_MESSAGE_EVENT"]:
                    content = self._extract_agent_content(data)
                    if content:
                        greeting = content
                        if session_id is not None:
                            break
                elif msg_type == WS_MESSAGE_TYPES["ERROR_EVENT"]:
                    raise ChatError(f"OCP error during start_session: {data}")
                elif msg_type == WS_MESSAGE_TYPES["TYPING_EVENT"]:
                    continue
        except asyncio.TimeoutError as exc:
            raise ChatError("Timed out waiting for start_session response") from exc
        except ConnectionClosed as exc:
            raise ChatError(f"OCP closed the WebSocket during start_session: {exc}") from exc

        if session_id is None:
            raise ChatError("start_session did not return a session_id")
        return session_id, greeting

    async def _do_dialog(
        self,
        ws: Any,
        chat_token: str,
        session_id: str,
        utterance: str,
        timeout_seconds: int,
    ) -> str | None:
        envelope = {
            "type": WS_MESSAGE_TYPES["DIALOG_REQUEST"],
            "api_key": chat_token,
            "session_id": session_id,
            "client_message_id": str(uuid.uuid4()),
            "utterance": utterance,
            "input_fields": None,
            "semantics": None,
        }
        await ws.send(json.dumps(envelope))

        try:
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == WS_MESSAGE_TYPES["DIALOG_MESSAGE_EVENT"]:
                    content = self._extract_agent_content(data)
                    if content:
                        return content
                elif msg_type == WS_MESSAGE_TYPES["STATE_EVENT"]:
                    state = data.get("state")
                    if state == WS_STATE_EVENTS["SESSION_EXPIRED"]:
                        raise ChatError("Chat session expired")
                    if state == WS_STATE_EVENTS["DIALOG_END"]:
                        return None
                elif msg_type == WS_MESSAGE_TYPES["ERROR_EVENT"]:
                    raise ChatError(f"OCP error during dialog: {data}")
                elif msg_type == WS_MESSAGE_TYPES["TYPING_EVENT"]:
                    continue
        except asyncio.TimeoutError as exc:
            raise ChatError("Timed out waiting for agent reply") from exc
        except ConnectionClosed as exc:
            raise ChatError(f"OCP closed the WebSocket during dialog: {exc}") from exc

    @staticmethod
    def _expects_greeting(start_response: dict) -> bool:
        """Some OCP variants embed the greeting in start_session_resp itself.

        If start_session_resp already carries a greeting, treat it as the
        full response and don't wait for a separate dialog_message_event.
        """
        greeting_keys = ("welcome", "greeting", "initial_message")
        return not any(start_response.get(k) for k in greeting_keys)

    @staticmethod
    def _extract_agent_content(data: dict) -> str | None:
        source = data.get("source")
        if source not in ("BOT", "AGENT"):
            return None
        content = (
            data.get("utterance")
            or data.get("dialog_response", {}).get("prompt", {}).get("content")
            or data.get("dialog_response", {}).get("prompt", {}).get("masked_content")
        )
        return str(content) if content else None
