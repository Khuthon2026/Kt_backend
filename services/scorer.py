from __future__ import annotations

import re
from typing import Any

from schemas import ScoreBreakdown

NEGATIVE_KEYWORDS = [
    "광고와 다름", "광고랑 다름", "사기", "낚시", "다운받지 마",
    "환불", "거짓", "속았", "삭제", "별로", "최악", "쓰레기",
]

POSITIVE_KEYWORDS = [
    "재밌어요", "좋아요", "추천", "만족", "괜찮아요", "유용", "편리",
]


async def calculate_score(app_info: dict[str, Any], histogram: dict[int, int], reviews: list[dict[str, Any]]) -> ScoreBreakdown:
    avg_rating_score = _calc_avg_rating_score(app_info.get("score") or 0.0)
    polarization_score = _calc_polarization_score(histogram)
    negative_keyword_score = _calc_negative_keyword_score(reviews)
    review_ratio_score = _calc_review_ratio_score(
        app_info.get("ratings") or 0,
        app_info.get("installs") or "0",
    )

    overall = (
        avg_rating_score * 0.25
        + polarization_score * 0.30
        + negative_keyword_score * 0.30
        + review_ratio_score * 0.15
    )

    return ScoreBreakdown(
        avg_rating_score=round(avg_rating_score, 1),
        polarization_score=round(polarization_score, 1),
        negative_keyword_score=round(negative_keyword_score, 1),
        review_ratio_score=round(review_ratio_score, 1),
        overall=round(overall, 1),
    )


def extract_keywords(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keyword_counts: dict[str, dict[str, Any]] = {}
    for word in NEGATIVE_KEYWORDS:
        keyword_counts[word] = {"word": word, "count": 0, "sentiment": "negative"}
    for word in POSITIVE_KEYWORDS:
        keyword_counts[word] = {"word": word, "count": 0, "sentiment": "positive"}

    for review in reviews:
        content = _normalize_content(review.get("content", ""))
        for word in NEGATIVE_KEYWORDS:
            if word in content:
                keyword_counts[word]["count"] += 1
        for word in POSITIVE_KEYWORDS:
            if word in content:
                keyword_counts[word]["count"] += 1

    items = [item for item in keyword_counts.values() if item["count"] > 0]
    items.sort(key=lambda x: x["count"], reverse=True)
    return items[:20]


def select_top_reviews(reviews: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    negative_candidates = [
        r for r in reviews
        if (r.get("score") or 0) <= 2
        and any(word in _normalize_content(r.get("content", "")) for word in NEGATIVE_KEYWORDS)
    ]
    positive_candidates = [
        r for r in reviews
        if (r.get("score") or 0) >= 4
        and any(word in _normalize_content(r.get("content", "")) for word in POSITIVE_KEYWORDS)
    ]

    negative = _format_top_reviews(negative_candidates, limit=2, keywords=NEGATIVE_KEYWORDS)
    positive = _format_top_reviews(positive_candidates, limit=2, keywords=POSITIVE_KEYWORDS)
    return {"negative": negative, "positive": positive}


def get_verdict(overall_score: float) -> str:
    if overall_score >= 70:
        return "TRUSTED"
    if overall_score >= 40:
        return "SUSPICIOUS"
    return "SCAM"


def _calc_avg_rating_score(score: float) -> float:
    return (score / 5.0) * 100


def _calc_polarization_score(histogram: dict[int, int]) -> float:
    total = sum(histogram.values()) or 1
    polar_ratio = ((histogram.get(1) or 0) + (histogram.get(5) or 0)) / total
    return (1 - polar_ratio) * 100


def _calc_negative_keyword_score(reviews: list[dict[str, Any]]) -> float:
    if not reviews:
        return 100.0

    hit_count = 0
    for review in reviews:
        content = _normalize_content(review.get("content", ""))
        if any(word in content for word in NEGATIVE_KEYWORDS):
            hit_count += 1

    neg_ratio = hit_count / len(reviews)
    return (1 - min(neg_ratio * 5, 1)) * 100


def _calc_review_ratio_score(ratings: int, installs: str) -> float:
    installs_numeric = _parse_installs(installs)
    if installs_numeric <= 0:
        return 0.0
    ratio = ratings / installs_numeric
    return min(ratio * 1000, 100)


def _parse_installs(installs: str) -> int:
    digits = re.sub(r"[^0-9]", "", installs or "")
    return int(digits) if digits else 0


def _normalize_content(content: str) -> str:
    return (content or "").strip()


def _format_top_reviews(
    reviews: list[dict[str, Any]],
    limit: int,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    sorted_reviews = sorted(
        reviews,
        key=lambda r: len(_normalize_content(r.get("content", ""))),
        reverse=True,
    )
    formatted: list[dict[str, Any]] = []
    for review in sorted_reviews[:limit]:
        content = _normalize_content(review.get("content", ""))
        keyword_line = content
        if keywords:
            matched = [word for word in keywords if word in content]
            if matched:
                keyword_line = ", ".join(matched)
        formatted.append(
            {
                "score": int(review.get("score") or 0),
                "content": keyword_line,
                "date": str(review.get("at", "")),
            }
        )
    return formatted
