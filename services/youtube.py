import os
import re
from typing import Optional

import httpx

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def fetch_ad_metadata(ad_url: str) -> Optional[dict]:
    video_id = extract_video_id(ad_url)
    if not video_id:
        return None
    if not YOUTUBE_API_KEY:
        return {"video_id": video_id, "title": "", "description": "", "tags": [], "channel": ""}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"id": video_id, "part": "snippet", "key": YOUTUBE_API_KEY},
        )
        data = resp.json()

    items = data.get("items", [])
    if not items:
        return None

    snippet = items[0]["snippet"]
    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags") or [],
        "channel": snippet.get("channelTitle", ""),
    }
