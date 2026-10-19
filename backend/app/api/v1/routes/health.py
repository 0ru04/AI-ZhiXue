from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health():
    return {"code": 0, "message": "ok", "data": {"status": "ok"}}
