from .base import BaseClient
import json


class MiniAppsClient(BaseClient):
    def __init__(self):
        super().__init__()
        self._active_version = None

    def get_apps(self, page_size=10, search_term=None):
        """Gets a list of applications."""
        endpoint = "miniapps/api/apps"
        params = {"pageSize": page_size, "searchTerm": search_term}
        return self.get(endpoint, params=params)

    def get_active_version(self):
        """Gets the active version from the config."""
        endpoint = "miniapps/api/config"
        response = self.get(endpoint)
        return response.get("config", {}).get("activeVersion")

    def get_miniapp(self, miniapp_id):
        """Gets a specific miniapp by ID using the active version.

        Args:
            miniapp_id (str): The ID of the miniapp to retrieve

        Returns:
            dict: The miniapp data
        """
        if not self._active_version:
            self._active_version = self.get_active_version()

        endpoint = f"miniapps/api/apps/{self._active_version}/{miniapp_id}"
        return self.get(endpoint)

    def update_miniapp(self, miniapp_id, miniapp_json):
        """Updates a specific miniapp by ID using the active version.

        Args:
            miniapp_id (str): The ID of the miniapp to update
            miniapp_json (dict): The miniapp data to update with

        Returns:
            dict: The updated miniapp data
        """
        if not self._active_version:
            self._active_version = self.get_active_version()

        endpoint = f"miniapps/api/apps/{self._active_version}/{miniapp_id}"
        payload = miniapp_json.get("model") if "model" in miniapp_json else miniapp_json

        # Create form-data with JSON file
        files = {
            "file": (f"{miniapp_id}.json", json.dumps(payload), "application/json")
        }

        response = self.put(endpoint, files=files)
        return response.json()
