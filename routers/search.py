from fastapi import APIRouter, Query

from schemas import ApiResponse, SearchResponse
from services import play_scraper

router = APIRouter()


@router.get("/search", response_model=ApiResponse[SearchResponse])
async def search_apps(q: str = Query(..., min_length=0)) -> ApiResponse[SearchResponse]:
    if not q.strip():
        return ApiResponse(success=True, data=SearchResponse(results=[]))

    results = await play_scraper.fetch_search_results(q)
    results = [r for r in results if r.get("google_play_id")]
    return ApiResponse(success=True, data=SearchResponse(results=results))
