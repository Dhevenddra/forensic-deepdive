from flask import Flask

app = Flask(__name__)


@app.get("/svc/items/<int:item_id>")
def fetch_item(item_id):
    return {"id": item_id}


@app.post("/svc/items")
def add_item():
    return {}
