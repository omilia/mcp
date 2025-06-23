import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()


class Authentication:
    def __init__(self):
        self.host = os.getenv("OCP_HOST")
        self.username = os.getenv("OCP_USERNAME")
        self.password = os.getenv("OCP_PASSWORD")

        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None

    def __enter__(self):
        self.get_token()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.revoke_token()

    def get_token(self):
        """
        Gets the access token. Returns existing token if valid, refreshes if expired,
        or generates new one if none exists.
        """
        current_time = time.time()

        # Return existing token if valid
        if (
            self._access_token is not None
            and self._token_expiry is not None
            and current_time < self._token_expiry
        ):
            return self._access_token

        # Refresh token if we have one
        if self._refresh_token is not None:
            try:
                self.refresh_token()
                return self._access_token
            except requests.exceptions.HTTPError:
                # If refresh fails, fall through to getting new token
                pass

        # Get new token
        url = f"{self.host}/auth/realms/master/protocol/openid-connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": "ocp",
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }

        response = requests.post(url, headers=headers, data=data)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(response.text)
            return None

        token = response.json()
        self._access_token = token["access_token"]
        if "refresh_token" in token:
            self._refresh_token = token["refresh_token"]
        self._token_expiry = time.time() + token["expires_in"]
        return self._access_token

    def refresh_token(self):
        """
        Refreshes the access token.
        """
        url = f"{self.host}/auth/realms/master/protocol/openid-connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": "ocp",
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        token = response.json()
        self._access_token = token["access_token"]
        if "refresh_token" in token:
            self._refresh_token = token["refresh_token"]
        self._token_expiry = time.time() + token["expires_in"]

    def revoke_token(self):
        """
        Revokes the refresh token.
        """
        url = f"{self.host}/auth/realms/master/protocol/openid-connect/logout"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"client_id": "ocp", "refresh_token": self._refresh_token}
        response = requests.post(url, headers=headers, data=data)
        try:
            response.raise_for_status()
            print("Token successfully revoked")
        except requests.exceptions.HTTPError as e:
            print(f"Failed to revoke token: {e}")
            print(response.text)

    def check_token(self):
        url = f"{self.host}/miniapps/api/apps?pageSize=1"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        response = requests.get(url, headers=headers)

        # A 200 OK response means the token is active and valid.
        is_valid = response.status_code == 200
        if is_valid:
            print("Token is valid. UserInfo response:")
            print(response.json())
        else:
            print(
                f"Token validation failed. Status: {response.status_code}, Body: {response.text}"
            )

        return is_valid
