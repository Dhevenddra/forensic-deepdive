import httpx
import requests


def load_user(user_id):
    return requests.get(f"/api/users/{user_id}")


def list_users():
    return requests.get("/api/users")


def add_user(body):
    return requests.post("/api/users", json=body)


def remove_user(user_id):
    return requests.request("DELETE", f"/api/users/{user_id}")


class ApiClient:
    def __init__(self):
        self.client = httpx.Client()

    def fetch_things(self):
        client = httpx.Client()
        return client.get("/api/things")

    def get_health(self):
        return requests.get("/health")


def lookup(d, key):
    # must NOT be read as an HTTP call (dict.get on an un-allowlisted receiver)
    return d.get(key)
