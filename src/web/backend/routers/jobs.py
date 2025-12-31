"""Job status router."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from ..dependencies import JobManagerDep
from ..services.job_manager import JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    job_manager: JobManagerDep,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all jobs, optionally filtered by project."""
    jobs = job_manager.list_jobs(project_id=project_id)
    return [
        {
            "job_id": job.id,
            "type": job.type.value,
            "project_id": job.project_id,
            "status": job.status.value,
            "progress": job.progress,
            "message": job.message,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }
        for job in jobs
    ]


@router.get("/{job_id}")
def get_job(
    job_id: str,
    job_manager: JobManagerDep,
) -> dict[str, Any]:
    """Get job status."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    return {
        "job_id": job.id,
        "type": job.type.value,
        "project_id": job.project_id,
        "status": job.status.value,
        "progress": job.progress,
        "message": job.message,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(
    job_id: str,
    job_manager: JobManagerDep,
) -> None:
    """Cancel a running job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status.value}",
        )

    job_manager.cancel_job(job_id)
