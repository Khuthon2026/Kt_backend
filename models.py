from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String
from db import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    ad_url = Column(String, nullable=True)
    app_name = Column(String, nullable=False)
    google_play_id = Column(String, nullable=True)   # store_match 완료 후 확정
    mode = Column(String, nullable=False, default="app_only")  # app_only / with_ad
    status = Column(String, nullable=False, default="pending")  # pending / processing / done / failed
    current_step = Column(String, nullable=True)  # youtube_fetch / store_match / review_crawl / score_calc
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class App(Base):
    __tablename__ = "apps"

    id = Column(String, primary_key=True)
    google_play_id = Column(String, unique=True, nullable=False)
    app_store_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    developer = Column(String, nullable=False)
    category = Column(String, nullable=True)
    icon_url = Column(String, nullable=True)
    google_play_rating = Column(Float, nullable=True)
    ratings_count = Column(Integer, nullable=True)
    app_store_rating = Column(Float, nullable=True)
    installs = Column(String, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
