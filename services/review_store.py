from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from db import async_session_maker, is_db_configured
from models import AppModel, ReviewModel


def _build_histogram(reviews: list[ReviewModel]) -> dict[int, int]:
    histogram = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in reviews:
        score = int(review.rating or 0)
        if score in histogram:
            histogram[score] += 1
    return histogram


async def fetch_app_data_from_db(app_id: str) -> dict[str, Any] | None:
    if not is_db_configured() or not async_session_maker:
        return None

    async with async_session_maker() as session:
        app = await session.scalar(
            select(AppModel).where(AppModel.google_play_id == app_id)
        )
        if not app:
            return None

        reviews = (
            await session.execute(select(ReviewModel).where(ReviewModel.app_id == app.id))
        ).scalars().all()

        review_payload = [
            {
                "score": int(r.rating or 0),
                "content": r.content or "",
                "at": r.review_date or "",
            }
            for r in reviews
        ]

        low_review_payload = [r for r in review_payload if r["score"] == 1]

        return {
            "app": {
                "title": app.title or "",
                "developer": app.developer or "",
                "developer_id": app.developer_id or "",
                "score": float(app.score or 0.0),
                "ratings": int(app.ratings or 0),
                "installs": app.installs or "0",
                "description": "",
                "genre": app.genre or "",
                "icon": app.icon_url or "",
                "header_image": "",
                "screenshots": [],
            },
            "histogram": _build_histogram(reviews),
            "reviews": review_payload,
            "low_reviews": low_review_payload,
        }


async def upsert_app_reviews(app_data: dict[str, Any], reviews: list[dict[str, Any]], source: str) -> None:
    if not is_db_configured() or not async_session_maker:
        return

    google_play_id = app_data.get("google_play_id") or app_data.get("app_id") or ""
    if not google_play_id:
        return

    async with async_session_maker() as session:
        app = await session.scalar(
            select(AppModel).where(AppModel.google_play_id == google_play_id)
        )
        if not app:
            app = AppModel(google_play_id=google_play_id)
            session.add(app)
            await session.flush()

        app.title = app_data.get("title", app.title or "")
        app.developer = app_data.get("developer", app.developer or "")
        app.developer_id = app_data.get("developer_id", app.developer_id or "")
        app.icon_url = app_data.get("icon", app.icon_url or "")
        app.genre = app_data.get("genre", app.genre or "")
        app.score = float(app_data.get("score") or app.score or 0.0)
        app.ratings = int(app_data.get("ratings") or app.ratings or 0)
        app.installs = app_data.get("installs", app.installs or "0")

        await session.execute(delete(ReviewModel).where(ReviewModel.app_id == app.id))

        for review in reviews:
            session.add(
                ReviewModel(
                    app_id=app.id,
                    rating=int(review.get("score") or 0),
                    content=review.get("content") or "",
                    review_date=str(review.get("at") or ""),
                    source=source,
                )
            )

        await session.commit()
