import asyncio
import os
import re
import sys
import unittest
import unittest.mock as um
from unittest.mock import AsyncMock, MagicMock

# Make src importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

os.environ.setdefault("OCP_BASE_URL", "https://test.ocp.ai")

import main  # noqa: E402 — must import after sys.path and env are set
from fastmcp.exceptions import ToolError  # noqa: E402


def _make_metrics_client_mock(describe_return, aggregate_return=None, grouped_return=None):
    """Return an async-context-manager mock for main.MetricsClient.

    The mock's __aenter__ returns an inner object whose describe_table /
    aggregate / query_grouped are AsyncMocks. The inner object is also exposed
    as ``outer.inner`` so tests can assert call/await behavior.
    """
    inner = MagicMock()
    inner.describe_table = AsyncMock(return_value=describe_return)
    inner.list_tables = AsyncMock(return_value=[])
    inner.aggregate = AsyncMock(
        return_value=aggregate_return if aggregate_return is not None else {"metrics": []}
    )
    inner.query_grouped = AsyncMock(
        return_value=grouped_return if grouped_return is not None else {"metrics": []}
    )
    inner.version = "v3"

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=False)

    outer = MagicMock(return_value=cm)
    outer.inner = inner
    return outer


# Representative table schema: exactly one TIMESTAMP column (auto-detectable),
# two other dimensions (one excluded), and two measures.
_SCHEMA = [
    {"name": "STREAM_START_DATETIME", "type": "TIMESTAMP", "pk": True},
    {"name": "FLOW_INSTANCE_STATUS", "type": "VARCHAR(32)", "pk": True},
    {"name": "OCP_GROUP_NAME", "type": "VARCHAR(64)", "pk": True},
    {"name": "TOTAL_FLOWS", "type": "NUMBER(18,0)", "pk": False},
    {"name": "DURATION", "type": "NUMBER(18,2)", "pk": False},
]
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


class TestToolRegistration(unittest.TestCase):
    def test_tools_registered_and_public(self):
        """Both tools are registered on the FastMCP instance and carry the PUBLIC tag."""
        t1 = asyncio.run(main.mcp.get_tool("list_metrics_tables"))
        t2 = asyncio.run(main.mcp.get_tool("describe_metrics_table"))
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)
        self.assertIn("public", t1.tags)
        self.assertIn("public", t2.tags)


class TestDescribeMetricsTable(unittest.TestCase):
    _COLUMNS = [
        {"name": "OCP_GROUP_NAME", "type": "VARCHAR(64)", "pk": True},
        {"name": "DIALOGS_COUNT", "type": "NUMBER(18,0)", "pk": False},
    ]

    def test_describe_classifies_dimensions_and_measures(self):
        """describe_metrics_table classifies pk=True as dimensions, pk=False as measures."""
        mock_client = _make_metrics_client_mock(self._COLUMNS)

        import unittest.mock as um
        with um.patch.object(main, "MetricsClient", mock_client):
            result = asyncio.run(
                main.describe_metrics_table(
                    table_name="DIALOGS_METRICS",
                    Authorization="tok",
                    execution_mode="normal",
                )
            )

        self.assertEqual(result["table"], "DIALOGS_METRICS")
        self.assertEqual(len(result["columns"]), 2)
        self.assertEqual(len(result["dimensions"]), 1)
        self.assertEqual(result["dimensions"][0]["name"], "OCP_GROUP_NAME")
        self.assertEqual(len(result["measures"]), 1)
        self.assertEqual(result["measures"][0]["name"], "DIALOGS_COUNT")

    def test_describe_unknown_table_raises(self):
        """describe_metrics_table raises ToolError naming list_metrics_tables for empty result."""
        mock_client = _make_metrics_client_mock([])

        import unittest.mock as um
        with um.patch.object(main, "MetricsClient", mock_client):
            with self.assertRaises(ToolError) as ctx:
                asyncio.run(
                    main.describe_metrics_table(
                        table_name="NOPE",
                        Authorization="tok",
                        execution_mode="normal",
                    )
                )

        self.assertIn("list_metrics_tables", str(ctx.exception))


class TestQueryMetricsAggregation(unittest.TestCase):
    def _run_tool(self, mock_client, **kwargs):
        params = dict(Authorization="tok", execution_mode="normal")
        params.update(kwargs)
        with um.patch.object(main, "MetricsClient", mock_client):
            return asyncio.run(main.query_metrics_aggregation(**params))

    def test_aggregation_happy_path_normalizes(self):
        """Returns normalized totals mapping the API alias to its value."""
        agg = {"metrics": [{"name": "count_TOTAL_FLOWS", "values": 8923}]}
        mock_client = _make_metrics_client_mock(_SCHEMA, aggregate_return=agg)

        result = self._run_tool(
            mock_client,
            table="DIALOGS_METRICS",
            measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
            ocp_group_names=["ocp-qa"],
            start="2025-07-23 11:00:00",
            end="2025-08-23 12:02:00",
        )

        mock_client.inner.aggregate.assert_awaited_once()
        self.assertEqual(result["table"], "DIALOGS_METRICS")
        self.assertEqual(result["version"], "v3")
        self.assertEqual(result["ocp_group_names"], ["ocp-qa"])
        self.assertEqual(result["range"], {"start": "2025-07-23 11:00:00", "end": "2025-08-23 12:02:00", "timezone": "UTC"})
        self.assertEqual(len(result["results"]), 1)
        r = result["results"][0]
        self.assertEqual(r, {"measure": "TOTAL_FLOWS", "operator": "count", "alias": "count_TOTAL_FLOWS", "value": 8923})

    def test_missing_group_raises_before_api_call(self):
        """Omitting ocp_group_names raises ToolError naming list_groups; aggregate never awaited."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                ocp_group_names=None,
            )
        self.assertIn("list_groups", str(ctx.exception))
        mock_client.inner.aggregate.assert_not_awaited()

    def test_measure_that_is_dimension_raises(self):
        """A pk (dimension) name used as a measure raises ToolError naming describe_metrics_table."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "FLOW_INSTANCE_STATUS", "operator": "count"}],
                ocp_group_names=["g"],
            )
        msg = str(ctx.exception)
        self.assertIn("FLOW_INSTANCE_STATUS", msg)
        self.assertIn("describe_metrics_table", msg)
        mock_client.inner.aggregate.assert_not_awaited()

    def test_invalid_operator_raises(self):
        """An operator outside the enum raises ToolError naming the operator."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "median"}],
                ocp_group_names=["g"],
            )
        self.assertIn("median", str(ctx.exception))
        mock_client.inner.aggregate.assert_not_awaited()

    def test_non_pk_filter_column_raises(self):
        """A filter on a measure (pk=False) column raises ToolError naming it + describe_metrics_table."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                ocp_group_names=["g"],
                filters=[{"column": "TOTAL_FLOWS", "values": [1]}],
            )
        msg = str(ctx.exception)
        self.assertIn("TOTAL_FLOWS", msg)
        self.assertIn("describe_metrics_table", msg)
        mock_client.inner.aggregate.assert_not_awaited()

    def test_excluded_filter_column_raises(self):
        """OCP_GROUP_NAME cannot be used as a filter column even though it is pk."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError):
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                ocp_group_names=["g"],
                filters=[{"column": "OCP_GROUP_NAME", "values": ["x"]}],
            )
        mock_client.inner.aggregate.assert_not_awaited()

    def test_default_window_last_24h(self):
        """Omitting start/end sends now-24h / now formatted yyyy-MM-dd HH:mm:ss."""
        mock_client = _make_metrics_client_mock(_SCHEMA, aggregate_return={"metrics": []})
        self._run_tool(
            mock_client,
            table="T",
            measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
            ocp_group_names=["g"],
        )
        kwargs = mock_client.inner.aggregate.call_args.kwargs
        self.assertRegex(kwargs["start"], _TS_RE)
        self.assertRegex(kwargs["end"], _TS_RE)

    def test_iso_offset_start_raises(self):
        """An ISO-offset / T-form start is rejected at the tool boundary."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                ocp_group_names=["g"],
                start="2026-06-01T00:00:00+02:00",
            )
        self.assertIn("yyyy-MM-dd HH:mm:ss", str(ctx.exception))
        mock_client.inner.aggregate.assert_not_awaited()

    def test_time_column_auto_detected(self):
        """A single TIMESTAMP column is auto-detected and passed to aggregate."""
        mock_client = _make_metrics_client_mock(_SCHEMA, aggregate_return={"metrics": []})
        self._run_tool(
            mock_client,
            table="T",
            measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
            ocp_group_names=["g"],
        )
        self.assertEqual(mock_client.inner.aggregate.call_args.kwargs["time_column"], "STREAM_START_DATETIME")

    def test_time_column_ambiguous_raises(self):
        """Zero or multiple TIMESTAMP columns with no explicit time_column raises ToolError."""
        two_ts = _SCHEMA + [{"name": "STREAM_END_DATETIME", "type": "TIMESTAMP", "pk": True}]
        mock_client = _make_metrics_client_mock(two_ts)
        with self.assertRaises(ToolError):
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                ocp_group_names=["g"],
            )
        mock_client.inner.aggregate.assert_not_awaited()


class TestQueryMetricsGrouped(unittest.TestCase):
    def _run_tool(self, mock_client, **kwargs):
        params = dict(Authorization="tok", execution_mode="normal")
        params.update(kwargs)
        with um.patch.object(main, "MetricsClient", mock_client):
            return asyncio.run(main.query_metrics_grouped(**params))

    def test_grouped_happy_path_with_percentage(self):
        """Returns per-dimension rows; percentage requested server-side and read back."""
        grouped = {
            "metrics": [
                {
                    "name": "count_TOTAL_FLOWS",
                    "groups": [
                        {"key": ["COMPLETED"], "value": 7845, "percentage": {"value": 63.2}},
                        {"key": ["FAILED"], "value": 4560, "percentage": {"value": 36.8}},
                    ],
                }
            ]
        }
        mock_client = _make_metrics_client_mock(_SCHEMA, grouped_return=grouped)

        result = self._run_tool(
            mock_client,
            table="T",
            measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
            group_by=["FLOW_INSTANCE_STATUS"],
            ocp_group_names=["ocp-qa"],
            percentage=True,
        )

        self.assertEqual(result["dimensions"], ["FLOW_INSTANCE_STATUS"])
        self.assertEqual(len(result["rows"]), 2)
        completed = next(r for r in result["rows"] if r["FLOW_INSTANCE_STATUS"] == "COMPLETED")
        self.assertEqual(completed["measures"], {"count_TOTAL_FLOWS": 7845})
        self.assertEqual(completed["percentage"], 63.2)
        # percentage requested server-side for the group-by columns
        self.assertEqual(mock_client.inner.query_grouped.call_args.kwargs["percentage"], ["FLOW_INSTANCE_STATUS"])

    def test_grouped_without_percentage(self):
        """Default (percentage=False): query_grouped called with percentage=None; rows omit percentage."""
        grouped = {
            "metrics": [
                {"name": "count_TOTAL_FLOWS", "groups": [{"key": ["COMPLETED"], "value": 7845}]}
            ]
        }
        mock_client = _make_metrics_client_mock(_SCHEMA, grouped_return=grouped)

        result = self._run_tool(
            mock_client,
            table="T",
            measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
            group_by=["FLOW_INSTANCE_STATUS"],
            ocp_group_names=["ocp-qa"],
        )

        self.assertIsNone(mock_client.inner.query_grouped.call_args.kwargs["percentage"])
        self.assertNotIn("percentage", result["rows"][0])

    def test_grouped_non_pk_column_raises(self):
        """A pk=False group_by column raises ToolError naming it; query_grouped never awaited."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                group_by=["TOTAL_FLOWS"],
                ocp_group_names=["g"],
            )
        msg = str(ctx.exception)
        self.assertIn("TOTAL_FLOWS", msg)
        self.assertIn("describe_metrics_table", msg)
        mock_client.inner.query_grouped.assert_not_awaited()

    def test_grouped_missing_group_raises(self):
        """Omitting ocp_group_names raises ToolError naming list_groups before any API call."""
        mock_client = _make_metrics_client_mock(_SCHEMA)
        with self.assertRaises(ToolError) as ctx:
            self._run_tool(
                mock_client,
                table="T",
                measures=[{"name": "TOTAL_FLOWS", "operator": "count"}],
                group_by=["FLOW_INSTANCE_STATUS"],
                ocp_group_names=[],
            )
        self.assertIn("list_groups", str(ctx.exception))
        mock_client.inner.query_grouped.assert_not_awaited()

    def test_grouped_merges_metrics_by_key_not_index(self):
        """Two metrics with differently-ordered groups[] pair to the correct dimension key."""
        grouped = {
            "metrics": [
                {"name": "count_TOTAL_FLOWS", "groups": [
                    {"key": ["COMPLETED"], "value": 10},
                    {"key": ["FAILED"], "value": 2},
                ]},
                {"name": "avg_DURATION", "groups": [
                    {"key": ["FAILED"], "value": 5.0},
                    {"key": ["COMPLETED"], "value": 30.0},
                ]},
            ]
        }
        mock_client = _make_metrics_client_mock(_SCHEMA, grouped_return=grouped)

        result = self._run_tool(
            mock_client,
            table="T",
            measures=[
                {"name": "TOTAL_FLOWS", "operator": "count"},
                {"name": "DURATION", "operator": "avg"},
            ],
            group_by=["FLOW_INSTANCE_STATUS"],
            ocp_group_names=["g"],
        )

        completed = next(r for r in result["rows"] if r["FLOW_INSTANCE_STATUS"] == "COMPLETED")
        failed = next(r for r in result["rows"] if r["FLOW_INSTANCE_STATUS"] == "FAILED")
        self.assertEqual(completed["measures"], {"count_TOTAL_FLOWS": 10, "avg_DURATION": 30.0})
        self.assertEqual(failed["measures"], {"count_TOTAL_FLOWS": 2, "avg_DURATION": 5.0})


if __name__ == "__main__":
    unittest.main()
