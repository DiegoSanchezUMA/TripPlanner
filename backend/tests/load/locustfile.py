"""Escenario de carga mínimo. Amplíalo con los flujos del catálogo C-1."""

import os

from locust import HttpUser, between, task


class TravellerUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        token = os.environ.get("LOAD_TEST_TOKEN")
        if token:
            self.client.headers["Authorization"] = f"Bearer {token}"

    @task(5)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")
