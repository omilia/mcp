from datetime import datetime

from fastmcp.utilities.logging import get_logger

from .base import BaseClient

logger = get_logger(__name__)


class InsightsClient(BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        url_mapping = {  # The analytics stack is served under a different domain in specific environments
            "https://us1-m.ocp.ai": "https://us1-a.ocp.ai",
            "https://eu1-m.ocp.ai": "https://eu1-a.ocp.ai",
        }
        self.base_url = url_mapping.get(self.base_url, self.base_url)

    async def get_dialog_log(self, dialog_id: str) -> str:
        """Gets the dialog log for a specific dialog ID.

        Args:
            dialog_id (str): The ID of the dialog to retrieve logs for

        Returns:
            dict: The dialog log data
        """
        endpoint = f"dialogs-api/insights/v2/dialogs/{dialog_id}/log"
        headers = await self._get_auth_headers()
        url = f"{self.base_url}/{endpoint}"
        response = await self._client.get(url, headers=headers)
        return response.text

    async def search_dialogs(
        self,
        apps: list,
        from_date: str,
        to_date: str,
        size: int = 10,
        ani: list = None,
        dialog_group: str = None,
        application_layer: bool = True,
    ) -> list[dict]:
        """Search dialogs using various filter criteria. Can also be requested by users by saying
        "find sessions", "search logs" or "identify dialog logs"

        Args:
            apps (list): List of app IDs to filter by
            from_date (str): Start date/time in ISO format or milliseconds timestamp
            to_date (str): End date/time in ISO format or milliseconds timestamp
            size (int, optional): Number of results to return. Defaults to 10
            ani (list, optional): List of ANIs to filter by. ANI is the phone number of the caller.
            dialog_group (str, optional): Dialog group ID to filter by
            application_layer (bool, optional): Whether to include application layer. Defaults to True

        Returns:
            list[dict]: Search results containing matching dialogs
        """
        endpoint = "dialogs-api/insights/v2/dialogs/search"

        from_ms = self._convert_to_ms(from_date)
        to_ms = self._convert_to_ms(to_date)
        # Build search payload from parameters
        payload = {
            "from_ms": from_ms,
            "to_ms": to_ms,
            "size": size,
            "query_params": {
                "application_layer": application_layer,
                "ocp_group_names": [dialog_group],
            },
            "order": "desc",
        }

        if apps:
            payload["query_params"]["apps"] = apps
        if ani:
            payload["query_params"]["ani"] = ani

        response = await self.post(endpoint, json=payload)
        return response.get("dialogs", [])

    def _convert_to_ms(self, timestamp):
        """Convert ISO datetime string to milliseconds timestamp.

        Args:
            timestamp (str): ISO formatted datetime string or milliseconds timestamp

        Returns:
            str: Milliseconds timestamp
        """
        if isinstance(timestamp, str) and not timestamp.isdigit():
            dt = datetime.fromisoformat(timestamp.replace("Z", "+03:00"))
            return str(int(dt.timestamp() * 1000))
        return timestamp
