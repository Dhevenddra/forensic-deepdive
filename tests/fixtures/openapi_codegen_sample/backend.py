"""FastAPI backend for the OpenAPI codegen-shortcut fixture (DEC-048).

Only `/api/items/{item_id}` has an in-code handler. `/api/orphan/{orphan_id}`
is declared in `openapi.json` but has NO handler here — it must surface as a
spec-only (documented-but-unlocated) Endpoint.
"""

from fastapi import FastAPI

app = FastAPI()


@app.get("/api/items/{item_id}")
def get_item(item_id: str):
    return {"id": item_id}
