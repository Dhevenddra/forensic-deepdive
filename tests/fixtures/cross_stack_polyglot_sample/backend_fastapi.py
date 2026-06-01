from fastapi import FastAPI

app = FastAPI()


@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    return {"id": user_id}


@app.post("/api/users")
def create_user(body: dict):
    return body
