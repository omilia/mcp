from fastmcp.utilities.logging import get_logger

from .base import BaseClient

logger = get_logger(__name__)

# TODO: confirm against the metrics-api OpenAPI spec once available.
# Grounding search (find *openapi* + grep metrics-api|/tables in src) found NO existing routes or specs.
# Prefix follows the "{domain}-api/{area}" shape of insights.py (dialogs-api/insights), which
# also carries an explicit version segment — the closest structural analog to metrics.
# integrations.py uses "{domain}/api" but has no version segment, making it a weaker analog here.
# This constant is the single line to change when the spec is confirmed.
METRICS_API_PREFIX = "metrics-api/api"

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

        Issues GET {base_url}/{METRICS_API_PREFIX}/{version}/tables/{table_name}
        and extracts the "columns" key from the response.

        Each column dict carries:
          - name (str): column identifier, e.g. "OCP_GROUP_NAME"
          - type (str): SQL type, e.g. "VARCHAR(64)"
          - pk (bool): True = dimension (filterable / group-by key);
                       False = measure (aggregatable numeric value)

        Args:
            table_name: The table identifier, e.g. "DIALOGS_METRICS".

        Returns:
            list: Column dicts with name/type/pk fields.
                  Returns [] if the "columns" key is absent or the response is not a dict.
        """
        endpoint = f"{METRICS_API_PREFIX}/{self.version}/tables/{table_name}"
        data = await self.get(endpoint)
        if not isinstance(data, dict):
            return []
        return data.get("columns", [])
