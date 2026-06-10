from fastmcp.utilities.logging import get_logger

from .base import BaseClient

logger = get_logger(__name__)

# Confirmed against Confluence (OCP Metrics API). Full URL = {base_url}/metrics-api/{version}/tables/...
# There is NO "/api" segment.
METRICS_API_PREFIX = "metrics-api"

# Default API version. Overridable via MetricsClient(version="v4").
DEFAULT_METRICS_VERSION = "v3"


class MetricsClient(BaseClient):
    """Client for the OCP generic metrics-controller endpoints.

    Provides read-only discovery of available metrics tables and their schemas.
    All requests are authenticated via BaseClient's auth resolution chain.

    URL pattern: {base_url}/{METRICS_API_PREFIX}/{version}/tables[/{table_name}]
    """

    def __init__(self, *args, version: str = DEFAULT_METRICS_VERSION, **kwargs):
        """Initialise the MetricsClient.

        Args:
            *args: Positional arguments forwarded to BaseClient (e.g. auth_header).
            version: Metrics API version segment (default "v3"). Keyword-only so it
                     is not accidentally forwarded to BaseClient.__init__.
            **kwargs: Keyword arguments forwarded to BaseClient (e.g. auth_header).
        """
        super().__init__(*args, **kwargs)
        self.version = version

    async def list_tables(self) -> list:
        """Return the list of available metrics tables from the OCP metrics API.

        Issues GET {base_url}/{METRICS_API_PREFIX}/{version}/tables and extracts
        the "tables" key from the response (a list of table-name strings).

        Returns:
            list: Table name strings, e.g. ["DIALOGS_METRICS", "AGENT_ASSIST_AGENT_KPIS"].
                  Returns [] if the "tables" key is absent or the response is not a dict.
        """
        endpoint = f"{METRICS_API_PREFIX}/{self.version}/tables"
        data = await self.get(endpoint)
        if not isinstance(data, dict):
            return []
        return data.get("tables", [])

    async def describe_table(self, table_name: str) -> list:
        """Return the column schema for a specific metrics table.

        Issues GET {base_url}/{METRICS_API_PREFIX}/{version}/tables/{table_name}.
        The metrics API returns a top-level JSON list of column dicts (a bare
        array, not a {"columns": [...]} envelope).

        Each column dict carries:
          - name (str): column identifier, e.g. "OCP_GROUP_NAME"
          - type (str): SQL type, e.g. "VARCHAR(64)"
          - pk (bool): True = dimension (filterable / group-by key);
                       False = measure (aggregatable numeric value)

        Args:
            table_name: The table identifier, e.g. "DIALOGS_METRICS".

        Returns:
            list: Column dicts with name/type/pk fields.
                  Returns [] if the response is not a top-level list.
        """
        endpoint = f"{METRICS_API_PREFIX}/{self.version}/tables/{table_name}"
        data = await self.get(endpoint)
        if isinstance(data, list):
            return data
        return []
