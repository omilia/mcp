from .base import BaseClient


class OrchestratorClient(BaseClient):

    def search_apps(self, search_term: str | None = None, page_size: int = 30) -> dict:
        """Search Orchestrator apps with optional search term.
        
        Args:
            search_term (str, optional): Search term to filter apps. Case insensitive.
            
        Returns:
            dict: The apps matching the search criteria
        """
        endpoint = "orchestrator/api/apps/pagination/"
        params = {"limit": page_size}
        if search_term:
            params['search_term'] = search_term
            
        return self.get(endpoint, params=params)

    def get_canvas(self, canvas_id: str) -> dict:
        """Get a canvas by ID.
        
        Args:
            canvas_id: The ID of the canvas to get
        """
        endpoint = f"orchestrator/api/canvases/{canvas_id}/"
        return self.get(endpoint)