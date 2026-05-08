import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from models import Job, App
from services import play_scraper
from services import youtube as yt_service


def create_job(db: Session, app_name: str, ad_url: Optional[str]) -> str:
    job_id = str(uuid.uuid4())
    db.add(Job(
        id=job_id,
        app_name=app_name,
        ad_url=ad_url,
        mode="with_ad" if ad_url else "app_only",
        status="pending",
        progress=0,
    ))
    db.commit()
    return job_id


def _update_job(db: Session, job_id: str, **kwargs):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        job.updated_at = datetime.utcnow()
        db.commit()


async def run_analyze_job(job_id: str, app_name: str, ad_url: Optional[str]):
    from db import SessionLocal
    db = SessionLocal()
    try:
        _update_job(db, job_id, status="processing", current_step="youtube_fetch", progress=10)

        # Step 3 — YouTube 광고 메타데이터 수집
        if ad_url:
            await yt_service.fetch_ad_metadata(ad_url)
            # 추후 ad_score 계산에 사용; 현재는 DB 저장 없이 수집만

        # Step 4 — Play Store 앱 매칭
        _update_job(db, job_id, current_step="store_match", progress=40)
        app_result = await play_scraper.search_app(app_name)

        if not app_result:
            _update_job(db, job_id, status="failed", current_step=None, progress=0)
            return

        google_play_id = app_result["google_play_id"]
        _update_job(db, job_id, google_play_id=google_play_id, progress=70)

        # apps 테이블 저장 (없으면 신규 생성, 있으면 last_crawled_at 갱신)
        existing = db.query(App).filter(App.google_play_id == google_play_id).first()
        if not existing:
            db.add(App(
                id=str(uuid.uuid4()),
                google_play_id=google_play_id,
                name=app_result["name"],
                developer=app_result["developer"],
                category=app_result["category"],
                icon_url=app_result["icon_url"],
                google_play_rating=app_result["score"],
                ratings_count=app_result["ratings_count"],
                installs=app_result["installs"],
                last_crawled_at=datetime.utcnow(),
            ))
        else:
            existing.last_crawled_at = datetime.utcnow()
            existing.google_play_rating = app_result["score"]
        db.commit()

        _update_job(db, job_id, status="done", current_step="store_match", progress=100)

    except Exception:
        _update_job(db, job_id, status="failed")
    finally:
        db.close()
