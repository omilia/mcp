from .base import BaseClient


class IntegrationsClient(BaseClient):
    def search_numbers(self, search_term: str | None = None, page_size: int = 100) -> dict:
        """Search numbers with optional search term.
        
        Args:
            search_term (str, optional): Search term to filter numbers. Case insensitive.
            
        Returns:
            dict: The numbers matching the search criteria
        """
        endpoint = "integrations/api/numbers"
        params = {"pageSize": page_size, "searchTerm": search_term}
        return self.get(endpoint, params=params)