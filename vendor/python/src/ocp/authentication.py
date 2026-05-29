"""Keycloak password-grant authentication for the OCP MCP server.

Structural notes:

1. Uses ``httpx.AsyncClient`` — all existing ``src/ocp/*`` modules are async,
   this one matches.
2. Realm is parameterized via the ``OCP_KEYCLOAK_REALM`` env var (default
   ``master``). Swarm OCP uses ``master``; k8s OCP uses ``ocp``.
3. Log-safe: no stdout writes, no response bodies in log lines, no
   credentials in exception messages.

Token state lives in-process memory only — never on disk. Refresh tokens are
attempted before falling back to a fresh password grant, with a 30-second
proactive-refresh skew margin so a token expiring mid-request is refreshed
before it dies.

Wired into :class:`ocp.base.BaseClient` as the third autodiscovery branch
(after explicit Bearer header and ``OCP_ACCESS_TOKEN``).
"""

import os
import time

import httpx
from dotenv import load_dotenv
from fastmcp.utilities.logging import get_logger

from .base import (
    AuthenticationError,
    KeycloakConfigError,
    KeycloakCredentialsError,
    KeycloakUnavailableError,
)

load_dotenv()

logger = get_logger(__name__)

# Proactive-refresh skew margin (seconds). A cached token is considered
# expired this many seconds BEFORE its real expiry, so a token expiring
# mid-request is refreshed before it dies. Module-level so tests can
# monkey-patch it.
TOKEN_REFRESH_SKEW_SECONDS = 30

# Existence marker used in log lines when a field's presence (not value)
# matters — never log raw token values.
_REDACTED = "***"


class Authentication:
    """Keycloak password-grant client with in-memory token cache.

    One :class:`Authentication` instance per :class:`ocp.base.BaseClient` —
    the token cache is per-instance, not module-global, to avoid
    cross-client state leaks. Acceptable cost: parallel BaseClients each
    authenticate once.

    The owned ``httpx.AsyncClient`` is lazy-created on first HTTP call
    and must be closed via :meth:`aclose` on shutdown.

    Token state — access token, refresh token, expiry — is kept in
    instance attributes only. There is no filesystem persistence and no
    shared memory. Tokens die with the Python process.

    :param realm: Optional Keycloak realm override. When ``None`` (the
        default), the realm is read from the ``OCP_KEYCLOAK_REALM`` env
        var, falling back to ``"master"``. Tests pass an explicit value
        to bypass env reads.
    """

    def __init__(self, realm: str | None = None) -> None:
        self._host: str | None = os.getenv("OCP_BASE_URL")
        if not self._host:
            # Fail fast at construction so callers don't get a confusing
            # KeyError or empty-URL POST later. Body is not interpolated.
            raise KeycloakConfigError(
                "OCP_BASE_URL is not set. Set OCP_BASE_URL to the Keycloak base URL."
            )

        self._username: str | None = os.getenv("OCP_USERNAME")
        self._password: str | None = os.getenv("OCP_PASSWORD")

        # Realm resolution: explicit arg wins; else env; else "master".
        if realm is not None:
            self._realm: str = realm
        else:
            self._realm = os.getenv("OCP_KEYCLOAK_REALM") or "master"

        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0.0

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _url(self, kind: str) -> str:
        """Build the Keycloak endpoint URL for the given action.

        :param kind: ``"token"`` or ``"logout"``.
        """
        return (
            f"{self._host}/auth/realms/{self._realm}/protocol/openid-connect/{kind}"
        )

    def _ensure_client(self) -> httpx.AsyncClient:
        """Lazy-create and return the owned ``httpx.AsyncClient``."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _translate_http_error(self, status: int) -> AuthenticationError:
        """Map a Keycloak HTTP status code to an ``AuthenticationError`` subclass.

        Body is intentionally NOT passed in — Keycloak error bodies can
        echo malformed-request credentials, and we don't want them in logs
        or in re-raised exception messages.
        """
        if status == 401:
            return KeycloakCredentialsError(
                "Keycloak rejected the credentials. Check OCP_USERNAME / OCP_PASSWORD."
            )
        if status in (400, 404):
            return KeycloakConfigError(
                "Keycloak request rejected. Check OCP_BASE_URL and OCP_KEYCLOAK_REALM "
                f"(current: {self._realm})."
            )
        if 500 <= status < 600:
            return KeycloakUnavailableError(
                "Keycloak unreachable. Check OCP_BASE_URL connectivity."
            )
        # Fallback for any unexpected status (e.g. 3xx, 418). Treat as
        # unavailable rather than leaking the body — the caller can still
        # distinguish by isinstance.
        return KeycloakUnavailableError(
            "Keycloak returned an unexpected status. Check OCP_BASE_URL connectivity."
        )

    def _store_tokens(self, payload: dict) -> str:
        """Update cached token state from a Keycloak token-endpoint response.

        :param payload: The parsed JSON body. NOT logged.
        :returns: The fresh access token string.
        """
        self._access_token = payload["access_token"]
        # ``refresh_token`` is optional in OIDC; only update if present.
        if "refresh_token" in payload:
            self._refresh_token = payload["refresh_token"]
        # ``expires_in`` is seconds-until-expiry; convert to absolute epoch.
        self._token_expiry = time.time() + float(payload.get("expires_in", 0))
        return self._access_token

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def get_token(self) -> str:
        """Return a valid access token, fetching or refreshing as needed.

        Endpoint: ``{OCP_BASE_URL}/auth/realms/{realm}/protocol/openid-connect/token``.

        Order of operations:

        1. If a cached access token exists AND ``time.time() <
           _token_expiry - TOKEN_REFRESH_SKEW_SECONDS``, return it.
        2. Else if a refresh token is cached, attempt a refresh-token
           grant. On any ``AuthenticationError`` (including
           :class:`KeycloakUnavailableError` and
           :class:`KeycloakCredentialsError`), fall through to (3).
        3. Password grant. Raises one of the three error subclasses on
           failure (see :meth:`_translate_http_error`).
        """
        current_time = time.time()
        if (
            self._access_token is not None
            and current_time < self._token_expiry - TOKEN_REFRESH_SKEW_SECONDS
        ):
            return self._access_token

        # Try refresh first, but never let a refresh failure escape — fall
        # through to a fresh password grant.
        if self._refresh_token is not None:
            try:
                return await self.refresh_token()
            except AuthenticationError:
                logger.debug("refresh_token failed; falling through to password-grant")

        client = self._ensure_client()
        url = self._url("token")
        data = {
            "grant_type": "password",
            "client_id": "ocp",
            "username": self._username or "",
            "password": self._password or "",
        }
        try:
            response = await client.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
            )
        except (httpx.ConnectError, httpx.TimeoutException):
            # Type name only — no underlying exception args.
            logger.debug("Keycloak password-grant: transport error to %s", url)
            raise KeycloakUnavailableError(
                "Keycloak unreachable. Check OCP_BASE_URL connectivity."
            )

        # Endpoint + status only. Never response.text.
        logger.debug("Keycloak password-grant: status=%s", response.status_code)
        if response.status_code != 200:
            raise self._translate_http_error(response.status_code)

        return self._store_tokens(response.json())

    async def refresh_token(self) -> str:
        """Exchange the cached refresh token for a fresh access token.

        Endpoint: ``{OCP_BASE_URL}/auth/realms/{realm}/protocol/openid-connect/token``
        (same endpoint as the password grant; the ``grant_type`` form
        field selects the flow).

        Raises one of the three :class:`AuthenticationError` subclasses on
        failure; the caller in :meth:`get_token` decides whether to fall
        through to a password grant.
        """
        if self._refresh_token is None:
            # Caller bug — shouldn't be hit through get_token's guard.
            raise KeycloakConfigError(
                "No refresh token cached. Call get_token first."
            )

        client = self._ensure_client()
        url = self._url("token")
        data = {
            "grant_type": "refresh_token",
            "client_id": "ocp",
            "refresh_token": self._refresh_token,
        }
        try:
            response = await client.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
            )
        except (httpx.ConnectError, httpx.TimeoutException):
            logger.debug("Keycloak refresh-grant: transport error to %s", url)
            raise KeycloakUnavailableError(
                "Keycloak unreachable. Check OCP_BASE_URL connectivity."
            )

        logger.debug("Keycloak refresh-grant: status=%s", response.status_code)
        if response.status_code != 200:
            raise self._translate_http_error(response.status_code)

        return self._store_tokens(response.json())

    async def revoke_token(self) -> None:
        """Best-effort token revocation. Never raises.

        Endpoint: ``{OCP_BASE_URL}/auth/realms/{realm}/protocol/openid-connect/logout``.

        Called explicitly by tests or shutdown code; not chained from
        ``__aexit__`` because Authentication outlives a single request.
        Failures are caught broadly and logged at DEBUG with the
        exception type only — never the message, which may contain
        upstream URLs or credentials.

        Cached state is cleared unconditionally so a subsequent
        :meth:`get_token` cannot reuse a token that may already have
        been invalidated server-side.
        """
        if self._refresh_token is None:
            return

        client = self._ensure_client()
        url = self._url("logout")
        data = {
            "client_id": "ocp",
            "refresh_token": self._refresh_token,
        }
        try:
            await client.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
            )
        except Exception as exc:  # noqa: BLE001 - intentional best-effort swallow
            logger.debug("revoke_token failed: %s", type(exc).__name__)
        finally:
            self._access_token = None
            self._refresh_token = None
            self._token_expiry = 0.0

    async def aclose(self) -> None:
        """Close the owned ``httpx.AsyncClient`` if it was lazy-created."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
