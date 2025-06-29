from datetime import datetime
import requests

from .base import BaseClient


class InsightsClient(BaseClient):
    def __init__(self):
        super().__init__()
        self.base_url = "https://us1-a.ocp.ai"

    def get_dialog_log(self, dialog_id: str) -> str:
        """Gets the dialog log for a specific dialog ID.
        
        Args:
            dialog_id (str): The ID of the dialog to retrieve logs for
            
        Returns:
            dict: The dialog log data
        """
        endpoint = f"dialogs-api/insights/v2/dialogs/{dialog_id}/log"
        headers = self._get_auth_headers()
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=headers)

        return response.text
    
    def search_dialogs(self, apps: list, from_date: str, to_date: str, 
                      size: int = 10, ani: list = None, dialog_group: str = None,
                      ocp_group_names: list = None, region: str = None, 
                      application_layer: bool = True, steps_gt: int = None):
        """Search dialogs using various filter criteria. Can also be requested by users by saying
        "find sessions", "search logs" or "identify dialog logs"
        
        Args:
            apps (list): List of app IDs to filter by
            from_date (str): Start date/time in ISO format or milliseconds timestamp
            to_date (str): End date/time in ISO format or milliseconds timestamp
            size (int, optional): Number of results to return. Defaults to 10
            ani (list, optional): List of ANIs to filter by. ANI is the phone number of the caller.
            dialog_group (str, optional): Dialog group ID to filter by
            ocp_group_names (list, optional): List of OCP group names to filter by
            region (str, optional): Region to filter by
            application_layer (bool, optional): Whether to include application layer. Defaults to True
            steps_gt (int, optional): Filter dialogs with steps greater than this number
            
        Returns:
            dict: Search results containing matching dialogs
        """
        endpoint = "dialogs-api/insights/v2/dialogs/search"
        headers = self._get_auth_headers()

        from_ms = self._convert_to_ms(from_date)
        to_ms = self._convert_to_ms(to_date)
        # Build search payload from parameters
        payload = {
            "apps": apps,
            "from": from_ms,
            "to": to_ms,
            "size": size,
            "applicationLayer": application_layer
        }

        # Add optional parameters if provided
        if ani:
            payload["ani"] = ani
        if dialog_group:
            payload["dialogGroup"] = dialog_group
        if ocp_group_names:
            payload["ocpGroupNames"] = ocp_group_names
        if region:
            payload["region"] = region
        if steps_gt:
            payload["stepsGt"] = steps_gt

        response = self.post(endpoint, json=payload)
        return response.get("dialogs", {})


    def _convert_to_ms(self, timestamp):
        """Convert ISO datetime string to milliseconds timestamp.
        
        Args:
            timestamp (str): ISO formatted datetime string or milliseconds timestamp
            
        Returns:
            str: Milliseconds timestamp
        """
        if isinstance(timestamp, str) and not timestamp.isdigit():
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return str(int(dt.timestamp() * 1000))
        return timestamp


