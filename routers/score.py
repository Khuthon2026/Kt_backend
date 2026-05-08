from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from db import get_db
from schemas import ApiResponse, AppAnalyzeRequest, JobCreateResponse
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
