import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import requests

# Add the src directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from ocp.base import BaseClient


class TestBaseClient(unittest.TestCase):

    @patch("ocp.base.Authentication")
    def setUp(self, MockAuthentication):
        """Set up for the tests."""
        # Configure the mock for Authentication
        self.mock_auth_instance = MockAuthentication.return_value
        self.mock_auth_instance.host = "http://fake-host.com"
        self.mock_auth_instance.get_token.return_value = "fake_token"
        
        # Instantiate the client
        self.client = BaseClient()

    @patch("requests.get")
    def test_get_success(self, mock_get):
        """Test a successful GET request."""
        # Configure the mock for requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "success"}
        mock_get.return_value = mock_response

        # Make the request
        endpoint = "test/endpoint"
        response_data = self.client.get(endpoint, params={"a": 1})

        # Assertions
        self.assertEqual(response_data, {"data": "success"})
        self.mock_auth_instance.get_token.assert_called_once()
        expected_url = f"{self.client.base_url}/{endpoint}"
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_get.assert_called_once_with(
            expected_url, headers=expected_headers, params={"a": 1}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("requests.post")
    def test_post_success(self, mock_post):
        """Test a successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "created"}
        mock_post.return_value = mock_response

        endpoint = "test/endpoint"
        payload = {"key": "value"}
        response_data = self.client.post(endpoint, json=payload)

        self.assertEqual(response_data, {"message": "created"})
        self.mock_auth_instance.get_token.assert_called_once()
        expected_url = f"{self.client.base_url}/{endpoint}"
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_post.assert_called_once_with(
            expected_url, headers=expected_headers, json=payload
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("requests.put")
    def test_put_success(self, mock_put):
        """Test a successful PUT request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "updated"}
        mock_put.return_value = mock_response

        endpoint = "test/endpoint/1"
        payload = {"key": "new_value"}
        response_data = self.client.put(endpoint, json=payload)

        self.assertEqual(response_data, {"message": "updated"})
        self.mock_auth_instance.get_token.assert_called_once()
        expected_url = f"{self.client.base_url}/{endpoint}"
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_put.assert_called_once_with(
            expected_url, headers=expected_headers, json=payload
        )
        mock_response.raise_for_status.assert_called_once()
        
    @patch("requests.delete")
    def test_delete_success_with_content(self, mock_delete):
        """Test a successful DELETE request that returns content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "deleted"}
        mock_delete.return_value = mock_response
        
        endpoint = "test/endpoint/1"
        response_data = self.client.delete(endpoint)

        self.assertEqual(response_data, {"message": "deleted"})
        self.mock_auth_instance.get_token.assert_called_once()
        expected_url = f"{self.client.base_url}/{endpoint}"
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_delete.assert_called_once_with(
            expected_url, headers=expected_headers
        )
        mock_response.raise_for_status.assert_called_once()
        
    @patch("requests.delete")
    def test_delete_success_no_content(self, mock_delete):
        """Test a successful DELETE request with 204 No Content."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        endpoint = "test/endpoint/1"
        response_data = self.client.delete(endpoint)

        self.assertIsNone(response_data)
        self.mock_auth_instance.get_token.assert_called_once()
        expected_url = f"{self.client.base_url}/{endpoint}"
        expected_headers = {"Authorization": "Bearer fake_token"}
        mock_delete.assert_called_once_with(
            expected_url, headers=expected_headers
        )
        mock_response.raise_for_status.assert_called_once()

    def test_get_auth_headers_no_token(self):
        """Test that an exception is raised if no token is acquired."""
        self.mock_auth_instance.get_token.return_value = None
        
        with self.assertRaisesRegex(Exception, "Failed to acquire authentication token."):
            self.client.get("test")

    @patch("requests.get")
    def test_request_failure(self, mock_get):
        """Test handling of a failed request."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.get("invalid/endpoint")

    @patch('requests.get')
    def test_get_with_custom_headers(self, mock_get):
        """Test GET request with additional custom headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        custom_headers = {'X-Custom-Header': 'CustomValue'}
        self.client.get('test/endpoint', headers=custom_headers)

        expected_headers = {
            "Authorization": "Bearer fake_token",
            'X-Custom-Header': 'CustomValue'
        }
        
        mock_get.assert_called_with(
            f"{self.client.base_url}/test/endpoint",
            headers=expected_headers
        )

if __name__ == "__main__":
    unittest.main() 