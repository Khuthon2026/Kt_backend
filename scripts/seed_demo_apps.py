import asyncio

from db import init_db
from services import play_scraper
from services.review_store import upsert_app_reviews


DEMO_QUERIES = [
    "카카오톡",
    "Hero Wars: Alliance",
    "데몬헌터 머나먼",
    "배달의 민족",
]


async def _resolve_app_id(query: str) -> str | None:
    if "." in query:
        return query
    results = await play_scraper.fetch_search_results(query)
    if not results:
        return None
    return results[0].get("google_play_id")


async def seed_demo_apps() -> None:
    await init_db()
    for query in DEMO_QUERIES:
        app_id = await _resolve_app_id(query)
        if not app_id:
            print(f"[skip] app id not found for: {query}")
            continue

        scraped = await play_scraper.fetch_app_data(app_id)
        app_info = scraped.get("app") or {}
        app_info["google_play_id"] = app_id
        reviews = scraped.get("reviews") or []

        await upsert_app_reviews(app_info, reviews, source="seed")
        print(f"[ok] seeded: {app_id} ({query}) with {len(reviews)} reviews")


if __name__ == "__main__":
    asyncio.run(seed_demo_apps())
