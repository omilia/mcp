import os

import httpx
from dotenv import load_dotenv
from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

load_dotenv()


class AuthenticationError(Exception):
    """Raised when no auth credentials are available, or as a base for Keycloak-specific failures."""


class KeycloakCredentialsError(AuthenticationError):
    """Keycloak rejected the credentials (401 invalid_grant). Check OCP_USERNAME / OCP_PASSWORD."""


class KeycloakConfigError(AuthenticationError):
    """Keycloak request rejected (400 invalid_request, 404 realm not found). Check OCP_BASE_URL and OCP_KEYCLOAK_REALM."""


class KeycloakUnavailableError(AuthenticationError):
    """Keycloak unreachable (5xx, ConnectError, TimeoutException). Check OCP_BASE_URL connectivity."""


class BaseClient:
    """
    A base client for making authenticated requests to the OCP API.

    Authenticates in priority order (first match wins, no explicit mode flag):

      1. ``auth_header`` passed to the constructor — propagated from an MCP
         client that holds a Keycloak session token. Sent as
         ``Authorization: Bearer <token>``.
      2. ``OCP_ACCESS_TOKEN`` environment variable — a Personal Access
         Token. Sent as ``X-OCP-PERSONAL-ACCESS-TOKEN: <pat>``.
      3. ``OCP_USERNAME`` AND ``OCP_PASSWORD`` environment variables —
         Keycloak password-grant. A per-BaseClient :class:`Authentication`
         instance is lazy-constructed; the actual token fetch is deferred
         to the first request (see :meth:`_get_auth_headers`). Realm is
         read from ``OCP_KEYCLOAK_REALM`` (default ``master``). The
         Authentication instance is intentionally NOT a module-level
         singleton — each BaseClient owns its own Authentication and
         token cache so parallel requests don't share state.

    If none of the above resolve, ``AuthenticationError`` is raised the
    first time a request is sent (not at construction). The error message
    enumerates all three options.

    The owned :class:`Authentication` (when branch 3 is active) outlives a
    single ``async with`` request context; ``__aexit__`` does NOT chain into
    ``Authentication.aclose()``. Callers running a long-lived MCP server
    process do not need to close it explicitly; tests that want to revoke
    the refresh token call ``Authentication.revoke_token()`` /
    ``Authentication.aclose()`` directly.
    """

    def __init__(self, auth_header: str = None):
        if auth_header:
            if not auth_header.startswith("Bearer "):
                auth_header = f"Bearer {auth_header}"
            self._auth_header = {"Authorization": f"{auth_header}"}
            self._authentication = None
        elif os.getenv("OCP_ACCESS_TOKEN"):
            self._auth_header = {"X-OCP-PERSONAL-ACCESS-TOKEN": os.getenv("OCP_ACCESS_TOKEN")}
            self._authentication = None
        elif os.getenv("OCP_USERNAME") and os.getenv("OCP_PASSWORD"):
            # Branch 3: Keycloak password-grant. The Authentication
            # instance is per-BaseClient, NOT module-level — keeps token
            # state isolated per request context.
            # Lazy-import Authentication to break the module-load cycle
            # (authentication.py imports the error classes defined above).
            from .authentication import Authentication
            self._auth_header = None
            self._authentication = Authentication()
        else:
            self._auth_header = None
            self._authentication = None
        self.base_url = os.getenv("OCP_BASE_URL", "https://pub.demo.ocp.ai")
        self._client = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _get_auth_headers(self):
        """Return the auth headers, or raise if no credentials are available.

        Resolution mirrors the precedence chosen in :meth:`__init__`:

          - Bearer / PAT branch (``self._auth_header`` set): returns the
            pre-built dict directly. No network call.
          - Keycloak branch (``self._authentication`` set): awaits
            :meth:`Authentication.get_token` and wraps the bare access
            token as ``Authorization: Bearer <token>``. Any
            :class:`AuthenticationError` subclass raised by ``get_token``
            (``KeycloakCredentialsError``, ``KeycloakConfigError``,
            ``KeycloakUnavailableError``) propagates unchanged.
          - Else: raises :class:`AuthenticationError` whose message
            enumerates all three auth options.
        """
        if self._auth_header:
            return self._auth_header
        if self._authentication is not None:
            token = await self._authentication.get_token()
            return {"Authorization": f"Bearer {token}"}
        raise AuthenticationError(
            "No OCP credentials available. Set the OCP_ACCESS_TOKEN "
            "environment variable (Personal Access Token), OR set "
            "OCP_USERNAME and OCP_PASSWORD (Keycloak password grant; "
            "optionally OCP_KEYCLOAK_REALM, default 'master'), OR pass "
            "an auth_header to the BaseClient constructor (Bearer token)."
        )

    async def get(self, endpoint, **kwargs):
        """
        Performs a GET request to a specified endpoint with authentication.
        """
        headers = await self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = await self._client.get(url, headers=headers, **kwargs)
        logger.debug(f"GET request to {url} returned {response.status_code} with response {response.text}")
        response.raise_for_status()
        return response.json()

    async def post(self, endpoint, **kwargs):
        """
        Performs a POST request to a specified endpoint with authentication.
        """
        headers = await self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = await self._client.post(url, headers=headers, **kwargs)
        logger.debug(f"POST request to {url} returned {response.status_code} with response {response.text}")
        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {"status": response.status_code, "error": str(e), "response": response.text}
        return response.json()

    async def put(self, endpoint, **kwargs):
        """
        Performs a PUT request to a specified endpoint with authentication.
        """
        headers = await self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = await self._client.put(url, headers=headers, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            return {"status": response.status_code, "error": str(e), "response": response.text}
        return response.json()

    async def delete(self, endpoint, **kwargs):
        """
        Performs a DELETE request to a specified endpoint with authentication.
        """
        headers = await self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = await self._client.delete(url, headers=headers, **kwargs)
        response.raise_for_status()
        # Delete requests often return 204 No Content, which has no JSON body
        if response.status_code != 204:
            return response.json()
        return None

    async def patch(self, endpoint, **kwargs):
        """
        Performs a PATCH request to a specified endpoint with authentication.
        """
        headers = await self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        base = self.base_url or "https://pub.demo.ocp.ai"
        url = f"{base}/{endpoint}"
        response = await self._client.patch(url, headers=headers, **kwargs)
        response.raise_for_status()
        # Handle empty response bodies (204 No Content, etc)
        if response.status_code == 204 or not response.text:
            return {"status": "success", "status_code": response.status_code}
        return response.json()

    async def get_binary(self, endpoint, **kwargs):
        """
        Performs a GET request and returns binary content (for file downloads like ZIP).
        """
        headers = await self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        # Ensure base_url is set
        base = self.base_url or "https://pub.demo.ocp.ai"
        endpoint_str = str(endpoint) if endpoint else ""
        url = f"{base}/{endpoint_str}"
        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            logger.error(f"Invalid URL format: {url}")
            return {"error": f"Invalid URL: {url}"}

        response = await self._client.get(url, headers=headers, **kwargs)
        logger.debug(f"GET binary request to {url} returned {response.status_code}")
        response.raise_for_status()
        return response.content

    # TODO: try to do this with httpx instead of using the requests library
    # async def post_multipart(self, endpoint, file_path=None, payload_data=None, filename="",
    #                          file_field_name="train_data", file_mime_type="text/plain", include_payload=True, **kwargs):
    #     """
    #     Performs a POST request with multipart/form-data encoding.
    #     Useful for APIs that require multipart encoding (e.g., file uploads with metadata).
    #
    #     Args:
    #         endpoint: API endpoint
    #         file_path: Path to file to upload (optional)
    #         payload_data: Dictionary containing the payload (will be JSON-encoded)
    #         filename: Name of the file in the multipart form
    #         file_field_name: Name of the file field in multipart form (default: "train_data")
    #         file_mime_type: MIME type for the file (default: "text/plain")
    #         include_payload: Whether to include the payload field in form data (default: True)
    #     """
    #     try:
    #         headers = await self._get_auth_headers()
    #         if 'headers' in kwargs:
    #             headers.update(kwargs.pop('headers'))
    #
    #         base = self.base_url or "https://pub.demo.ocp.ai"
    #         url = f"{base}/{endpoint}"
    #
    #         logger.debug(f"post_multipart - base_url: {self.base_url}, endpoint: {endpoint}, final_url: {url}")
    #
    #         # Prepare multipart fields for MultipartEncoder
    #         fields = {}
    #
    #         # Add file if provided
    #         if file_path and file_path.strip():
    #             with open(file_path, 'rb') as f:
    #                 file_content = f.read()
    #             fields[file_field_name] = (filename, file_content, file_mime_type)
    #         # Note: If no file_path provided, don't add an empty file field to multipart data
    #
    #         # Add payload as form data only if include_payload is True and payload_data is not empty
    #         if include_payload and payload_data:
    #             fields['payload'] = json.dumps(payload_data)
    #
    #         logger.debug(f"Preparing multipart request - fields: {list(fields.keys())}")
    #
    #         # Create the multipart encoder and set content type
    #         mp_encoder = MultipartEncoder(fields=fields)
    #         headers['Content-Type'] = mp_encoder.content_type
    #
    #         logger.debug(f"Content-Type: {mp_encoder.content_type}")
    #
    #         # Use requests library in a thread pool executor since MultipartEncoder works best with requests
    #         def make_request():
    #             try:
    #                 response = requests.post(url, headers=headers, data=mp_encoder, verify=False, **kwargs)
    #                 response.raise_for_status()
    #                 # Handle empty responses (e.g., 204 No Content)
    #                 if response.status_code == 204 or not response.text:
    #                     logger.debug(f"post_multipart returned empty response body (status: {response.status_code})")
    #                     return {"status": "success", "status_code": response.status_code,
    #                             "message": "Empty response body"}
    #                 try:
    #                     return response.json()
    #                 except requests.exceptions.JSONDecodeError as json_error:
    #                     logger.warning(
    #                         f"Failed to parse JSON response: {json_error}. Response text: {response.text[:200]}")
    #                     return {
    #                         "status": "success",
    #                         "status_code": response.status_code,
    #                         "message": "Response body could not be parsed as JSON",
    #                         "raw_response": response.text[:500]
    #                     }
    #             except requests.exceptions.HTTPError as http_error:
    #                 logger.error(f"HTTP Error {http_error.response.status_code}: {http_error.response.text}")
    #                 logger.error(f"Request URL: {url}")
    #                 logger.error(f"Request headers: {headers}")
    #                 raise
    #
    #         loop = asyncio.get_event_loop()
    #         result = await loop.run_in_executor(ThreadPoolExecutor(max_workers=1), make_request)
    #         return result
    #
    #     except Exception as e:
    #         logger.error(f"post_multipart error: {type(e).__name__}: {str(e)}", exc_info=True)
    #         return {
    #             "error": str(e),
    #             "error_type": type(e).__name__,
    #             "base_url": self.base_url,
    #             "endpoint": endpoint
    #         }
