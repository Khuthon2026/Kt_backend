from fastapi import APIRouter, HTTPException
from schemas import ApiResponse, AppAnalyzeRequest, AnalyzeResponse, AppInfo, TopReviews, KeywordItem
from services import play_scraper, scorer

router = APIRouter(tags=["Score"])


@router.post("/analyze", response_model=ApiResponse[AnalyzeResponse])
async def analyze_app(request: AppAnalyzeRequest):
    app_id = play_scraper.extract_app_id(request.app_id)

    try:
        scraped = await play_scraper.fetch_app_data(app_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "SCRAPING_FAILED", "message": "스크래핑 중 오류가 발생했습니다"},
        ) from exc

    app_info_data = scraped["app"]
    score_breakdown = scorer.calculate_score(
        app_info=app_info_data,
        histogram=scraped.get("histogram") or {},
        reviews=scraped.get("reviews") or [],
    )
    verdict = scorer.get_verdict(score_breakdown.overall)
    keywords = scorer.extract_keywords(scraped.get("reviews") or [])
    top_reviews = scorer.select_top_reviews(scraped.get("reviews") or [])

    return ApiResponse(
        success=True,
        data=AnalyzeResponse(
            app_id=app_id,
            app_info=AppInfo(
                title=app_info_data.get("title", ""),
                developer=app_info_data.get("developer", ""),
                icon=app_info_data.get("icon", ""),
                genre=app_info_data.get("genre", ""),
                score=app_info_data.get("score") or 0.0,
                ratings=app_info_data.get("ratings") or 0,
                installs=app_info_data.get("installs") or "0",
            ),
            score_breakdown=score_breakdown,
            verdict=verdict,
            keywords=[KeywordItem(**item) for item in keywords],
            top_reviews=TopReviews(**top_reviews),
        ),
    )
