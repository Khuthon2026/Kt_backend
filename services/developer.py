import asyncio
from datetime import datetime, timedelta
from typing import Any

try:
    from google_play_scraper import developer as gps_developer
except ImportError:
    gps_developer = None


async def fetch_developer_apps(dev_id: str, current_genre: str) -> dict[str, Any] | None:
    if not dev_id:
        return None

    if gps_developer is None:
        return None

    loop = asyncio.get_running_loop()
    try:
        apps = await loop.run_in_executor(
            None,
            lambda: gps_developer(dev_id, lang="ko", country="kr"),
        )
    except Exception:
        return None

    apps = apps or []
    total_count = len(apps)
    if total_count == 0:
        return {
            "developer_id": dev_id,
            "total_count": 0,
            "recent_3months_count": 0,
            "category_overlap": 0.0,
            "pattern_score": 0,
            "apps": [],
        }

    recent_3months_count = _count_recent_apps(apps, days=90)
    category_overlap = _calc_category_overlap(apps, current_genre)
    average_score = _calc_average_score(apps)
    pattern_score = _calc_pattern_score(
        total_count=total_count,
        recent_3months_count=recent_3months_count,
        category_overlap=category_overlap,
        average_score=average_score,
    )

    apps_payload = _build_apps_payload(apps)

    return {
        "developer_id": dev_id,
        "total_count": total_count,
        "recent_3months_count": recent_3months_count,
        "category_overlap": round(category_overlap, 3),
        "pattern_score": pattern_score,
        "apps": apps_payload,
    }


def _count_recent_apps(apps: list[dict[str, Any]], days: int) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    count = 0
    for app in apps:
        released = _parse_released(app.get("released"))
        if released and released >= cutoff:
            count += 1
    return count


def _calc_category_overlap(apps: list[dict[str, Any]], current_genre: str) -> float:
    if not apps:
        return 0.0
    match_count = sum(1 for app in apps if (app.get("genre") or "") == current_genre)
    return match_count / len(apps)


def _calc_average_score(apps: list[dict[str, Any]]) -> float:
    scores = [float(app.get("score") or 0.0) for app in apps]
    return sum(scores) / len(scores) if scores else 0.0


def _calc_pattern_score(
    total_count: int,
    recent_3months_count: int,
    category_overlap: float,
    average_score: float,
) -> int:
    score = 0
    if total_count >= 5:
        score += 1
    if recent_3months_count >= 2:
        score += 1
    if category_overlap >= 0.7:
        score += 1
    if average_score < 3.5:
        score += 1
    if total_count > 0 and recent_3months_count >= total_count * 0.5:
        score += 1
    return score


def _build_apps_payload(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for app in apps:
        released_at = _format_released_at(app.get("released"))
        items.append(
            {
                "name": app.get("title", ""),
                "google_play_id": app.get("appId", ""),
                "genre": app.get("genre", ""),
                "released_at": released_at,
            }
        )

    items.sort(
        key=lambda x: (x.get("released_at", "") != "", x.get("released_at", "")),
        reverse=True,
    )
    return items[:20]


def _parse_released(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value

    raw = str(value).strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _format_released_at(value: Any) -> str:
    released = _parse_released(value)
    if not released:
        return ""
    return released.strftime("%Y-%m")
