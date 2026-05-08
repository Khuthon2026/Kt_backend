from typing import Generic, TypeVar, Optional
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
    store_score: float      # 앱스토어 지표 점수 (0~100)
    permission_score: float  # 권한 요청 점수 (0~100)
    keyword_score: float    # 설명 키워드 점수 (0~100)
    overall: float          # 종합 신뢰도 점수 (0~100)


class AppInfo(BaseModel):
    title: str
    developer: str
    score: float
    ratings: int
    installs: str
    description: str
    icon: str
    genre: str


class AnalyzeResponse(BaseModel):
    app_id: str
    app_info: AppInfo
    score_breakdown: ScoreBreakdown
    suspicious_keywords: list[str]
    verdict: str  # "TRUSTED" | "SUSPICIOUS" | "SCAM"
