from schemas import ScoreBreakdown

SUSPICIOUS_KEYWORDS = [
    # 한국어
    "무료", "공짜", "선착순", "한정", "이벤트", "특가", "긴급", "즉시",
    "100%", "보장", "확정", "당첨", "쉽게", "간단히", "누구나", "지금바로",
    "돈버는", "수익", "재테크", "부업", "알바",
    # 영어
    "free", "limited", "exclusive", "guaranteed", "instant", "easy money",
    "get rich", "earn cash", "no risk",
]

DANGEROUS_PERMISSIONS = {
    "android.permission.READ_CONTACTS",
    "android.permission.SEND_SMS",
    "android.permission.READ_SMS",
    "android.permission.CALL_PHONE",
    "android.permission.RECORD_AUDIO",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.CAMERA",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.PROCESS_OUTGOING_CALLS",
}


def calculate_score(app_data: dict) -> ScoreBreakdown:
    store_score = _calc_store_score(app_data)
    permission_score = _calc_permission_score(app_data.get("permissions", []))
    keyword_score = _calc_keyword_score(app_data.get("description", ""))

    overall = store_score * 0.4 + permission_score * 0.3 + keyword_score * 0.3

    return ScoreBreakdown(
        store_score=round(store_score, 1),
        permission_score=round(permission_score, 1),
        keyword_score=round(keyword_score, 1),
        overall=round(overall, 1),
    )


def _calc_store_score(app_data: dict) -> float:
    rating = app_data.get("score") or 0.0
    ratings_count = app_data.get("ratings") or 0

    rating_score = (rating / 5.0) * 100

    if ratings_count < 100:
        trust = 0.4
    elif ratings_count < 1_000:
        trust = 0.6
    elif ratings_count < 10_000:
        trust = 0.8
    else:
        trust = 1.0

    return rating_score * trust


def _calc_permission_score(permissions: list) -> float:
    dangerous = sum(1 for p in permissions if p in DANGEROUS_PERMISSIONS)
    if dangerous == 0:
        return 100.0
    elif dangerous <= 2:
        return 70.0
    elif dangerous <= 4:
        return 45.0
    else:
        return 15.0


def _calc_keyword_score(description: str) -> float:
    desc_lower = description.lower()
    hits = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in desc_lower)
    if hits == 0:
        return 100.0
    elif hits <= 2:
        return 70.0
    elif hits <= 5:
        return 45.0
    else:
        return 15.0


def find_suspicious_keywords(description: str) -> list[str]:
    desc_lower = description.lower()
    return [kw for kw in SUSPICIOUS_KEYWORDS if kw in desc_lower]


def get_verdict(overall_score: float) -> str:
    if overall_score >= 70:
        return "TRUSTED"
    elif overall_score >= 40:
        return "SUSPICIOUS"
    else:
        return "SCAM"
