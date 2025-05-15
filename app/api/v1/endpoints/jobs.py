from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1 import schemas # Updated import
from app.db import models # Updated import
from app.db.session import get_db

router = APIRouter()

@router.post("/", response_model=schemas.JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    *,
    db: Session = Depends(get_db),
    job_in: schemas.JobCreate
) -> models.Job: # Return type should be the ORM model for FastAPI to convert using response_model
    """
    Create new job.
    """
    # Create an instance of the SQLAlchemy model from the Pydantic model
    db_job = models.Job(title=job_in.title, description=job_in.description)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@router.get("/", response_model=List[schemas.JobRead])
def read_jobs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[models.Job]: # Return type is a list of ORM models
    """
    Retrieve all jobs with pagination.
    """
    jobs = db.query(models.Job).offset(skip).limit(limit).all()
    return jobs

# Get a specific job by ID
@router.get("/{job_id}", response_model=schemas.JobRead)
def read_job_by_id(
    job_id: int,
    db: Session = Depends(get_db)
) -> models.Job:
    """
    Get a specific job by its ID.
    """
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return db_job

@router.put("/{job_id}", response_model=schemas.JobRead)
def update_job(
    job_id: int,
    job_in: schemas.JobUpdate,
    db: Session = Depends(get_db)
) -> models.Job:
    """
    Update an existing job.
    """
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Update fields from job_in if they are provided (not None)
    update_data = job_in.model_dump(exclude_unset=True) # Pydantic v2
    for key, value in update_data.items():
        setattr(db_job, key, value)
    
    db.add(db_job) # or db.merge(db_job) if you prefer
    db.commit()
    db.refresh(db_job)
    return db_job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an existing job.
    """
    db_job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    db.delete(db_job)
    db.commit()
    # No need to return anything for 204 response
    return None # Or can just be empty if function has no explicit return type annotation

# TODO: Add tests for pagination (skip, limit) for read_jobs in test_jobs.py 