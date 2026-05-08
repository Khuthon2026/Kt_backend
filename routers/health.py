from fastapi import APIRouter
from schemas import ApiResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return ApiResponse(success=True, data={"status": "ok"})
