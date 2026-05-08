# CLAUDE.md — Backend

> 이 파일은 Claude Code가 프로젝트 컨텍스트를 이해하기 위한 파일입니다.
> 해커톤 전용 설정이므로, 속도와 완성도를 최우선으로 합니다.

---

## 프로젝트 개요

- **목적**: 해커톤 백엔드 프로젝트
- **주제**: AdGap (De Clone) — 양산형 앱 광고 신뢰도 점수화 도구
- **개발 기간**: 해커톤 당일 (단기 집중 개발)
- **팀 규모**: 4명 (BE 2, FE 2)

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Framework | FastAPI |
| Language | Python 3.11 |
| 앱 스크래핑 | google-play-scraper |
| 영상 분석 | yt-dlp |
| 유효성 검사 | Pydantic v2 |
| 배포 | Railway (GitHub main 브랜치 자동 배포) |
| API 문서 | Swagger UI (FastAPI 자동 생성 — `/docs`) |

---

## 프로젝트 구조

```
/
├── main.py              # FastAPI 앱 진입점, CORS, 전역 예외 처리
├── schemas.py           # Pydantic DTO (ApiResponse 래퍼 포함)
├── routers/
│   ├── health.py        # GET /health
│   └── score.py         # POST /api/analyze
├── services/
│   ├── play_scraper.py  # google-play-scraper 연동, app_id 파싱
│   └── scorer.py        # 신뢰도 점수 계산 로직
├── requirements.txt
├── runtime.txt          # python-3.11 (Railway 감지용)
└── Procfile             # uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 코드 컨벤션

### 네이밍
- **파일/모듈**: snake_case → `play_scraper.py`, `score.py`
- **함수/변수**: snake_case → `get_app_info`, `app_id`
- **클래스**: PascalCase → `AppAnalyzeRequest`, `ScoreBreakdown`
- **상수**: UPPER_SNAKE_CASE → `SUSPICIOUS_KEYWORDS`, `DANGEROUS_PERMISSIONS`

### Router
- URL은 소문자 + 하이픈 → `/api/analyze`, `/api/app-score`
- RESTful 규칙 준수 (GET/POST/PUT/DELETE)
- 비즈니스 로직은 Router에 작성하지 않음 — `services/`로 위임

```python
# ✅ Good
@router.post("/analyze", response_model=ApiResponse[AnalyzeResponse])
async def analyze_app(request: AppAnalyzeRequest):
    app_data = await play_scraper.fetch_app_info(request.app_id)
    return ApiResponse(success=True, data=scorer.calculate_score(app_data))
```

### Service
- 하나의 함수는 하나의 책임만
- 동기 라이브러리(google-play-scraper 등)는 `asyncio.get_event_loop().run_in_executor`로 래핑

```python
# ✅ Good
async def fetch_app_info(app_id: str) -> dict:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: gps_app(app_id, lang="ko", country="kr"))
    return result
```

### DTO (Pydantic)
- Request / Response 스키마 분리
- 모든 스키마는 `schemas.py`에서 관리
- 공통 응답은 `ApiResponse[T]` Generic으로 래핑

```python
# ✅ Good
class AppAnalyzeRequest(BaseModel):
    app_id: str  # com.example.app 또는 Play Store URL

class AnalyzeResponse(BaseModel):
    app_id: str
    app_info: AppInfo
    score_breakdown: ScoreBreakdown
    suspicious_keywords: list[str]
    verdict: str  # "TRUSTED" | "SUSPICIOUS" | "SCAM"
```

### 예외 처리
- `HTTPException`으로 클라이언트 오류 처리
- `main.py`의 `global_exception_handler`가 500 에러 공통 처리

```python
# ✅ Good
raise HTTPException(
    status_code=404,
    detail={"code": "APP_NOT_FOUND", "message": f"앱을 찾을 수 없습니다: {app_id}"},
)
```

### 공통 응답 형식
모든 API 응답은 아래 형식으로 통일합니다.

```json
// 성공
{
  "success": true,
  "data": { ... }
}

// 실패
{
  "success": false,
  "error": {
    "code": "APP_NOT_FOUND",
    "message": "앱을 찾을 수 없습니다."
  }
}
```

---

## 핵심 API

### `POST /api/analyze`
앱 패키지명 또는 Play Store URL을 받아 신뢰도 점수를 반환합니다.

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
      "score": 4.2,
      "ratings": 15000,
      "installs": "1,000,000+",
      "description": "...",
      "icon": "https://...",
      "genre": "도구"
    },
    "score_breakdown": {
      "store_score": 78.4,
      "permission_score": 70.0,
      "keyword_score": 45.0,
      "overall": 66.2
    },
    "suspicious_keywords": ["무료", "선착순"],
    "verdict": "SUSPICIOUS"
  }
}
```

**verdict 기준**
| overall 점수 | verdict |
|---|---|
| 70 이상 | `TRUSTED` |
| 40 ~ 69 | `SUSPICIOUS` |
| 39 이하 | `SCAM` |

---

## 버전 관리

- 의존성 버전은 `requirements.txt`에 고정
- 임의로 버전 올리지 않음, 변경 시 팀원과 합의 후 수정

---

## 테스트 정책

- 해커톤 기간 중 단위 테스트 작성은 하지 않음
- API 동작 확인은 **Swagger UI (`/docs`)로 수동 테스트**

---

## 브랜치 전략

```
main         ← Railway 자동 배포 (직접 push 금지)
dev          ← 통합 브랜치 (PR 후 머지)
{이름}       ← 개인 작업 브랜치 (예: jihun, gildong)
```

### 규칙
1. **개인 브랜치 → dev** PR 후 머지
2. **dev → main** 은 배포 준비 완료 시점에만 머지
3. 큰 기능이 dev에 머지될 때마다 **개인 브랜치에 dev를 머지해서 싱크 유지**
4. main에 직접 push 절대 금지

---

## 배포 환경

- **플랫폼**: Railway
- **자동 배포**: `main` 브랜치 push 시 자동 배포
- **Python 버전**: `runtime.txt`에 `python-3.11` 명시
- **시작 명령**: `Procfile` — `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **환경변수**: Railway 대시보드에서 관리, 로컬은 `.env` 파일 사용 (gitignore 처리)

### Railway 주의사항
- 기존 Java 빌드팩이 잡혀 있으면 **Settings > Build > Python 빌드팩으로 수동 변경** 필요
- `requirements.txt`가 루트에 있으면 Railway가 자동 감지함

---

## CORS 설정

`main.py`의 `CORSMiddleware`에서 관리.
Vercel 도메인 확정 시 `allow_origins`에 실제 URL 추가.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://{실제-vercel-도메인}.vercel.app",  # 확정 시 교체
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 해커톤 필수 주의사항

### 하지 말아야 할 것 ❌
- 복잡한 설계 패턴 도입 (추상화, 인터페이스 분리 등)
- Docker / 컨테이너 환경 구성 (Railway가 알아서 처리)
- 지금 당장 쓰이지 않는 코드 작성
- 성능 최적화 (캐싱, 비동기 큐 등) — MVP 완성 후에 고민

### 우선순위 ✅
1. `POST /api/analyze` 동작 여부
2. 프론트엔드 연동 완료
3. 예외 처리 기본 세팅
4. 나머지 디테일

---

## 자주 쓰는 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 실행 (hot reload)
uvicorn main:app --reload

# 로컬 실행 (포트 지정)
uvicorn main:app --reload --port 8000
```

---

## API 문서

- 로컬: `http://localhost:8000/docs`
- 배포: `https://{railway-domain}/docs`

---

## 참고

- 프론트엔드 레포: `team-frontend`
- API 명세: Swagger (`/docs`) 또는 Notion 참고
- 디자인 시안: Figma 링크 (추후 업데이트)
- 문의: GitHub Issues 또는 Discord

## 성과 문서화
팀장이 "문서화해줘"라고 요청하면 @docs/DOCS_GUIDE.md 를 참조해서 정리하세요.
