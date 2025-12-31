"""File upload/download router."""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, status

from ..dependencies import ProjectServiceDep, ConfigDep

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


@router.post("/input", status_code=status.HTTP_201_CREATED)
async def upload_input_document(
    project_id: str,
    file: UploadFile = File(...),
    project_service: ProjectServiceDep = None,
    config: ConfigDep = None,
) -> dict[str, str]:
    """Upload an input document (markdown)."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    # Validate file size
    if file.size and file.size > config.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {config.max_upload_size} bytes",
        )

    # Validate file type
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only markdown (.md) files are allowed",
        )

    # Save file
    project_path = config.projects_dir / project_id
    input_dir = project_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    file_path = input_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "filename": file.filename,
        "path": str(file_path),
        "size": len(content),
    }


@router.post("/voiceover", status_code=status.HTTP_201_CREATED)
async def upload_voiceover(
    project_id: str,
    scene_id: str,
    file: UploadFile = File(...),
    project_service: ProjectServiceDep = None,
    config: ConfigDep = None,
) -> dict[str, str]:
    """Upload a manual voiceover recording."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {allowed_extensions}",
        )

    # Save file
    project_path = config.projects_dir / project_id
    voiceover_dir = project_path / "voiceover"
    voiceover_dir.mkdir(parents=True, exist_ok=True)

    # Save with scene_id as filename, keeping original extension
    file_path = voiceover_dir / f"{scene_id}{ext}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "scene_id": scene_id,
        "filename": file_path.name,
        "path": str(file_path),
        "size": len(content),
    }


@router.get("/input")
def list_input_files(
    project_id: str,
    project_service: ProjectServiceDep,
    config: ConfigDep,
) -> list[dict[str, str]]:
    """List input files for a project."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    project_path = config.projects_dir / project_id
    input_dir = project_path / "input"

    if not input_dir.exists():
        return []

    return [
        {
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
        }
        for f in input_dir.glob("*")
        if f.is_file()
    ]


@router.delete("/input/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_input_file(
    project_id: str,
    filename: str,
    project_service: ProjectServiceDep,
    config: ConfigDep,
) -> None:
    """Delete an input file."""
    # Verify project exists
    try:
        project_service.get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )

    project_path = config.projects_dir / project_id
    file_path = project_path / "input" / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}",
        )

    file_path.unlink()
