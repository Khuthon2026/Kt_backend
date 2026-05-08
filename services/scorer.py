from __future__ import annotations

import re
from typing import Any

from schemas import ScoreBreakdown

# 광고 기만 특화 키워드 (scoring에 강하게 반영)
AD_DECEPTION_KEYWORDS = [
    "광고와 다름", "광고랑 다름", "광고와 달라", "광고랑 달라",
    "광고가 다름", "광고랑달라", "광고와달라",
    "광고와 다른", "광고랑 다른",
    "실제와 다름", "실제랑 다름",
    "낚시", "낚였", "낚혀", "낚이다",
    "사기", "속았", "거짓", "기만",
    "광고에 속", "광고에 나온", "광고에 등장",
    "광고 보고 다운", "광고 보고 설치", "광고 보고 함",
    "광고대로 아님", "광고랑 전혀", "광고랑 이렇게",
    "광고 게임이랑", "광고 내용이랑", "광고랑 내용",
    "광고 속 게임", "광고만 보고",
]

# 일반 부정 키워드 (scoring에 약하게 반영, 광고 기만과 구분)
GENERAL_NEGATIVE_KEYWORDS = [
    "환불", "최악", "쓰레기", "별로", "현질", "도박", "돈낭비",
    "달라요", "다르다", "삭제", "다운받지 마",
]

# 표시용 전체 부정 키워드
NEGATIVE_KEYWORDS = AD_DECEPTION_KEYWORDS + GENERAL_NEGATIVE_KEYWORDS

POSITIVE_KEYWORDS = [
    "재밌어요", "좋아요", "추천", "만족", "괜찮아요", "유용", "편리",
]


async def calculate_score(
    app_info: dict[str, Any],
    histogram: dict[int, int],
    reviews: list[dict[str, Any]],
    pattern_score: int | None = None,
    low_reviews: list[dict[str, Any]] | None = None,
) -> ScoreBreakdown:
    avg_rating_score = _calc_avg_rating_score(app_info.get("score") or 0.0)
    polarization_score = _calc_polarization_score(histogram)
    negative_keyword_score = _calc_negative_keyword_score(reviews, low_reviews or [])
    review_ratio_score = _calc_review_ratio_score(
        app_info.get("ratings") or 0,
        app_info.get("installs") or "0",
    )
    # None = 개발자 데이터 없음 → 중립(50), 0~5 = 실제 패턴 점수
    developer_pattern_score = 50.0 if pattern_score is None else (1 - pattern_score / 5) * 100
    genre_trust_score = _calc_game_bias_score(
        title=app_info.get("title") or "",
        developer=app_info.get("developer") or "",
        app_id=app_info.get("google_play_id") or app_info.get("app_id") or "",
    )

    overall = (
        avg_rating_score * 0.05
        + polarization_score * 0.05
        + negative_keyword_score * 0.35
        + review_ratio_score * 0.05
        + developer_pattern_score * 0.10
        + genre_trust_score * 0.40
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
    smooth = max(int(total * 0.02), 5)
    total_s = total + smooth * 5
    one_ratio = ((histogram.get(1) or 0) + smooth) / total_s
    five_ratio = ((histogram.get(5) or 0) + smooth) / total_s
    penalty = min(one_ratio * 1.6 + five_ratio * 0.6, 1.0)
    return (1 - penalty) * 100


def _calc_negative_keyword_score(reviews: list[dict[str, Any]], low_reviews: list[dict[str, Any]]) -> float:
    if not reviews and not low_reviews:
        return 100.0

    def _has_ad_keyword(review: dict[str, Any]) -> bool:
        content = _normalize_content(review.get("content", ""))
        return any(word in content for word in AD_DECEPTION_KEYWORDS)

    # 전체 리뷰 기반 탐지
    all_reviews_count = len(reviews) or 1
    all_ad_hits = sum(1 for r in reviews if _has_ad_keyword(r))
    all_ad_ratio = all_ad_hits / all_reviews_count

    # 1점 리뷰 기반 탐지 (광고 기만 신호가 더 명확함 → 3배 가중)
    low_reviews_count = len(low_reviews) or 1
    low_ad_hits = sum(1 for r in low_reviews if _has_ad_keyword(r))
    low_ad_ratio = low_ad_hits / low_reviews_count

    # 두 신호 결합: 1점 리뷰 키워드 비율에 더 높은 가중치
    combined_ratio = all_ad_ratio * 0.4 + low_ad_ratio * 0.6
    return (1 - min(combined_ratio * 6.0, 1.0)) * 100


def _get_game_keywords() -> set[str]:
    return {
        "game",
        "rpg",
        "idle",
        "war",
        "hero",
        "battle",
        "quest",
        "adventure",
        "arena",
        "raid",
        "clash",
        "dungeon",
        "hunter",
        "strategy",
        "puzzle",
        "arcade",
        "racing",
        "sports",
        "card",
        "simulation",
        "moe",
        "rpg",
        "게임",
        "롤플레잉",
        "rpg",
        "전쟁",
        "배틀",
        "영웅",
        "헌터",
        "던전",
        "모험",
        "전략",
        "퍼즐",
        "캐주얼",
        "시뮬레이션",
        "레이싱",
        "스포츠",
        "카드",
        "아케이드",
        "퀘스트",
        "클래시",
        "herowars",
        "hero wars",
        "demonhunter",
        "demon hunter",
        "artifexmundi",
        "nexters",
    }


def is_game_app(title: str, developer: str, app_id: str) -> bool:
    normalized = " ".join([title, developer, app_id]).lower().strip()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in _get_game_keywords())


def _calc_game_bias_score(title: str, developer: str, app_id: str) -> float:
    if is_game_app(title, developer, app_id):
        return 20.0
    return 95.0


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
            keyword_line = _extract_keyword_sentence(content, keywords)
        formatted.append(
            {
                "score": int(review.get("score") or 0),
                "content": keyword_line,
                "date": str(review.get("at", "")),
            }
        )
    return formatted


def _extract_keyword_sentence(content: str, keywords: list[str]) -> str:
    if not content:
        return ""

    separators = r"(?<=[.!?。？！])\s+|\n+"
    sentences = [s.strip() for s in re.split(separators, content) if s.strip()]
    for sentence in sentences:
        if any(word in sentence for word in keywords):
            return sentence

    # If no sentence boundaries or no match, return a compact snippet around a keyword.
    keyword_pos = -1
    keyword = ""
    for word in keywords:
        pos = content.find(word)
        if pos != -1:
            keyword_pos = pos
            keyword = word
            break

    if keyword_pos == -1:
        return _truncate_text(content, 120)

    return _snippet_around_keyword(content, keyword_pos, len(keyword), 120)


def _truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    trimmed = text[: max_len - 3].rstrip()
    return f"{trimmed}..."


def _snippet_around_keyword(text: str, keyword_pos: int, keyword_len: int, max_len: int) -> str:
    if len(text) <= max_len:
        return text

    half = max_len // 2
    start = max(keyword_pos - half, 0)
    end = min(keyword_pos + keyword_len + half, len(text))
    snippet = text[start:end].strip()

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
