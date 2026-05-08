from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import health, score, search, verify

app = FastAPI(
    title="AdGap API",
    description="양산형 앱 광고 신뢰도 점수화 도구",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://khuthonbackend-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": str(exc)},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": detail.get("code", "HTTP_ERROR"), "message": detail.get("message", "")},
        },
    )


app.include_router(health.router)
app.include_router(score.router, prefix="/api")
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(verify.router, prefix="/api", tags=["verify"])
