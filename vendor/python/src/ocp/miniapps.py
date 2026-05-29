import json

from fastmcp.utilities.logging import get_logger

from utils import get_announcement_announce_list, NameMustBeUniqueError

from .base import BaseClient

logger = get_logger(__name__)


class MiniAppsClient(BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_version = None

    async def get_apps(self, page_size=10, search_term=None):
        """Gets a list of applications."""
        endpoint = "miniapps/api/apps"
        params = {"pageSize": page_size, "searchTerm": search_term}
        return await self.get(endpoint, params=params)

    async def get_active_version(self):
        """Gets the active version from the config."""
        endpoint = "miniapps/api/config"
        response = await self.get(endpoint)
        return response.get("config", {}).get("activeVersion")

    async def get_miniapp(self, miniapp_id):
        """Gets a specific miniapp by ID using the active version.

        Args:
            miniapp_id (str): The ID of the miniapp to retrieve

        Returns:
            dict: The miniapp data
        """
        if not self._active_version:
            self._active_version = await self.get_active_version()

        endpoint = f"miniapps/api/apps/{self._active_version}/{miniapp_id}"
        return await self.get(endpoint)

    async def update_miniapp(self, miniapp_id, miniapp_json):
        """Updates a specific miniapp by ID using the active version.

        Args:
            miniapp_id (str): The ID of the miniapp to update
            miniapp_json (dict): The miniapp data to update with

        Returns:
            dict: The updated miniapp data
        """
        if not self._active_version:
            self._active_version = await self.get_active_version()

        endpoint = f"miniapps/api/apps/{self._active_version}/{miniapp_id}"
        payload = miniapp_json.get("model") if "model" in miniapp_json else miniapp_json

        # Create form-data with JSON file
        files = {
            "file": (f"{miniapp_id}.json", json.dumps(payload), "application/json")
        }

        return await self.put(endpoint, files=files)

    @staticmethod
    def get_miniapp_group(miniapp_id:str) -> str:
        """
        Gets the group of a miniapp by ID.
        """
        return miniapp_id.split(".")[-1]

    async def _create_intent_banking_miniapp(self, name:str, group:str) -> str:
        """
        Creates a new Banking2 intent miniapp with static languages, and sensitivity.
        Returns the miniapp ID.
        """
        if not self._active_version:
            self._active_version = await self.get_active_version()
            
        endpoint = "miniapps/api/apps"
        payload = {
            "name": name,
            "type": "Intent",
            "group": group,
            "domain": "Banking2.MiniApps",
            "languages": ["en-US"],
            "sensitivity": "None",
            "version": self._active_version
        }
        resp = await self.post(endpoint, json=payload)
        return resp.get("miniAppId") 

    async def _create_webservice_miniapp(self, name:str, group:str) -> str:
        """
        Creates a new webservice miniapp.
        Returns the miniapp ID.
        """
        if not self._active_version:
            self._active_version = await self.get_active_version()

        endpoint = "miniapps/api/apps"
        payload = {
            "name": name,
            "type": "WebService.MiniApps",
            "group": group,
            "languages": ["en-US"],
            "sensitivity": "None",
            "version": self._active_version
        }
        resp = await self.post(endpoint, json=payload)
        
        if "status" in resp and resp["status"] == 409:
            raise NameMustBeUniqueError(name)
        return resp.get("miniAppId")

    async def _create_announcement_miniapp(self, name:str, group:str, announcement:str) -> str:
        """
        Creates a new Announcement miniapp with a specific announcement.
        Returns the miniapp ID.
        """
        if not self._active_version:
            self._active_version = await self.get_active_version()

        # Create an empty miniapp    
        endpoint = "miniapps/api/apps"
        payload = {
            "name": name,
            "type": "Announcement.MiniApps",
            "group": group,
            "languages": ["en-US"],
            "sensitivity": "None",
            "version": self._active_version
        }
        resp = await self.post(endpoint, json=payload)
        logger.info(f"Response: {resp}")
        miniapp_id = resp["miniAppId"]

        # Get and update the new miniapp
        miniapp_data = await self.get_miniapp(miniapp_id)
        miniapp_data["model"]["announceList"] = get_announcement_announce_list(announcement)
        await self.update_miniapp(miniapp_id, miniapp_data)
        return miniapp_id 

    async def _update_miniapp_with_kb(self, miniapp_id:str, vector_store_id:str) -> dict:
        """
        Updates a miniapp's pathfinderFallback section with a new vectorStoreId.
        Gets the first reask ID from the Reasks array and uses it as the reaskId.

        Args:
            miniapp_id (str): The ID of the miniapp to update
            vector_store_id (str): The vector store ID to set in pathfinderFallback

        Returns:
            dict: The updated miniapp data
        """
        # Get the current miniapp data
        miniapp_data = await self.get_miniapp(miniapp_id)
        
        # Extract the first reask ID from the Reasks array
        reasks = miniapp_data.get("Reasks")
        first_reask_id = reasks[0].get("md5")
        
        # Update the pathfinderFallback section
        if "pathfinderFallback" not in miniapp_data:
            miniapp_data["pathfinderFallback"] = {}
        
        miniapp_data["pathfinderFallback"].update({
            "enabled": True,
            "locales": {"en-US": {"vectorStoreId": vector_store_id}},
            "bargeIn": {"normal": False},
            "postAction": {"reaskId": first_reask_id}
        })
        
        # Update the miniapp using the existing update method
        return await self.update_miniapp(miniapp_id, miniapp_data)
