"""
Background Jobs Router

API endpoints for creating and managing background jobs (permit pulls, property aggregation).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from supabase import Client

from app.database import get_db

router = APIRouter(prefix="/api/background-jobs", tags=["Background Jobs"])


class CreateJobRequest(BaseModel):
    """Request model for creating a background job."""
    job_type: str = Field(..., description="Job type: initial_pull, incremental_pull, or property_aggregation")
    parameters: dict = Field(default={}, description="Job-specific parameters")


class JobResponse(BaseModel):
    """Response model for a background job."""
    id: str
    county_id: str
    job_type: str
    status: str
    parameters: Optional[dict] = None
    permits_pulled: int = 0
    permits_saved: int = 0
    properties_created: int = 0
    properties_updated: int = 0
    leads_created: int = 0
    current_year: Optional[int] = None
    current_batch: int = 0
    progress_percent: int = 0
    permits_per_second: Optional[float] = None
    estimated_completion_at: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    elapsed_seconds: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/counties/{county_id}/jobs", response_model=JobResponse)
async def create_job(
    county_id: str,
    request: CreateJobRequest,
    db: Client = Depends(get_db)
):
    """
    Create a new background job for a county.

    Example for 30-year historical pull:
    ```json
    {
        "job_type": "initial_pull",
        "parameters": {
            "years": 30,
            "permit_type": "Building/Residential/Trade/Mechanical"
        }
    }
    ```

    Example for incremental daily pull:
    ```json
    {
        "job_type": "incremental_pull",
        "parameters": {
            "days_back": 2,
            "permit_type": "Building/Residential/Trade/Mechanical"
        }
    }
    ```
    """
    # Verify county exists
    county_result = db.table('counties').select('id').eq('id', county_id).execute()
    if not county_result.data:
        raise HTTPException(status_code=404, detail="County not found")

    # Validate job_type
    valid_job_types = ['initial_pull', 'incremental_pull', 'property_aggregation']
    if request.job_type not in valid_job_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job_type. Must be one of: {', '.join(valid_job_types)}"
        )

    # Check if there's already a running job for this county
    running_jobs = db.table('background_jobs') \
        .select('id, job_type, status') \
        .eq('county_id', county_id) \
        .in_('status', ['pending', 'running']) \
        .execute()

    if running_jobs.data:
        existing_job = running_jobs.data[0]
        raise HTTPException(
            status_code=409,
            detail=f"Job {existing_job['id']} is already {existing_job['status']} for this county. Wait for it to complete or cancel it first."
        )

    # Create job
    job_data = {
        'county_id': county_id,
        'job_type': request.job_type,
        'status': 'pending',
        'parameters': request.parameters,
    }

    result = db.table('background_jobs').insert(job_data).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")

    return result.data[0]


@router.get("/counties/{county_id}/jobs", response_model=List[JobResponse])
async def list_jobs(
    county_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    db: Client = Depends(get_db)
):
    """
    List background jobs for a county.

    Optional filters:
    - status: Filter by job status (pending, running, completed, failed, cancelled)
    - limit: Max number of jobs to return (default 50)
    """
    query = db.table('background_jobs') \
        .select('*') \
        .eq('county_id', county_id) \
        .order('created_at', desc=True) \
        .limit(limit)

    if status:
        query = query.eq('status', status)

    result = query.execute()

    return result.data or []


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Client = Depends(get_db)
):
    """
    Get a specific job by ID.

    Returns detailed progress information including:
    - permits_pulled, permits_saved
    - properties_created, properties_updated
    - leads_created
    - current_year, current_batch (for multi-year pulls)
    - progress_percent (0-100)
    - permits_per_second, estimated_completion_at
    """
    result = db.table('background_jobs').select('*').eq('id', job_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    return result.data[0]


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Client = Depends(get_db)
):
    """
    Cancel a pending or running job.

    Note: Cancellation is graceful - the job will finish its current batch
    before stopping. Check the job status to confirm it has been cancelled.
    """
    # Get current job
    result = db.table('background_jobs').select('*').eq('id', job_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = result.data[0]

    # Only allow cancelling pending or running jobs
    if job['status'] not in ['pending', 'running']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job['status']}'. Can only cancel pending or running jobs."
        )

    # Update job status to cancelled
    update_result = db.table('background_jobs').update({
        'status': 'cancelled',
        'completed_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', job_id).execute()

    if not update_result.data:
        raise HTTPException(status_code=500, detail="Failed to cancel job")

    return {
        "success": True,
        "message": f"Job {job_id} cancelled",
        "job": update_result.data[0]
    }


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: Client = Depends(get_db)
):
    """
    Delete a completed or failed job.

    Cannot delete pending or running jobs - cancel them first.
    """
    # Get current job
    result = db.table('background_jobs').select('*').eq('id', job_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = result.data[0]

    # Only allow deleting completed, failed, or cancelled jobs
    if job['status'] in ['pending', 'running']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete job with status '{job['status']}'. Cancel it first."
        )

    # Delete job
    db.table('background_jobs').delete().eq('id', job_id).execute()

    return {
        "success": True,
        "message": f"Job {job_id} deleted"
    }
