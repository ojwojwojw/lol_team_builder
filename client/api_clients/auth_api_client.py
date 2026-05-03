from api_clients.base_api_client import BaseApiClient


class AuthApiClient(BaseApiClient):
    """Auth-only API client."""

    def login(self, username, password):
        return self._post(
            "/auth/login",
            {"username": username, "password": password},
            use_auth=False,
        )

    def bootstrap_admin(self, username, password):
        return self._post(
            "/auth/bootstrap-admin",
            {"username": username, "password": password},
            use_auth=False,
        )

    def get_setup_status(self):
        return self._get("/auth/setup-status", use_auth=False)

    def get_me(self):
        return self._get("/auth/me")

    def list_users(self):
        return self._get("/auth/users")

    def create_user(self, username, password):
        return self._post(
            "/auth/users",
            {"username": username, "password": password},
        )
