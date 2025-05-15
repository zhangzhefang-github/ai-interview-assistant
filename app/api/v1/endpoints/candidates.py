from typing import List, Any
import shutil # Potentially for saving temp file, though parse_resume might take bytes directly
import io # For creating in-memory file-like objects for docx
import logging # Add this import

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form # Added File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import EmailStr # To use EmailStr directly for Form parameters

import docx # For .docx parsing
import fitz  # PyMuPDF for .pdf parsing

from app.api.v1 import schemas # Import schemas
from app.db import models     # Import models
from app.db.session import get_db
from app.services.ai_services import parse_resume # Import the AI service

logger = logging.getLogger(__name__) # Add this line to get a logger instance

router = APIRouter()

@router.post("/", response_model=schemas.Candidate, status_code=status.HTTP_201_CREATED)
def create_candidate(
    *,
    db: Session = Depends(get_db),
    candidate_in: schemas.CandidateCreate
) -> models.Candidate:
    """
    Create new candidate.
    """
    # Check if candidate with this email already exists
    existing_candidate = db.query(models.Candidate).filter(models.Candidate.email == candidate_in.email).first()
    if existing_candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A candidate with this email already exists."
        )
    
    db_candidate = models.Candidate(
        name=candidate_in.name,
        email=candidate_in.email,
        resume_text=candidate_in.resume_text
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

@router.get("/{candidate_id}", response_model=schemas.Candidate)
def read_candidate_by_id(
    candidate_id: int,
    db: Session = Depends(get_db)
) -> models.Candidate:
    """
    Get a specific candidate by their ID.
    """
    db_candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return db_candidate

@router.get("/", response_model=List[schemas.Candidate])
def read_candidates(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[models.Candidate]:
    """
    Retrieve all candidates with pagination.
    """
    candidates = db.query(models.Candidate).offset(skip).limit(limit).all()
    return candidates

@router.put("/{candidate_id}", response_model=schemas.Candidate)
def update_candidate(
    candidate_id: int,
    candidate_in: schemas.CandidateUpdate,
    db: Session = Depends(get_db)
) -> models.Candidate:
    """
    Update an existing candidate. Email cannot be updated via this endpoint.
    """
    db_candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    update_data = candidate_in.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
    
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int, 
    db: Session = Depends(get_db)
):
    logger.info(f"Attempting to delete candidate with ID: {candidate_id}")
    db_candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if db_candidate is None:
        logger.warning(f"Candidate with ID {candidate_id} not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Check for associated interviews
    associated_interviews_count = db.query(models.Interview).filter(models.Interview.candidate_id == candidate_id).count()
    if associated_interviews_count > 0:
        logger.warning(f"Attempt to delete candidate ID {candidate_id} failed: Candidate has {associated_interviews_count} associated interviews.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Cannot delete candidate: Candidate is associated with {associated_interviews_count} interview(s). Please delete or reassign them first."
        )

    try:
        db.delete(db_candidate)
        db.commit()
        logger.info(f"Successfully deleted candidate with ID: {candidate_id}")
    except Exception as e: # Catch potential commit errors, though the main one was caught by the check above
        db.rollback()
        logger.error(f"Error during deleting candidate ID {candidate_id} after checks: {e}", exc_info=True)
        # This might indicate other integrity issues or a race condition if checks passed but commit failed.
        # For now, a generic 500 is okay, but could be more specific if other constraints are known.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete candidate due to a database error: {str(e)}")
    
    return # Return None with 204 status

# New endpoint for creating candidate with resume upload
@router.post("/upload-resume/", response_model=schemas.Candidate, status_code=status.HTTP_201_CREATED)
async def create_candidate_with_resume_upload( # Made async to handle await for file.read()
    db: Session = Depends(get_db),
    name: str = Form(...),
    email: EmailStr = Form(...), # Use EmailStr for validation
    resume_file: UploadFile = File(...)
) -> models.Candidate:
    """
    Create new candidate with resume upload.
    The resume file will be parsed by an AI service to extract text.
    For .docx and .pdf, content will be extracted before sending to AI.
    """
    existing_candidate = db.query(models.Candidate).filter(models.Candidate.email == email).first()
    if existing_candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A candidate with this email already exists."
        )

    extracted_text_for_ai = ""
    filename_lower = resume_file.filename.lower()

    try:
        await resume_file.seek(0) # Ensure file pointer is at the beginning
        resume_content_bytes = await resume_file.read()
        await resume_file.seek(0) # Reset pointer again in case it's needed by a library using the file object directly

        if filename_lower.endswith(".txt"):
            try:
                extracted_text_for_ai = resume_content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    extracted_text_for_ai = resume_content_bytes.decode('latin-1')
                except UnicodeDecodeError as e:
                    # logger.error(f"Unicode decode error for {resume_file.filename}: {e}")
                    logger.error(f"Unicode decode error for {resume_file.filename}: {e}", exc_info=True)
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not decode .txt file '{resume_file.filename}\'. Please ensure it's UTF-8 or a common Western encoding.")
        
        elif filename_lower.endswith(".docx"):
            try:
                # python-docx needs a file-like object that supports seek, so use io.BytesIO
                file_stream = io.BytesIO(resume_content_bytes)
                doc = docx.Document(file_stream)
                extracted_text_for_ai = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                # logger.error(f"Error parsing DOCX file {resume_file.filename}: {e}", exc_info=True)
                logger.error(f"Error parsing DOCX file {resume_file.filename}: {e}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing .docx file '{resume_file.filename}': {str(e)}")

        elif filename_lower.endswith(".pdf"):
            try:
                # PyMuPDF (fitz) can open from bytes
                pdf_document = fitz.open(stream=resume_content_bytes, filetype="pdf")
                text_parts = []
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    text_parts.append(page.get_text())
                extracted_text_for_ai = "\n".join(text_parts)
                pdf_document.close()
            except Exception as e:
                # logger.error(f"Error parsing PDF file {resume_file.filename}: {e}", exc_info=True)
                logger.error(f"Error parsing PDF file {resume_file.filename}: {e}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing .pdf file '{resume_file.filename}': {str(e)}")
        else:
            # Fallback for unsupported types, or if you want to specifically disallow .doc
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported file type: {resume_file.filename}. Please upload .txt, .pdf, or .docx.")

        # Now, send the extracted text to the AI service if any text was extracted
        if extracted_text_for_ai:
            parsed_resume_text = await parse_resume(resume_text=extracted_text_for_ai)
        else:
            # This case might happen if a .txt was empty, or if a docx/pdf was empty or unparseable before exception
            parsed_resume_text = f"[File: {resume_file.filename}, Type: {resume_file.content_type} - No content extracted or file was empty.]"
            
    except HTTPException: # Re-raise HTTPExceptions directly that were raised above
        raise
    except Exception as e:
        # logger.error(f"General error processing resume file {resume_file.filename}: {e}", exc_info=True)
        logger.error(f"General error processing resume file {resume_file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the resume file '{resume_file.filename}': {str(e)}"
        )
    finally:
        await resume_file.close()

    db_candidate = models.Candidate(
        name=name,
        email=email,
        resume_text=parsed_resume_text # Store the AI parsed text
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate 