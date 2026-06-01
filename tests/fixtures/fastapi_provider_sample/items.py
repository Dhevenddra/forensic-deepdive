from fastapi import APIRouter

router = APIRouter(prefix="/items")


@router.post("/")
def create_item():
    return {}


@router.get("/{item_id}")
def get_item(item_id: int):
    return {"id": item_id}
