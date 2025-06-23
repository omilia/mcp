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



