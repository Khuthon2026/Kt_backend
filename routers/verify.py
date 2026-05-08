import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

import job_store
from schemas import (
    VerifyRequest,
    VerifyCreateResponse,
    VerifyStatusResponse,
    VerifyResultResponse,
)
from services import play_scraper, scorer, developer
from services.scorer import NEGATIVE_KEYWORDS, extract_keywords, select_top_reviews

router = APIRouter(tags=["verify"])


async def run_analysis(job_id: str, google_play_id: str) -> None:
    try:
        job_store.update_job(job_id, status="processing", progress=10, current_step="store_fetch")
        scraped = await play_scraper.fetch_app_data(google_play_id)

        job_store.update_job(job_id, progress=40, current_step="review_crawl")
        app_info_data: dict[str, Any] = scraped["app"]
        reviews: list[dict[str, Any]] = scraped.get("reviews") or []
        histogram: dict[int, int] = scraped.get("histogram") or {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        job_store.update_job(job_id, progress=70, current_step="score_calc")
        score_breakdown = await scorer.calculate_score(
            app_info=app_info_data,
            histogram=histogram,
            reviews=reviews,
        )

        job_store.update_job(job_id, progress=85, current_step="developer_fetch")
        dev_data = await developer.fetch_developer_apps(
            dev_id=app_info_data.get("developer_id", ""),
            current_genre=app_info_data.get("genre", ""),
        )

        neg_hits = sum(
            1 for r in reviews
            if any(kw in (r.get("content") or "") for kw in NEGATIVE_KEYWORDS)
        )
        negative_ratio = round(neg_hits / len(reviews), 3) if reviews else 0.0

        total_hist = sum(histogram.values()) or 1
        polarization_index = round(
            ((histogram.get(1) or 0) + (histogram.get(5) or 0)) / total_hist, 3
        )

        all_keywords = extract_keywords(reviews)
        trust_keywords: dict[str, int] = {
            k["word"]: k["count"] for k in all_keywords if k["sentiment"] == "negative"
        }

        top_reviews_data = select_top_reviews(reviews)
        spam_score = round((100 - score_breakdown.overall) / 20, 1)

        job = job_store.get_job(job_id)
        mode = job.mode if job else "app_only"

        result: dict[str, Any] = {
            "job_id": job_id,
            "mode": mode,
            "spam_score": spam_score,
            "ad_score": None,
            "app": {
                "name": app_info_data.get("title", ""),
                "developer": app_info_data.get("developer", ""),
                "google_play_id": google_play_id,
                "icon_url": app_info_data.get("icon", ""),
                "category": app_info_data.get("genre", ""),
            },
            "ratings": {
                "google_play": app_info_data.get("score") or 0.0,
            },
            "review_stats": {
                "negative_ratio": negative_ratio,
                "polarization_index": polarization_index,
                "trust_keywords": trust_keywords,
            },
            "reviews": {
                "negative": [
                    {"score": r["score"], "text": r["content"], "date": r["date"]}
                    for r in top_reviews_data["negative"]
                ],
                "positive": [
                    {"score": r["score"], "text": r["content"], "date": r["date"]}
                    for r in top_reviews_data["positive"]
                ],
            },
            "developer_stats": {
                "app_count": dev_data["recent_3months_count"] if dev_data else 0,
                "category_overlap": dev_data["category_overlap"] if dev_data else 0.0,
                "pattern_score": dev_data["pattern_score"] if dev_data else 0,
            },
            "developer_apps": [
                {
                    "name": app["name"],
                    "google_play_id": app["google_play_id"],
                    "released_at": app["released_at"],
                }
                for app in (dev_data["apps"] if dev_data else [])
            ],
        }

        job_store.update_job(job_id, status="done", progress=100, current_step="done", result=result)

    except Exception as exc:
        job_store.update_job(job_id, status="failed", current_step="failed", error=str(exc))


@router.post("/verify", response_model=VerifyCreateResponse)
async def create_verify_job(
    request: VerifyRequest,
    background_tasks: BackgroundTasks,
) -> VerifyCreateResponse:
    job_id = str(uuid.uuid4())
    mode = "with_ad" if request.ad_url else "app_only"
    job_store.create_job(job_id, mode)
    background_tasks.add_task(run_analysis, job_id, request.google_play_id)
    return VerifyCreateResponse(job_id=job_id, status="pending", mode=mode)


@router.get("/verify/{job_id}/status", response_model=VerifyStatusResponse)
async def get_verify_status(job_id: str) -> VerifyStatusResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": f"분석 작업을 찾을 수 없습니다: {job_id}"},
        )
    return VerifyStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
    )


@router.get("/verify/{job_id}", response_model=VerifyResultResponse)
async def get_verify_result(job_id: str) -> VerifyResultResponse:
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": f"분석 작업을 찾을 수 없습니다: {job_id}"},
        )
    if job.status != "done":
        raise HTTPException(
            status_code=202,
            detail={"code": "JOB_NOT_READY", "message": "분석이 아직 완료되지 않았습니다. /status를 먼저 확인하세요"},
        )
    return VerifyResultResponse(**job.result)
