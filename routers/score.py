from fastapi import APIRouter, HTTPException
from schemas import ApiResponse, AppAnalyzeRequest, AnalyzeResponse, AppInfo
from services import play_scraper, scorer

router = APIRouter(tags=["Score"])


@router.post("/analyze", response_model=ApiResponse[AnalyzeResponse])
async def analyze_app(request: AppAnalyzeRequest):
    app_id = play_scraper.extract_app_id(request.app_id)

    try:
        app_data = await play_scraper.fetch_app_info(app_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "APP_NOT_FOUND", "message": f"앱을 찾을 수 없습니다: {app_id}"},
        )

    score_breakdown = scorer.calculate_score(app_data)
    suspicious_keywords = scorer.find_suspicious_keywords(app_data["description"])
    verdict = scorer.get_verdict(score_breakdown.overall)

    return ApiResponse(
        success=True,
        data=AnalyzeResponse(
            app_id=app_id,
            app_info=AppInfo(
                title=app_data["title"],
                developer=app_data["developer"],
                score=app_data["score"],
                ratings=app_data["ratings"],
                installs=app_data["installs"],
                description=app_data["description"],
                icon=app_data["icon"],
                genre=app_data["genre"],
            ),
            score_breakdown=score_breakdown,
            suspicious_keywords=suspicious_keywords,
            verdict=verdict,
        ),
    )
