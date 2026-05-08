import re
import asyncio
from typing import Any

from fastapi import HTTPException
from google_play_scraper import app as gps_app
from google_play_scraper import reviews as gps_reviews
from google_play_scraper import Sort


def extract_app_id(input_str: str) -> str:
    """Play Store URL 또는 패키지명에서 app_id 추출"""
    match = re.search(r'id=([a-zA-Z0-9._]+)', input_str)
    if match:
        return match.group(1)
    return input_str.strip()


async def fetch_app_data(app_id: str) -> dict[str, Any]:
    """google-play-scraper로 앱 정보/리뷰 조회 (동기 라이브러리를 async로 래핑)."""
    loop = asyncio.get_running_loop()

    try:
        app_result = await loop.run_in_executor(
            None,
            lambda: gps_app(app_id, lang="ko", country="kr"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "APP_NOT_FOUND", "message": f"앱을 찾을 수 없습니다: {app_id}"},
        ) from exc

    try:
        review_result, _ = await loop.run_in_executor(
            None,
            lambda: gps_reviews(
                app_id,
                lang="ko",
                country="kr",
                sort=Sort.NEWEST,
                count=200,
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "SCRAPING_FAILED", "message": "스크래핑 중 오류가 발생했습니다"},
        ) from exc

    return {
        "app": {
            "title": app_result.get("title", ""),
            "developer": app_result.get("developer", ""),
            "score": app_result.get("score") or 0.0,
            "ratings": app_result.get("ratings") or 0,
            "installs": app_result.get("installs", "0"),
            "description": app_result.get("description", ""),
            "genre": app_result.get("genre", ""),
            "icon": app_result.get("icon", ""),
        },
        "histogram": app_result.get("histogram") or {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "reviews": review_result or [],
    }
