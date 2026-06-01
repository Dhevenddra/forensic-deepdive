from fastapi import FastAPI

from items import router

app = FastAPI()


@app.get("/users/{user_id}")
def read_user(user_id: int):
    return {"id": user_id}


@app.get("/health")
def health():
    return "ok"


app.include_router(router, prefix="/api")
