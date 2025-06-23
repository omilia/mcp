import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import requests

# Add the src directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from ocp.authentication import Authentication


class TestAuthentication(unittest.TestCase):

    def setUp(self):
        """Set up for the tests."""
        # We patch os.environ to avoid depending on a real .env file
        with patch.dict(
            os.environ,
            {
                "OCP_HOST": "http://fake-host.com",
                "OCP_USERNAME": "user",
                "OCP_PASSWORD": "password",
            },
        ):
            self.auth = Authentication()

    @patch("time.time")
    @patch("requests.post")
    def test_get_token_success(self, mock_post, mock_time):
        """Test successful token acquisition."""
        mock_time.return_value = 1000.0
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "fake_access_token",
            "refresh_token": "fake_refresh_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token = self.auth.get_token()

        self.assertEqual(token, "fake_access_token")
        self.assertEqual(self.auth._access_token, "fake_access_token")
        self.assertEqual(self.auth._refresh_token, "fake_refresh_token")
        self.assertEqual(self.auth._token_expiry, 1000.0 + 3600)
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_get_token_failure(self, mock_post):
        """Test failed token acquisition."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_post.return_value = mock_response

        token = self.auth.get_token()

        self.assertIsNone(token)
        self.assertIsNone(self.auth._access_token)
        mock_post.assert_called_once()

    @patch("time.time")
    @patch("requests.post")
    def test_refresh_token_success(self, mock_post, mock_time):
        """Test successful token refresh."""
        mock_time.return_value = 5000.0
        self.auth._refresh_token = "old_refresh_token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        self.auth.refresh_token()

        self.assertEqual(self.auth._access_token, "new_access_token")
        self.assertEqual(self.auth._refresh_token, "new_refresh_token")
        self.assertEqual(self.auth._token_expiry, 5000.0 + 3600)
        mock_post.assert_called_once()

    @patch("requests.get")
    def test_check_token_valid(self, mock_get):
        """Test checking a valid token."""
        self.auth._access_token = "valid_token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_valid = self.auth.check_token()

        self.assertTrue(is_valid)
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_check_token_invalid(self, mock_get):
        """Test checking an invalid token."""
        self.auth._access_token = "invalid_token"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        is_valid = self.auth.check_token()

        self.assertFalse(is_valid)
        mock_get.assert_called_once()

    @patch("requests.post")
    def test_revoke_token_success(self, mock_post):
        """Test successful token revocation."""
        self.auth._refresh_token = "some_refresh_token"
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        self.auth.revoke_token()

        mock_post.assert_called_once()
        # You could also check the print output if you capture it

    @patch("requests.post")
    def test_context_manager(self, mock_post):
        """Test the class as a context manager."""
        # Mock get_token response
        get_token_response = MagicMock()
        get_token_response.status_code = 200
        get_token_response.json.return_value = {
            "access_token": "ctx_access_token",
            "refresh_token": "ctx_refresh_token",
            "expires_in": 3600,
        }

        # Mock revoke_token response
        revoke_token_response = MagicMock()
        revoke_token_response.status_code = 204

        mock_post.side_effect = [get_token_response, revoke_token_response]

        with patch(
            "os.getenv",
            side_effect=["http://fake-host.com", "ctx_user", "ctx_password"],
        ):
            with Authentication() as auth:
                self.assertEqual(auth._access_token, "ctx_access_token")

        # Check that get_token and revoke_token were called
        self.assertEqual(mock_post.call_count, 2)

    @patch("requests.post")
    @patch("time.time")
    def test_get_token_reuse_valid(self, mock_time, mock_post):
        """Test that get_token reuses a valid existing token."""
        # Set up initial token
        self.auth._access_token = "existing_token"
        self.auth._token_expiry = 3600
        mock_time.return_value = 1000  # Current time

        # Get token should return existing one
        token = self.auth.get_token()

        self.assertEqual(token, "existing_token")
        mock_post.assert_not_called()  # No new token request made

    @patch("requests.post")
    @patch("time.time")
    def test_get_token_refresh_expired(self, mock_time, mock_post):
        """Test that get_token refreshes an expired token."""
        # Set up expired token
        self.auth._access_token = "expired_token"
        self.auth._refresh_token = "refresh_token"
        self.auth._token_expiry = 1000
        mock_time.return_value = 2000  # Time after expiry

        # Mock token response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token = self.auth.get_token()

        self.assertEqual(token, "new_token")
        self.assertEqual(self.auth._refresh_token, "new_refresh")
        self.assertEqual(self.auth._token_expiry, 2000 + 3600)
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
