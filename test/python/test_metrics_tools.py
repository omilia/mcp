import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

# Make src importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

os.environ.setdefault("OCP_BASE_URL", "https://test.ocp.ai")

import main  # noqa: E402 — must import after sys.path and env are set
from fastmcp.exceptions import ToolError  # noqa: E402


def _make_metrics_client_mock(describe_return):
    """Return an async-context-manager mock for main.MetricsClient.

    The mock's __aenter__ returns an object whose describe_table is an
    AsyncMock returning *describe_return*.
    """
    inner = MagicMock()
    inner.describe_table = AsyncMock(return_value=describe_return)
    inner.list_tables = AsyncMock(return_value=[])

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=inner)
    cm.__aexit__ = AsyncMock(return_value=False)

    outer = MagicMock(return_value=cm)
    return outer


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


if __name__ == "__main__":
    unittest.main()
