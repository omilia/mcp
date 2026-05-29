from .base import BaseClient


class PathfinderClient(BaseClient):
    """
    A client for interacting with the Pathfinder service API.
    Provides methods for managing pathfinder operations and resources.
    """

    async def create_faq(self, project_id, urls, follow_links_one_level_down=False):
        """
        Creates a FAQ for a specific project using the provided URLs.

        Args:
            project_id (str): The ID of the project to create FAQ for
            urls (str or list): URL(s) to process for FAQ creation. Can be a single URL string 
                               or a list of URLs that will be joined with newlines
            follow_links_one_level_down (bool): Whether to follow links one level down. 
                                              Defaults to False

        Returns:
            dict: The response from the FAQ creation API
        """
        endpoint = f"pathfinder/api/v1/projects/{project_id}/faq"
        
        # Handle both single URL string and list of URLs
        if isinstance(urls, list):
            urls_value = '\n'.join(urls)
        else:
            urls_value = str(urls)

        # Prepare multipart form data using files parameter
        files = {
            'urls': (None, urls_value),
            'follow_links_one_level_down': (None, str(follow_links_one_level_down).lower())
        }
        
        return await self.post(endpoint, files=files)
    
    async def list_projects(self, search_term=None):
        """
        Lists pathfinder projects with optional search filtering.
        
        Args:
            search_term (str, optional): Search term to filter projects
            
        Returns:
            dict: The response containing the list of projects
        """
        endpoint = "pathfinder/api/v1/projects"
        
        # Add search_term as query parameter if provided
        params = {}
        if search_term:
            params['search_term'] = search_term
        
        return await self.get(endpoint, params=params)


    async def create_project(self, name: str, group: str, language: str, domain: str, mode: str):
        """
        Creates a new pathfinder project.
        
        Args:
            name: The name of the project
            group: The group of the project
            language: The language of the project example: en-US, en-GB.
            domain: The domain of the project example: 'energy', 'car retail'.
            mode: The mode of the project

        Returns:
            dict: The response containing the new project
        """
        endpoint = "pathfinder/api/v1/projects"
        
        payload = {"name": name, "group": group, "language": language, "domain": domain, "mode": mode}

        
        return await self.post(endpoint, json=payload)
    
    async def get_project(self, project_id: str) -> dict:
        """
        Gets a specific pathfinder project by its ID.
        """
        endpoint = f"pathfinder/api/v1/projects/{project_id}"
        return await self.get(endpoint)
    
    async def deploy_faq(self, project_id):
        """
        Deploys FAQ vector stores for a specific project.
        
        Args:
            project_id (str): The ID of the project to deploy FAQ for
            
        Returns:
            dict: The response from the FAQ deployment API
        """
        endpoint = "pathfinder/api/v1/faq/vector_stores/deploy"
        payload = {"project_id": project_id}
        response = await self.post(endpoint, json=payload)
        index_name = response.get("index_name")
        return f"Created new knowledge base index: {index_name}"

    async def list_faqs(self) -> dict:
        """
        Lists FAQ vector stores.
        """
        endpoint = "pathfinder/api/v1/faq/vector_stores"
        return await self.get(endpoint)


