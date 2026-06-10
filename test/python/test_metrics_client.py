import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Make src importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

os.environ.setdefault("OCP_BASE_URL", "https://test.ocp.ai")

from fastmcp.exceptions import ToolError  # noqa: E402
from ocp.metrics import DEFAULT_METRICS_VERSION, METRICS_API_PREFIX, MetricsClient  # noqa: E402


def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


def _make_response(json_data):
    """Return a fake httpx-response-like object."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    resp.text = str(json_data)
    return resp


def _wire_client(client, json_data):
    """Replace the HTTP layer on *client* with a fake returning *json_data*."""
    fake_http = MagicMock()
    fake_http.get = AsyncMock(return_value=_make_response(json_data))
    client._client = fake_http
    return fake_http


def _wire_post(client, json_data):
    """Replace the HTTP layer's POST on *client* with a fake returning *json_data*."""
    fake_http = MagicMock()
    fake_http.post = AsyncMock(return_value=_make_response(json_data))
    client._client = fake_http
    return fake_http


class TestListTables(unittest.TestCase):
    def test_list_tables_url_and_parse(self):
        """list_tables() returns the 'tables' list and calls the correct URL."""
        client = MetricsClient(auth_header="tok")
        tables_data = ["DIALOGS_METRICS", "AGENT_ASSIST_AGENT_KPIS"]
        fake_http = _wire_client(client, {"tables": tables_data})

        result = _run(client.list_tables())

        self.assertEqual(result, tables_data)
        fake_http.get.assert_awaited_once()
        called_url = fake_http.get.call_args[0][0]
        expected_url = f"https://test.ocp.ai/{METRICS_API_PREFIX}/{DEFAULT_METRICS_VERSION}/tables"
        self.assertEqual(called_url, expected_url)

    def test_version_override(self):
        """MetricsClient(version='v4') uses /v4/ in the URL."""
        client = MetricsClient(auth_header="tok", version="v4")
        fake_http = _wire_client(client, {"tables": []})

        _run(client.list_tables())

        called_url = fake_http.get.call_args[0][0]
        self.assertIn("/v4/tables", called_url)

    def test_missing_tables_key_returns_empty(self):
        """list_tables() returns [] when the response has no 'tables' key."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, {})

        result = _run(client.list_tables())

        self.assertEqual(result, [])

    def test_list_tables_url_has_no_api_segment(self):
        """Regression: the list_tables URL is /metrics-api/v3/tables with NO /api/ segment."""
        client = MetricsClient(auth_header="tok")
        fake_http = _wire_client(client, {"tables": []})

        _run(client.list_tables())

        called_url = fake_http.get.call_args[0][0]
        self.assertEqual(called_url, "https://test.ocp.ai/metrics-api/v3/tables")
        self.assertNotIn("/api/", called_url)

    def test_non_dict_response_returns_empty(self):
        """list_tables() returns [] for a non-dict response."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, ["unexpected", "list"])

        result = _run(client.list_tables())

        self.assertEqual(result, [])


class TestDescribeTable(unittest.TestCase):
    def test_describe_table_url_and_parse(self):
        """describe_table() returns the top-level column list with pk classification intact."""
        client = MetricsClient(auth_header="tok")
        columns_data = [
            {"name": "OCP_GROUP_NAME", "type": "VARCHAR(64)", "pk": True},
            {"name": "DIALOGS_COUNT", "type": "NUMBER(18,0)", "pk": False},
        ]
        # The metrics API returns a BARE ARRAY, not {"columns": [...]}.
        fake_http = _wire_client(client, columns_data)

        result = _run(client.describe_table("DIALOGS_METRICS"))

        self.assertEqual(len(result), 2)
        pk_col = next(c for c in result if c["pk"] is True)
        measure_col = next(c for c in result if c["pk"] is False)
        self.assertEqual(pk_col["name"], "OCP_GROUP_NAME")
        self.assertEqual(measure_col["name"], "DIALOGS_COUNT")

        called_url = fake_http.get.call_args[0][0]
        self.assertTrue(called_url.endswith("/tables/DIALOGS_METRICS"))
        self.assertIn("/metrics-api/v3/", called_url)
        self.assertNotIn("/api/", called_url)

    def test_describe_table_parses_top_level_list_mixed_pk(self):
        """Regression: a top-level list with mixed pk True/False is returned verbatim."""
        client = MetricsClient(auth_header="tok")
        columns_data = [
            {"name": "FLOW_INSTANCE_STATUS", "type": "VARCHAR(32)", "pk": True},
            {"name": "STREAM_START_DATETIME", "type": "TIMESTAMP", "pk": True},
            {"name": "TOTAL_FLOWS", "type": "NUMBER(18,0)", "pk": False},
        ]
        _wire_client(client, columns_data)

        result = _run(client.describe_table("FLOWS"))

        self.assertEqual(result, columns_data)
        self.assertEqual([c["pk"] for c in result], [True, True, False])

    def test_dict_response_returns_empty(self):
        """describe_table() returns [] when the response is a dict (not the expected list)."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, {})

        result = _run(client.describe_table("X"))

        self.assertEqual(result, [])

    def test_non_list_response_returns_empty(self):
        """describe_table() returns [] for a None/non-list response."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, None)

        result = _run(client.describe_table("X"))

        self.assertEqual(result, [])


class TestMissingKeysReturnEmpty(unittest.TestCase):
    def test_both_methods_return_empty_for_empty_dict(self):
        """Both list_tables() and describe_table() return [] when response is {}."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, {})

        self.assertEqual(_run(client.list_tables()), [])

        # Re-wire for second call (AsyncMock reuse is fine but be explicit)
        _wire_client(client, {})
        self.assertEqual(_run(client.describe_table("X")), [])


_METRICS = [{"name": "INTENTS_HANDLED", "operator": "count", "alias": "INTENT_COUNT"}]


class TestAggregate(unittest.TestCase):
    def test_aggregate_url_and_payload(self):
        """aggregate() POSTs to the /aggregations endpoint with the confirmed payload."""
        client = MetricsClient(auth_header="tok")
        fake_http = _wire_post(client, {"metrics": [{"name": "INTENT_COUNT", "values": 8923}]})

        result = _run(
            client.aggregate(
                "DIALOGS_METRICS",
                metrics=_METRICS,
                start="2025-07-23 11:00:00",
                end="2025-08-23 12:02:00",
                time_column="STREAM_START_DATETIME",
                ocp_group_names=["ocp-qa"],
            )
        )

        self.assertEqual(result, {"metrics": [{"name": "INTENT_COUNT", "values": 8923}]})
        fake_http.post.assert_awaited_once()
        called_url = fake_http.post.call_args[0][0]
        self.assertEqual(
            called_url,
            "https://test.ocp.ai/metrics-api/v3/tables/DIALOGS_METRICS/aggregations",
        )
        payload = fake_http.post.call_args.kwargs["json"]
        self.assertEqual(payload["metrics"], _METRICS)
        self.assertEqual(payload["start"], "2025-07-23 11:00:00")
        self.assertEqual(payload["end"], "2025-08-23 12:02:00")
        self.assertEqual(payload["time_column"], "STREAM_START_DATETIME")
        self.assertEqual(payload["timezone"], "UTC")
        self.assertEqual(payload["ocp_group_names"], ["ocp-qa"])
        # filters omitted when not supplied; org id omitted when not supplied
        self.assertNotIn("filters", payload)
        self.assertNotIn("ocp_organization_id", payload)

    def test_aggregate_optional_keys_included_when_supplied(self):
        """filters and ocp_organization_id appear in the payload only when supplied."""
        client = MetricsClient(auth_header="tok")
        fake_http = _wire_post(client, {"metrics": []})

        _run(
            client.aggregate(
                "DIALOGS_METRICS",
                metrics=_METRICS,
                start="2025-07-23 11:00:00",
                end="2025-08-23 12:02:00",
                time_column="STREAM_START_DATETIME",
                ocp_group_names=["ocp-qa"],
                filters=[{"column": "REGION", "values": ["us-west-2"]}],
                ocp_organization_id="org-1",
            )
        )

        payload = fake_http.post.call_args.kwargs["json"]
        self.assertEqual(payload["filters"], [{"column": "REGION", "values": ["us-west-2"]}])
        self.assertEqual(payload["ocp_organization_id"], "org-1")

    def test_aggregate_error_dict_raises_toolerror(self):
        """A post() error-dict return is converted into a ToolError with status + message."""
        client = MetricsClient(auth_header="tok")
        client.post = AsyncMock(
            return_value={"status": 400, "error": "Bad column", "response": "{}"}
        )

        with self.assertRaises(ToolError) as ctx:
            _run(
                client.aggregate(
                    "DIALOGS_METRICS",
                    metrics=_METRICS,
                    start="2025-07-23 11:00:00",
                    end="2025-08-23 12:02:00",
                    time_column="STREAM_START_DATETIME",
                    ocp_group_names=["ocp-qa"],
                )
            )

        msg = str(ctx.exception)
        self.assertIn("400", msg)
        self.assertIn("Bad column", msg)

    def test_aggregate_returns_raw_body_unchanged(self):
        """On a normal dict response, aggregate returns the body verbatim (no normalization)."""
        client = MetricsClient(auth_header="tok")
        body = {"metrics": [{"name": "INTENT_COUNT", "values": "8923"}], "filters": {}}
        _wire_post(client, body)

        result = _run(
            client.aggregate(
                "DIALOGS_METRICS",
                metrics=_METRICS,
                start="2025-07-23 11:00:00",
                end="2025-08-23 12:02:00",
                time_column="STREAM_START_DATETIME",
                ocp_group_names=["ocp-qa"],
            )
        )

        self.assertEqual(result, body)


class TestQueryGrouped(unittest.TestCase):
    def test_grouped_url_and_group_by(self):
        """query_grouped() POSTs to /groups with group_by.columns."""
        client = MetricsClient(auth_header="tok")
        fake_http = _wire_post(client, {"metrics": [{"name": "INTENT_COUNT", "groups": []}]})

        _run(
            client.query_grouped(
                "DIALOGS_METRICS",
                metrics=_METRICS,
                start="2025-10-05 11:00:00",
                end="2025-10-11 12:02:00",
                time_column="STREAM_START_DATETIME",
                ocp_group_names=["ocp-qa"],
                group_by_columns=["FLOW_INSTANCE_STATUS"],
            )
        )

        called_url = fake_http.post.call_args[0][0]
        self.assertEqual(
            called_url,
            "https://test.ocp.ai/metrics-api/v3/tables/DIALOGS_METRICS/groups",
        )
        payload = fake_http.post.call_args.kwargs["json"]
        self.assertEqual(payload["group_by"], {"columns": ["FLOW_INSTANCE_STATUS"]})
        self.assertNotIn("percentage", payload["group_by"])

    def test_grouped_with_percentage(self):
        """When percentage is supplied, group_by.percentage carries the subset."""
        client = MetricsClient(auth_header="tok")
        fake_http = _wire_post(client, {"metrics": []})

        _run(
            client.query_grouped(
                "DIALOGS_METRICS",
                metrics=_METRICS,
                start="2025-10-05 11:00:00",
                end="2025-10-11 12:02:00",
                time_column="STREAM_START_DATETIME",
                ocp_group_names=["ocp-qa"],
                group_by_columns=["FLOW_INSTANCE_STATUS"],
                percentage=["FLOW_INSTANCE_STATUS"],
            )
        )

        payload = fake_http.post.call_args.kwargs["json"]
        self.assertEqual(payload["group_by"]["percentage"], ["FLOW_INSTANCE_STATUS"])

    def test_grouped_error_dict_raises_toolerror(self):
        """query_grouped shares the post-error-dict -> ToolError guard."""
        client = MetricsClient(auth_header="tok")
        client.post = AsyncMock(
            return_value={"status": 422, "error": "Invalid group_by", "response": "{}"}
        )

        with self.assertRaises(ToolError) as ctx:
            _run(
                client.query_grouped(
                    "DIALOGS_METRICS",
                    metrics=_METRICS,
                    start="2025-10-05 11:00:00",
                    end="2025-10-11 12:02:00",
                    time_column="STREAM_START_DATETIME",
                    ocp_group_names=["ocp-qa"],
                    group_by_columns=["FLOW_INSTANCE_STATUS"],
                )
            )

        self.assertIn("422", str(ctx.exception))

    def test_grouped_returns_raw_body_unchanged(self):
        """A normal grouped response is returned verbatim for the tool to normalize."""
        client = MetricsClient(auth_header="tok")
        body = {
            "metrics": [
                {"name": "INTENT_COUNT", "groups": [{"key": ["COMPLETED"], "value": 7845}]}
            ]
        }
        _wire_post(client, body)

        result = _run(
            client.query_grouped(
                "DIALOGS_METRICS",
                metrics=_METRICS,
                start="2025-10-05 11:00:00",
                end="2025-10-11 12:02:00",
                time_column="STREAM_START_DATETIME",
                ocp_group_names=["ocp-qa"],
                group_by_columns=["FLOW_INSTANCE_STATUS"],
            )
        )

        self.assertEqual(result, body)


if __name__ == "__main__":
    unittest.main()
