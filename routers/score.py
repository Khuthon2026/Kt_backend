import asyncio

from fastapi import APIRouter, HTTPException
from schemas import ApiResponse, AppAnalyzeRequest, AnalyzeResponse, AppInfo, TopReviews, KeywordItem, DeveloperApps
from services import play_scraper, scorer, developer, review_store

router = APIRouter(tags=["Score"])


@router.post("/analyze", response_model=ApiResponse[AnalyzeResponse])
async def analyze_app(request: AppAnalyzeRequest):
    app_id = play_scraper.extract_app_id(request.app_id)

    try:
        scraped = await review_store.fetch_app_data_from_db(app_id)
        if not scraped:
            scraped = await play_scraper.fetch_app_data(app_id)
            fresh_app_info = {**scraped["app"], "google_play_id": app_id}
            await review_store.upsert_app_reviews(fresh_app_info, scraped.get("reviews") or [], "scraped")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "SCRAPING_FAILED", "message": "스크래핑 중 오류가 발생했습니다"},
        ) from exc

    app_info_data = scraped["app"]
    app_info_data["google_play_id"] = app_id
    reviews = scraped.get("reviews") or []
    low_reviews = scraped.get("low_reviews") or []
    developer_apps = await developer.fetch_developer_apps(
        dev_id=app_info_data.get("developer_id", ""),
        current_genre=app_info_data.get("genre", ""),
    )
    score_breakdown = await scorer.calculate_score(
        app_info=app_info_data,
        histogram=scraped.get("histogram") or {},
        reviews=reviews,
        pattern_score=developer_apps["pattern_score"] if developer_apps else None,
        low_reviews=low_reviews,
    )
    verdict = scorer.get_verdict(score_breakdown.overall)
    keywords = scorer.extract_keywords(reviews)
    top_reviews = scorer.select_top_reviews(reviews)

    return ApiResponse(
        success=True,
        data=AnalyzeResponse(
            app_id=app_id,
            app_info=AppInfo(
                title=app_info_data.get("title", ""),
                developer=app_info_data.get("developer", ""),
                developer_id=app_info_data.get("developer_id", ""),
                icon=app_info_data.get("icon", ""),
                genre=app_info_data.get("genre", ""),
                score=round(app_info_data.get("score") or 0.0, 1),
                ratings=app_info_data.get("ratings") or 0,
                installs=app_info_data.get("installs") or "0",
            ),
            score_breakdown=score_breakdown,
            verdict=verdict,
            keywords=[KeywordItem(**item) for item in keywords],
            top_reviews=TopReviews(**top_reviews),
            developer_apps=DeveloperApps(**developer_apps) if developer_apps else None,
        ),
    )
