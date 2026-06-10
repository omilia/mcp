import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Make src importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

os.environ.setdefault("OCP_BASE_URL", "https://test.ocp.ai")

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

    def test_non_dict_response_returns_empty(self):
        """list_tables() returns [] for a non-dict response."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, ["unexpected", "list"])

        result = _run(client.list_tables())

        self.assertEqual(result, [])


class TestDescribeTable(unittest.TestCase):
    def test_describe_table_url_and_parse(self):
        """describe_table() returns columns with pk classification and calls the correct URL."""
        client = MetricsClient(auth_header="tok")
        columns_data = [
            {"name": "OCP_GROUP_NAME", "type": "VARCHAR(64)", "pk": True},
            {"name": "DIALOGS_COUNT", "type": "NUMBER(18,0)", "pk": False},
        ]
        fake_http = _wire_client(client, {"columns": columns_data})

        result = _run(client.describe_table("DIALOGS_METRICS"))

        self.assertEqual(len(result), 2)
        pk_col = next(c for c in result if c["pk"] is True)
        measure_col = next(c for c in result if c["pk"] is False)
        self.assertEqual(pk_col["name"], "OCP_GROUP_NAME")
        self.assertEqual(measure_col["name"], "DIALOGS_COUNT")

        called_url = fake_http.get.call_args[0][0]
        self.assertTrue(called_url.endswith("/tables/DIALOGS_METRICS"))

    def test_missing_columns_key_returns_empty(self):
        """describe_table() returns [] when the response has no 'columns' key."""
        client = MetricsClient(auth_header="tok")
        _wire_client(client, {})

        result = _run(client.describe_table("X"))

        self.assertEqual(result, [])

    def test_non_dict_response_returns_empty(self):
        """describe_table() returns [] for a non-dict response."""
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


if __name__ == "__main__":
    unittest.main()
