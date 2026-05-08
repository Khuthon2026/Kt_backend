from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from models import Job
from schemas import ApiResponse, AppAnalyzeRequest, JobCreateResponse, JobStatusResponse
from services import job_processor

router = APIRouter(tags=["Score"])


@router.post("/analyze", response_model=ApiResponse[JobCreateResponse])
async def analyze_app(
    request: AppAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job_id = job_processor.create_job(db, request.app_name, request.ad_url)
    background_tasks.add_task(
        job_processor.run_analyze_job,
        job_id,
        request.app_name,
        request.ad_url,
    )
    return ApiResponse(
        success=True,
        data=JobCreateResponse(
            job_id=job_id,
            status="pending",
            mode="with_ad" if request.ad_url else "app_only",
        ),
    )


@router.get("/analyze/{job_id}/status", response_model=ApiResponse[JobStatusResponse])
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": f"분석 작업을 찾을 수 없습니다: {job_id}"},
        )
    return ApiResponse(
        success=True,
        data=JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
        ),
    )
