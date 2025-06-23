import requests
from .authentication import Authentication


class BaseClient:
    """
    A base client for making authenticated requests to the OCP API.
    It handles token acquisition and adds the Authorization header to each request.
    """

    def __init__(self):
        self.auth = Authentication()
        self.base_url = self.auth.host

    def _get_auth_headers(self):
        """
        Ensures a valid token is available and returns the required headers.
        """
        token = self.auth.get_token()
        if not token:
            raise Exception("Failed to acquire authentication token.")
        return {"Authorization": f"Bearer {token}"}

    def get(self, endpoint, **kwargs):
        """
        Performs a GET request to a specified endpoint with authentication.
        """
        headers = self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint, **kwargs):
        """
        Performs a POST request to a specified endpoint with authentication.
        """
        headers = self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint, **kwargs):
        """
        Performs a PUT request to a specified endpoint with authentication.
        """
        headers = self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = requests.put(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint, **kwargs):
        """
        Performs a DELETE request to a specified endpoint with authentication.
        """
        headers = self._get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        url = f"{self.base_url}/{endpoint}"
        response = requests.delete(url, headers=headers, **kwargs)
        response.raise_for_status()
        # Delete requests often return 204 No Content, which has no JSON body
        if response.status_code != 204:
            return response.json()
        return None
