# AdGap — 양산형 앱 광고 신뢰도 점수화 API

> **Khuthon 2026** 해커톤 백엔드 레포지토리  
> Google Play 앱의 광고 기만 여부를 리뷰·개발자 패턴 기반으로 분석합니다.

---

## 개요

유튜브·SNS에서 흔히 보이는 **"광고와 실제가 다른 양산형 앱"**을 탐지하는 신뢰도 점수화 도구입니다.  
앱 패키지명(또는 Play Store URL)을 입력하면 리뷰 키워드 분석, 평점 양극화, 개발자 출시 패턴 등 6개 시그널을 종합해 `TRUSTED / SUSPICIOUS / SCAM` 판정을 반환합니다.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Framework | FastAPI 0.115 |
| Language | Python 3.11 |
| 앱 데이터 수집 | google-play-scraper 1.2.7 |
| HTTP 클라이언트 | httpx 0.27 |
| 유효성 검사 | Pydantic v2 |
| DB | PostgreSQL (SQLAlchemy 2 + asyncpg) |
| 배포 | Railway (main 브랜치 자동 배포) |

---

## 프로젝트 구조

```
/
├── main.py              # FastAPI 앱, CORS, 전역 예외 처리
├── schemas.py           # Pydantic DTO (ApiResponse<T> 래퍼 포함)
├── db.py                # DB 초기화 (asyncpg)
├── job_store.py         # 비동기 분석 Job 상태 관리 (인메모리)
├── routers/
│   ├── health.py        # GET /health
│   ├── search.py        # GET /api/search
│   ├── score.py         # POST /api/analyze
│   └── verify.py        # POST /api/verify  (비동기 분석 Job)
├── services/
│   ├── play_scraper.py  # google-play-scraper 연동, app_id 파싱
│   ├── scorer.py        # 신뢰도 점수 계산 로직
│   ├── developer.py     # 개발자 앱 출시 패턴 분석
│   └── review_store.py  # 리뷰 DB 캐싱 레이어
├── requirements.txt
├── runtime.txt          # python-3.11
└── Procfile             # uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## API 엔드포인트

### `GET /health`
서버 상태 확인

---

### `GET /api/search?q={검색어}`
앱 이름으로 Play Store 검색

```json
// Response
{
  "success": true,
  "data": {
    "results": [
      {
        "google_play_id": "com.example.app",
        "title": "앱 이름",
        "developer": "개발사",
        "icon": "https://...",
        "score": 4.2
      }
    ]
  }
}
```

---

### `POST /api/analyze`
앱 신뢰도 점수 즉시 반환 (동기)

```json
// Request
{ "app_id": "com.example.app" }

// Response
{
  "success": true,
  "data": {
    "app_id": "com.example.app",
    "app_info": {
      "title": "앱 이름",
      "developer": "개발사",
      "developer_id": "개발사 ID",
      "icon": "https://...",
      "genre": "도구",
      "score": 4.2,
      "ratings": 15000,
      "installs": "1,000,000+"
    },
    "score_breakdown": {
      "avg_rating_score": 84.0,
      "polarization_score": 72.3,
      "negative_keyword_score": 91.5,
      "review_ratio_score": 60.0,
      "overall": 81.2
    },
    "verdict": "TRUSTED",
    "keywords": [
      { "word": "광고와 다름", "count": 3, "sentiment": "negative" }
    ],
    "top_reviews": {
      "negative": [{ "score": 1, "content": "...", "date": "..." }],
      "positive": [{ "score": 5, "content": "...", "date": "..." }]
    },
    "developer_apps": {
      "developer_id": "...",
      "total_count": 12,
      "recent_3months_count": 3,
      "category_overlap": 0.83,
      "pattern_score": 4,
      "apps": [...]
    }
  }
}
```

**verdict 기준**

| overall | verdict |
|---------|---------|
| 70 이상 | `TRUSTED` |
| 40 ~ 69 | `SUSPICIOUS` |
| 39 이하 | `SCAM` |

---

### `POST /api/verify`
비동기 심층 분석 Job 생성 (광고 URL 선택 입력)

```json
// Request
{ "google_play_id": "com.example.app", "ad_url": "https://youtu.be/xxxxx" }

// Response
{ "job_id": "uuid", "status": "pending", "mode": "with_ad" }
```

### `GET /api/verify/{job_id}/status`
분석 진행 상태 폴링

```json
{ "job_id": "uuid", "status": "processing", "progress": 70, "current_step": "developer_fetch" }
```

### `GET /api/verify/{job_id}`
분석 완료 결과 조회 (`status == "done"` 이후 호출)

---

## 점수 알고리즘

| 시그널 | 데이터 소스 | 가중치 |
|--------|-------------|--------|
| `avg_rating_score` | Play Store 평점 (0~5 → 0~100) | 5% |
| `polarization_score` | ★1 + ★5 비율 역산 | 5% |
| `negative_keyword_score` | 광고 기만 키워드 빈도 역산 (1점 리뷰 가중) | 35% |
| `review_ratio_score` | 설치수 대비 리뷰 수 정규화 | 5% |
| `developer_pattern_score` | 개발자 앱 출시 패턴 (양산형 탐지) | 10% |
| `genre_trust_score` | 장르 기반 신뢰 보정 (게임 앱 패널티) | 40% |

> overall이 낮을수록 위험. `negative_keyword_score`와 `polarization_score`는 원본 수치 역산 후 가중합.

---

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일)
DATABASE_URL=postgresql+asyncpg://...

# 서버 실행 (hot reload)
uvicorn main:app --reload --port 8000
```

API 문서: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 배포

- 플랫폼: **Railway** — `main` 브랜치 push 시 자동 배포
- Python 버전: `runtime.txt` → `python-3.11`
- 시작 명령: `Procfile` → `uvicorn main:app --host 0.0.0.0 --port $PORT`
- 환경변수: Railway 대시보드에서 관리

---

## 공통 응답 형식

```json
// 성공
{ "success": true, "data": { ... } }

// 실패
{ "success": false, "error": { "code": "APP_NOT_FOUND", "message": "앱을 찾을 수 없습니다." } }
```
