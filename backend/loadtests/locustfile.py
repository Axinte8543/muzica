import os
from typing import Any

from locust import HttpUser, task, between


DEFAULT_USERNAME = os.getenv("LOADTEST_USERNAME", "e2e_alice")
DEFAULT_PASSWORD = os.getenv("LOADTEST_PASSWORD", "E2E_Test_123!")


class MusicAppUser(HttpUser):
    wait_time = between(1, 3)
    host = os.getenv("LOADTEST_HOST", "http://127.0.0.1:8000")

    def on_start(self) -> None:
        self.auth_headers: dict[str, str] = {}
        self.conversation_id: int | None = None
        self._login()
        self._seed_conversation_context()

    def _login(self) -> None:
        response = self.client.post(
            "/api/auth/login/",
            json={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
            name="/api/auth/login/",
        )
        response.raise_for_status()
        token = response.json().get("access")
        if not token:
            raise RuntimeError("Login response did not include an access token")
        self.auth_headers = {"Authorization": f"Bearer {token}"}

    def _seed_conversation_context(self) -> None:
        response = self.client.get(
            "/api/chat/conversations/",
            headers=self.auth_headers,
            name="/api/chat/conversations/",
        )
        if response.status_code != 200:
            return

        payload: Any = response.json()
        conversations = payload if isinstance(payload, list) else payload.get("results", payload)
        if conversations:
            first = conversations[0]
            self.conversation_id = first.get("id")

    @task(4)
    def read_home(self) -> None:
        self.client.get(
            "/api/home/",
            headers=self.auth_headers,
            name="/api/home/",
        )

    @task(4)
    def read_recommendations(self) -> None:
        self.client.get(
            "/api/recommendations/",
            headers=self.auth_headers,
            name="/api/recommendations/",
        )

    @task(2)
    def read_conversations(self) -> None:
        self.client.get(
            "/api/chat/conversations/",
            headers=self.auth_headers,
            name="/api/chat/conversations/",
        )

    @task(2)
    def read_messages(self) -> None:
        self.client.get(
            "/api/chat/messages/?limit=10",
            headers=self.auth_headers,
            name="/api/chat/messages/?limit=:limit",
        )

    @task(1)
    def read_search(self) -> None:
        self.client.get(
            "/api/users/search/?q=alina",
            headers=self.auth_headers,
            name="/api/users/search/?q=:query",
        )
