from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, func, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


class AppModel(Base):
    __tablename__ = "apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_play_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    developer: Mapped[str] = mapped_column(String(200), default="")
    developer_id: Mapped[str] = mapped_column(String(200), default="")
    icon_url: Mapped[str] = mapped_column(String(500), default="")
    genre: Mapped[str] = mapped_column(String(100), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    ratings: Mapped[int] = mapped_column(Integer, default=0)
    installs: Mapped[str] = mapped_column(String(50), default="0")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    reviews: Mapped[list["ReviewModel"]] = relationship(
        "ReviewModel",
        back_populates="app",
        cascade="all, delete-orphan",
    )


class ReviewModel(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, default="")
    review_date: Mapped[str] = mapped_column(String(50), default="")
    source: Mapped[str] = mapped_column(String(20), default="seed")
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    app: Mapped[AppModel] = relationship("AppModel", back_populates="reviews")
