from typing import Generic, TypeVar, Optional, Literal
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class AppAnalyzeRequest(BaseModel):
    app_id: str  # com.example.app 또는 Play Store URL


class ScoreBreakdown(BaseModel):
    avg_rating_score: float        # 평균 평점 기반 (0~100)
    polarization_score: float      # ★1+★5 비율 역산
    negative_keyword_score: float  # 부정 키워드 빈도 역산
    review_ratio_score: float      # 설치수 대비 리뷰 수
    overall: float                 # 가중합 최종 점수 (0~100)


class AppInfo(BaseModel):
    title: str
    developer: str
    icon: str
    genre: str
    score: float
    ratings: int
    installs: str


class KeywordItem(BaseModel):
    word: str
    count: int
    sentiment: Literal["positive", "negative", "neutral"]


class ReviewItem(BaseModel):
    score: int
    content: str
    date: str


class TopReviews(BaseModel):
    negative: list[ReviewItem]
    positive: list[ReviewItem]


class AnalyzeResponse(BaseModel):
    app_id: str
    app_info: AppInfo
    score_breakdown: ScoreBreakdown
    verdict: str  # "TRUSTED" | "SUSPICIOUS" | "SCAM"
    keywords: list[KeywordItem]
    top_reviews: TopReviews
