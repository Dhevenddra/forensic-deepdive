import requests


def load_item(item_id):
    return requests.get(f"/svc/items/{item_id}")


def push_item(body):
    return requests.post("/svc/items", json=body)
