"""Feedback processing router."""

from fastapi import APIRouter, HTTPException, status

from ..dependencies import FeedbackServiceDep, ProjectServiceDep
from ..models.requests import AddFeedbackRequest
from ..models.responses import JobStartedResponse, FeedbackItemResponse

router = APIRouter(prefix="/projects/{project_id}/feedback", tags=["feedback"])


@router.get("", response_model=list[FeedbackItemResponse])
def list_feedback(
    project_id: str,
    service: FeedbackServiceDep,
    project_service: ProjectServiceDep,
) -> list[FeedbackItemResponse]:
    """List feedback history for a project."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    return service.list_feedback(project_id)


@router.post("", response_model=JobStartedResponse, status_code=status.HTTP_202_ACCEPTED)
def process_feedback(
    project_id: str,
    request: AddFeedbackRequest,
    service: FeedbackServiceDep,
    project_service: ProjectServiceDep,
) -> JobStartedResponse:
    """Process natural language feedback."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    job_id = service.process_feedback(
        project_id=project_id,
        feedback_text=request.feedback_text,
        dry_run=request.dry_run,
    )

    return JobStartedResponse(
        job_id=job_id,
        status="pending",
        message="Feedback processing started" + (" (dry run)" if request.dry_run else ""),
    )


@router.get("/{feedback_id}", response_model=FeedbackItemResponse)
def get_feedback(
    project_id: str,
    feedback_id: str,
    service: FeedbackServiceDep,
    project_service: ProjectServiceDep,
) -> FeedbackItemResponse:
    """Get a specific feedback item."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    item = service.get_feedback(project_id, feedback_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback not found: {feedback_id}",
        )

    return item
