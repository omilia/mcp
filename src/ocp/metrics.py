import os

from fastmcp.exceptions import ToolError
from fastmcp.utilities.logging import get_logger

from .base import BaseClient

logger = get_logger(__name__)


def _resolve_metrics_base_url(base_url: str) -> str:
    """Resolve the host that actually serves metrics-api.

    Metrics-api is NOT served on the OCP management/console host. On standard
    OCP cloud deployments the management host ``*-m.ocp.ai`` maps to the
    analytics host ``*-a.ocp.ai`` (e.g. https://us1-m.ocp.ai ->
    https://us1-a.ocp.ai). An explicit OCP_METRICS_BASE_URL overrides this for
    hosts that do not follow the convention.
    """
    override = os.getenv("OCP_METRICS_BASE_URL")
    if override:
        return override.rstrip("/")
    return base_url.replace("-m.ocp.ai", "-a.ocp.ai").rstrip("/")


def _raise_on_post_error(resp):
    """Convert BaseClient.post's swallowed-error dict into a ToolError.

    BaseClient.post() does NOT raise on 4xx/5xx — it returns
    {"status": <code>, "error": <str>, "response": <body>} instead of the
    parsed JSON. A rejected request must surface as an error, not flow back
    as a "successful" body the normalizer would mis-parse.
    """
    if isinstance(resp, dict) and "error" in resp and "status" in resp:
        raise ToolError(
            f"Metrics API request failed (status {resp['status']}): {resp['error']}"
        )

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
        # Metrics-api lives on the analytics host, not the management host.
        self.base_url = _resolve_metrics_base_url(self.base_url)

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
        and extracts the "columns" key. The live API returns a
        {"columns": [...]} envelope (confirmed against us1-a.ocp.ai).

        Each column dict carries:
          - name (str): column identifier, e.g. "DIALOGDATE"
          - type (str): SQL type, e.g. "TIMESTAMP_NTZ(9)", "NUMBER(38,0)"
          - pk (bool): True = dimension (filterable / group-by key);
                       False = measure (aggregatable numeric value)

        Args:
            table_name: The table identifier, e.g. "MINIAPPS_DIALOGS_METRICS".

        Returns:
            list: Column dicts with name/type/pk fields.
                  Returns [] if the "columns" key is absent or the response
                  is not a dict.
        """
        endpoint = f"{METRICS_API_PREFIX}/{self.version}/tables/{table_name}"
        data = await self.get(endpoint)
        if isinstance(data, dict):
            return data.get("columns", [])
        return []

    def _build_query_payload(
        self,
        *,
        metrics,
        start,
        end,
        time_column,
        ocp_group_names,
        filters=None,
        timezone="UTC",
        ocp_organization_id=None,
    ) -> dict:
        """Assemble the request body shared by aggregate() and query_grouped().

        Includes the always-present keys and adds optional keys (filters,
        ocp_organization_id) only when supplied.
        """
        payload = {
            "metrics": metrics,
            "start": start,
            "end": end,
            "time_column": time_column,
            "timezone": timezone,
            "ocp_group_names": ocp_group_names,
            # The API rejects a null/absent filters field ("Filters list cannot
            # be null."), so always send a list — empty when no filters given.
            "filters": filters or [],
        }
        if ocp_organization_id is not None:
            payload["ocp_organization_id"] = ocp_organization_id
        return payload

    async def aggregate(
        self,
        table,
        *,
        metrics,
        start,
        end,
        time_column,
        ocp_group_names,
        filters=None,
        timezone="UTC",
        ocp_organization_id=None,
    ) -> dict:
        """Run an aggregation query against a metrics table.

        POSTs to the table's aggregations endpoint under
        {base_url}/{METRICS_API_PREFIX}/{version}/tables/<table>/
        with the confirmed payload. Returns the raw API body unchanged
        (normalization is the tool's responsibility). Raises ToolError when the
        API rejects the request (post() returns its error dict).

        Args:
            table: Table identifier, e.g. "DIALOGS_METRICS".
            metrics: List of {"name", "operator", "alias"} dicts. operator in
                     {sum, avg, min, max, count}; alias is the key echoed in
                     the response.
            start, end: Range bounds formatted "yyyy-MM-dd HH:mm:ss".
            time_column: TIMESTAMP column the range filters on.
            ocp_group_names: List of OCP group names scoping the query.
            filters: Optional list of {"column", "values"} dicts.
            timezone: IANA-style timezone string (default "UTC").
            ocp_organization_id: Optional org-id passthrough.
        """
        endpoint = f"{METRICS_API_PREFIX}/{self.version}/tables/{table}/aggregations"
        payload = self._build_query_payload(
            metrics=metrics,
            start=start,
            end=end,
            time_column=time_column,
            ocp_group_names=ocp_group_names,
            filters=filters,
            timezone=timezone,
            ocp_organization_id=ocp_organization_id,
        )
        resp = await self.post(endpoint, json=payload)
        _raise_on_post_error(resp)
        return resp

    async def query_grouped(
        self,
        table,
        *,
        metrics,
        start,
        end,
        time_column,
        ocp_group_names,
        group_by_columns,
        percentage=None,
        filters=None,
        timezone="UTC",
        ocp_organization_id=None,
    ) -> dict:
        """Run a grouped breakdown query against a metrics table.

        POSTs to the table's groups endpoint under
        {base_url}/{METRICS_API_PREFIX}/{version}/tables/<table>/
        with the confirmed payload plus a group_by clause. Percentages, when
        requested, are computed SERVER-SIDE via group_by.percentage — this
        method never computes them client-side. Returns the raw API body
        unchanged; raises ToolError on the API error-dict.

        Args:
            table: Table identifier.
            metrics: List of {"name", "operator", "alias"} dicts.
            start, end: Range bounds formatted "yyyy-MM-dd HH:mm:ss".
            time_column: TIMESTAMP column the range filters on.
            ocp_group_names: List of OCP group names scoping the query.
            group_by_columns: pk columns to break the result down by.
            percentage: Optional subset of group_by_columns; when truthy the
                        server computes per-group percentages for those columns.
            filters: Optional list of {"column", "values"} dicts.
            timezone: IANA-style timezone string (default "UTC").
            ocp_organization_id: Optional org-id passthrough.
        """
        endpoint = f"{METRICS_API_PREFIX}/{self.version}/tables/{table}/groups"
        payload = self._build_query_payload(
            metrics=metrics,
            start=start,
            end=end,
            time_column=time_column,
            ocp_group_names=ocp_group_names,
            filters=filters,
            timezone=timezone,
            ocp_organization_id=ocp_organization_id,
        )
        group_by = {"columns": group_by_columns}
        if percentage:
            group_by["percentage"] = percentage
        payload["group_by"] = group_by
        resp = await self.post(endpoint, json=payload)
        _raise_on_post_error(resp)
        return resp
