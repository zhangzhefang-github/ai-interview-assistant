print("DEBUG_INTERVIEWS: interviews.py MODULE EXECUTION STARTED") # THIS IS A VERY TOP LEVEL PRINT
import logging
from typing import List, Any, Optional
import re # Added for robust question parsing
import json # Added for JSON parsing

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload # Import joinedload

from app.api.v1 import schemas # Import schemas
from app.db import models     # Import models
from app.db.session import get_db
# We might need AI services later for question generation
from app.services.ai_services import generate_interview_questions, analyze_jd, parse_resume, generate_interview_report # Added analyze_jd, parse_resume, and generate_interview_report
from app.utils.json_parser import extract_capability_assessment_json # Import the new parser
from app.services.ai_report_generator import generate_interview_report
from sqlalchemy import select # For SQLAlchemy 2.0 style queries if you use them
from sqlalchemy.sql import func # Added for SQLAlchemy functions

router = APIRouter()
logger = logging.getLogger(__name__) # Get logger early for use anywhere

# Keep only this one route for now to test if the module loads completely
@router.get("/{interview_id}/questions", response_model=List[schemas.Question])
def get_questions_for_interview(
    interview_id: int,
    db: Session = Depends(get_db)
) -> List[models.Question]:
    """
    Retrieves all questions associated with a specific interview.
    """
    logger.debug(f"get_questions_for_interview called for interview_id: {interview_id}")
    db_interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not db_interview:
        logger.warning(f"Interview not found for id: {interview_id} in get_questions_for_interview")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    logger.debug(f"Returning {len(db_interview.questions)} questions for interview_id: {interview_id}")
    return db_interview.questions

# logger.debug("Temporarily commenting out other routes to isolate the issue...")

@router.post("/", response_model=schemas.Interview, status_code=status.HTTP_201_CREATED)
def create_interview(
    interview_in: schemas.InterviewCreate, 
    db: Session = Depends(get_db)
) -> models.Interview:
    # Placeholder implementation - replace with actual logic
    # Ensure job_id and candidate_id exist
    job = db.query(models.Job).filter(models.Job.id == interview_in.job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with id {interview_in.job_id} not found")
    
    candidate = db.query(models.Candidate).filter(models.Candidate.id == interview_in.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate with id {interview_in.candidate_id} not found")
        
    db_interview = models.Interview(**interview_in.model_dump())
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    logger.info(f"Interview created with id {db_interview.id}")
    return db_interview

@router.get("/{interview_id}", response_model=schemas.Interview)
def read_interview_by_id(
    interview_id: int, 
    db: Session = Depends(get_db)
) -> models.Interview:
    db_interview = (
        db.query(models.Interview)
        .options(joinedload(models.Interview.job), joinedload(models.Interview.candidate))
        .filter(models.Interview.id == interview_id)
        .first()
    )
    if db_interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return db_interview

@router.get("/", response_model=List[schemas.Interview])
def read_interviews(
    skip: int = 0, 
    limit: int = 100, 
    job_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> List[models.Interview]:
    # Placeholder implementation - replace with actual logic
    query = db.query(models.Interview)
    if job_id is not None:
        query = query.filter(models.Interview.job_id == job_id)
    if candidate_id is not None:
        query = query.filter(models.Interview.candidate_id == candidate_id)
    
    interviews = query.offset(skip).limit(limit).all()
    return interviews

@router.put("/{interview_id}", response_model=schemas.Interview)
def update_interview(
    interview_id: int, 
    interview_in: schemas.InterviewUpdate, 
    db: Session = Depends(get_db)
) -> models.Interview:
    logger.info(f"Update_interview called for ID: {interview_id} with input data: {interview_in.model_dump()}")

    db_interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if db_interview is None:
        logger.warning(f"Interview not found for ID: {interview_id} during update attempt.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    logger.debug(f"Interview ID {interview_id} - Before update: status='{db_interview.status}'")

    update_data = interview_in.model_dump(exclude_unset=True)
    logger.info(f"Interview ID {interview_id} - Parsed update_data: {update_data}")

    for field, value in update_data.items():
        logger.debug(f"Interview ID {interview_id} - Setting field '{field}' to '{value}'")
        setattr(db_interview, field, value)
    
    logger.debug(f"Interview ID {interview_id} - After setattr, before commit: status='{db_interview.status}'")
        
    try:
        db.add(db_interview)
        db.commit()
        logger.info(f"Interview ID {interview_id} - db.commit() executed successfully.")
    except Exception as e:
        logger.error(f"Interview ID {interview_id} - Error during db.commit(): {str(e)} --- repr(e): {repr(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database commit error: {str(e)}")

    try:
        db.refresh(db_interview)
        logger.info(f"Interview ID {interview_id} - db.refresh() executed successfully.")
    except Exception as e:
        logger.error(f"Interview ID {interview_id} - Error during db.refresh(): {e}", exc_info=True)
        # If refresh fails, the commit likely succeeded.

    logger.info(f"Interview ID {interview_id} - After refresh: status='{db_interview.status}'")
    logger.info(f"Update_interview for ID: {interview_id} completed. Returning updated interview.")
    return db_interview

@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interview(
    interview_id: int, 
    db: Session = Depends(get_db)
):
    # Placeholder implementation - replace with actual logic
    db_interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if db_interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    db.delete(db_interview)
    db.commit()
    return

@router.post("/{interview_id}/generate-questions", response_model=schemas.InterviewWithQuestions, status_code=status.HTTP_201_CREATED)
async def generate_questions_for_interview_endpoint( # Renamed to avoid conflict
    interview_id: int, 
    db: Session = Depends(get_db)
) -> models.Interview: # Changed response model to Interview for now, assuming questions are part of it
    # Placeholder implementation - replace with actual logic
    db_interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not db_interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Ensure job and candidate are loaded for JD and resume text
    # FastAPI/SQLAlchemy might lazy load these, but explicit refresh can ensure they are available
    if not db_interview.job: 
        db.refresh(db_interview, attribute_names=['job']) 
    if not db_interview.candidate:
        db.refresh(db_interview, attribute_names=['candidate'])

    if not db_interview.job or not db_interview.job.description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description (JD) not found for this interview.")
    if not db_interview.candidate or not db_interview.candidate.resume_text: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate resume text not found for this interview.")

    try:
        logger.debug(f"Interview {interview_id}: Analyzing JD...")
        analyzed_jd_text = await analyze_jd(jd_text=db_interview.job.description)
        if analyzed_jd_text.startswith("Error:"):
            logger.error(f"AI service error analyzing JD for interview {interview_id}: {analyzed_jd_text}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI service failed to analyze JD: {analyzed_jd_text}")
        
        logger.debug(f"Interview {interview_id}: Parsing resume...")
        parsed_resume_text = await parse_resume(resume_text=db_interview.candidate.resume_text)
        if parsed_resume_text.startswith("Error:"):
            logger.error(f"AI service error parsing resume for interview {interview_id}: {parsed_resume_text}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI service failed to parse resume: {parsed_resume_text}")

        logger.debug(f"Interview {interview_id}: Generating questions...")
        generated_questions_str = await generate_interview_questions(
            analyzed_jd_info=analyzed_jd_text,
            structured_resume_info=parsed_resume_text
        )
        
        if generated_questions_str.startswith("Error:"):
            logger.error(f"AI service error generating questions for interview {interview_id}: {generated_questions_str}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI service failed to generate questions: {generated_questions_str}")

        # Assuming questions are returned as a string, each question on a new line
        # And prompts are updated to ensure this format without numbering.
        raw_question_lines = [q.strip() for q in generated_questions_str.split('\n') if q.strip()]
        
        question_texts = []
        for line in raw_question_lines:
            # Try to remove common leading list markers (e.g., "1. ", "- ", "* ")
            cleaned_line = re.sub(r"^\s*([\d\*\-\.]+\s*)+", "", line).strip()
            if cleaned_line: # Ensure the line is not empty after cleaning
                question_texts.append(cleaned_line)
        
        # Delete existing questions for this interview first
        db.query(models.Question).filter(models.Question.interview_id == interview_id).delete(synchronize_session=False)
        # synchronize_session=False is often recommended for bulk deletes before adding new related items
        # However, for smaller numbers or simplicity, default (usually 'evaluate') might be fine.
        # Let's commit the delete separately to be clean, or ensure the subsequent add/commit covers it.
        # db.commit() # Commit deletion before adding new ones

        if not question_texts:
            logger.warning(f"AI generated an empty list of questions for interview {interview_id}.")
            # No new questions to add, but update status if appropriate.
        else:
            for i, q_text in enumerate(question_texts):
                db_question = models.Question(
                    question_text=q_text, 
                    interview_id=db_interview.id,
                    order_num=i + 1  # Assign order_num
                )
                db.add(db_question)
        
        # Update interview status
        db_interview.status = "QUESTIONS_GENERATED" # New status
        db.add(db_interview) # Add the interview again to mark it as dirty for update

        db.commit()
        db.refresh(db_interview) # Refresh to get newly added questions and updated status
        logger.info(f"Generated {len(question_texts)} questions for interview {interview_id}. Status updated to QUESTIONS_GENERATED.")

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Unexpected error during question generation for interview {interview_id}: {e}", exc_info=True)
        db.rollback() # Rollback in case of other errors during DB operations or AI calls
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")

    return db_interview

@router.post("/{interview_id}/logs", response_model=schemas.InterviewLog, status_code=status.HTTP_201_CREATED)
def create_interview_log_entry(
    interview_id: int,
    log_in: schemas.InterviewLogCreate,
    db: Session = Depends(get_db)
) -> models.InterviewLog:
    db_interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not db_interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Potentially validate question_id if provided
    if log_in.question_id:
        db_question = db.query(models.Question).filter(models.Question.id == log_in.question_id, models.Question.interview_id == interview_id).first()
        if not db_question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                                detail=f"Question with id {log_in.question_id} not found for this interview.")
        # If question_text_snapshot is not provided but question_id is, populate it from the question
        if not log_in.question_text_snapshot and db_question:
            log_in.question_text_snapshot = db_question.question_text

    if not log_in.question_text_snapshot and not log_in.question_id:
         # Or decide if question_text_snapshot can be truly optional
        logger.warning(f"Creating InterviewLog for interview {interview_id} without explicit question text or ID.")


    db_log = models.InterviewLog(**log_in.model_dump(), interview_id=interview_id)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    logger.info(f"InterviewLog entry created with id {db_log.id} for interview {interview_id}")
    return db_log

@router.get("/{interview_id}/logs", response_model=List[schemas.InterviewLog])
def get_interview_log_entries(
    interview_id: int,
    db: Session = Depends(get_db)
) -> List[models.InterviewLog]:
    db_interview = db.query(models.Interview).options(joinedload(models.Interview.logs)).filter(models.Interview.id == interview_id).first()
    if not db_interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    # Logs are already ordered by order_num due to the relationship's order_by config
    return db_interview.logs

@router.post("/{interview_id}/generate-report", response_model=schemas.Report)
async def trigger_generate_interview_report(
    interview_id: int,
    db: Session = Depends(get_db)
) -> Any: # Changed to Any temporarily as db_report is a SQLAlchemy model
    logger.info(f"Triggering report generation for interview ID: {interview_id}")
    # Use joinedload to fetch related job, candidate, and logs efficiently
    db_interview = (
        db.query(models.Interview)
        .options(
            joinedload(models.Interview.job),
            joinedload(models.Interview.candidate),
            joinedload(models.Interview.logs) # Eagerly load logs
        )
        .filter(models.Interview.id == interview_id)
        .first()
    )

    if not db_interview:
        logger.warning(f"Interview not found for ID: {interview_id} when generating report.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if not db_interview.job or not db_interview.job.description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description not available for this interview.")
    if not db_interview.candidate or not db_interview.candidate.resume_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate resume not available for this interview.")

    # --- Construct dialogue string from structured logs ---
    dialogue_parts = []
    if db_interview.logs: # Check if logs exist and are loaded
        # Logs should be ordered by order_num due to relationship config
        for i, log_entry in enumerate(db_interview.logs):
            question_text = log_entry.question_text_snapshot or "(Ad-hoc Question)" 
            answer_text = log_entry.full_dialogue_text or "(No answer recorded)"
            dialogue_parts.append(f"Q{i+1}: {question_text}\nA{i+1}: {answer_text}")
        dialogue_for_report = "\n\n".join(dialogue_parts) # Assign to dialogue_for_report
        logger.info(f"Using structured logs for report generation for interview {interview_id}. Dialogue length: {len(dialogue_for_report)}")
    elif db_interview.conversation_log: # Fallback to old field if no structured logs (should be phased out)
        logger.warning(f"Interview {interview_id}: No structured logs found. Falling back to conversation_log field for report generation.")
        # Ensure conversation_log is not None or empty before assigning
        if not db_interview.conversation_log.strip(): # Check if it's empty or just whitespace
            logger.error(f"Interview {interview_id}: Fallback conversation_log is empty. Cannot generate report.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid interview conversation log found (fallback is empty) to generate a report.")
        dialogue_for_report = db_interview.conversation_log
    else:
        logger.error(f"Interview {interview_id}: No interview logs (structured or fallback) found. Cannot generate report.")
        # Initialize dialogue_for_report to an empty string or handle appropriately if this path means error
        dialogue_for_report = "" # Initialize to prevent UnboundLocalError before raising
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid interview conversation log found to generate report.")
    # ---

    if not dialogue_for_report.strip():
        logger.error(f"Interview {interview_id}: Final dialogue content for report is empty or whitespace. Cannot generate report.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview dialogue content is empty. Cannot generate report.")

    logger.info(f"Calling AI service to generate report for interview ID: {interview_id} using processed dialogue input.")
    try:
        # generate_interview_report is now an async function, so await is needed.
        generated_report_text = await generate_interview_report(
            conversation_log_str=dialogue_for_report,
            job_description=db_interview.job.description,
            candidate_resume=db_interview.candidate.resume_text
            # llm_model_name and temperature will use defaults from the service
        )
        logger.info(f"Successfully generated interview report text for interview {interview_id}.")

    except Exception as e:
        logger.error(f"AI service failed to generate report for interview {interview_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI service failed: {str(e)}")

    # --- Process and save the report --- 
    radar_scores_json = None
    text_report_content = generated_report_text

    # Attempt to extract JSON and then remove it from the text report
    try:
        extracted_json_data = extract_capability_assessment_json(generated_report_text)
        if extracted_json_data:
            radar_scores_json = extracted_json_data # This is already a dict
            # Remove the JSON block from the text report for cleaner display
            # This regex should match the ```json ... ``` block
            json_block_pattern = r"```json\s*\{\s*\"CANDIDATE_CAPABILITY_ASSESSMENT_JSON\"\s*:\s*\{.*?\}\s*\}\s*```"
            text_report_content = re.sub(json_block_pattern, "", generated_report_text, flags=re.DOTALL).strip()
            logger.info(f"Successfully parsed radar_data for interview {interview_id}: {radar_scores_json}")
            logger.info(f"Removed JSON block from text_report_content for interview {interview_id}.")
        else:
            logger.warning(f"Could not extract CANDIDATE_CAPABILITY_ASSESSMENT_JSON from report for interview {interview_id}. Radar data will be empty.")
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError parsing radar_data for interview {interview_id}: {e}. Raw text was: {generated_report_text[:500]}...", exc_info=True)
        # Keep text_report_content as is, radar_scores_json remains None
    except Exception as e: # Catch any other unexpected error during extraction/removal
        logger.error(f"Unexpected error extracting/removing JSON for interview {interview_id}: {e}. Raw text was: {generated_report_text[:500]}...", exc_info=True)

    # Update the Interview model with the radar_data
    if radar_scores_json:
        db_interview.radar_data = radar_scores_json # SQLAlchemy handles JSON conversion
    else:
        db_interview.radar_data = None # Ensure it's cleared if not found

    # Check if a report already exists for this interview
    db_report = db.query(models.Report).filter(models.Report.interview_id == interview_id).first()

    if db_report:
        logger.info(f"Updating existing report for interview ID: {interview_id}")
        db_report.generated_text = text_report_content # Save the cleaned text
        db_report.updated_at = func.now() # Explicitly set for MariaDB/older MySQL if onupdate not reliable via ORM only on Base
    else:
        logger.info(f"Creating new report for interview ID: {interview_id}")
        db_report = models.Report(
            interview_id=interview_id, 
            generated_text=text_report_content # Save the cleaned text
        )
        db.add(db_report)
    
    db_interview.status = models.InterviewStatus.REPORT_GENERATED
    db.add(db_interview) # Ensure interview is also updated (status and radar_data)

    try:
        db.commit()
        db.refresh(db_report) # Refresh to get ID, created_at, updated_at
        db.refresh(db_interview) # Refresh interview to get updated status and radar data in the object
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing report or interview update for interview {interview_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save report to database.")

    logger.info(f"Report generated and saved successfully for interview ID: {interview_id}")
    return db_report

# Diagnostic log: To be executed when this module is imported.
logger.debug("---- Routes registered in app.api.v1.endpoints.interviews.py router (minimal) ----")
if "router" in locals() and hasattr(router, "routes"):
    for r_idx, r in enumerate(router.routes):
        if hasattr(r, "path"):
            logger.debug(f"  [{r_idx}] Path: {r.path}, Name: {r.name}, Methods: {getattr(r, 'methods', 'N/A')}")
        else:
            logger.debug(f"  [{r_idx}] Route object: {r}")
else:
    logger.warning("  'router' object not found or has no 'routes' attribute at the time of printing in (minimal) interviews.py.")
logger.debug("------------------------------------------------------------------------------------") 