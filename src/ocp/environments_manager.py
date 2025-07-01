from .base import BaseClient


class EnvironmentsManagerClient(BaseClient):
    def get_variable_collections(self, search_term: str | None = None) -> dict:
        """Get a list of all variable collections."""
        endpoint = "envs-manager/api/v1/variables-collections"
        params = {"searchTerm": search_term}
        return self.get(endpoint, params=params)
    
    def get_collection_variables(self, collection_id: str) -> dict:
        """Get a list of all variables in a collection."""
        endpoint = f"envs-manager/api/v1/variables-collections/{collection_id}"
        return self.get(endpoint)