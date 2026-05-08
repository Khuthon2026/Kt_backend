import re
import asyncio
from google_play_scraper import app as gps_app


def extract_app_id(input_str: str) -> str:
    """Play Store URL 또는 패키지명에서 app_id 추출"""
    match = re.search(r'id=([a-zA-Z0-9._]+)', input_str)
    if match:
        return match.group(1)
    return input_str.strip()


async def fetch_app_info(app_id: str) -> dict:
    """google-play-scraper로 앱 정보 조회 (동기 라이브러리를 async로 래핑)"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: gps_app(app_id, lang="ko", country="kr"),
    )
    return {
        "title": result.get("title", ""),
        "developer": result.get("developer", ""),
        "score": result.get("score") or 0.0,
        "ratings": result.get("ratings") or 0,
        "installs": result.get("installs", "0"),
        "description": result.get("description", ""),
        "permissions": result.get("permissions") or [],
        "genre": result.get("genre", ""),
        "free": result.get("free", True),
        "icon": result.get("icon", ""),
        "screenshots": result.get("screenshots") or [],
        "video": result.get("video"),  # 프로모션 영상 URL (있으면)
    }
