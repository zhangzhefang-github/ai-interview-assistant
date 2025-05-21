print("DEBUG_INTERVIEWS: interviews.py MODULE EXECUTION STARTED") # THIS IS A VERY TOP LEVEL PRINT
import logging
from typing import List, Any, Optional
import re # Added for robust question parsing
import json # Added for JSON parsing
import asyncio # For SSE streaming
import uuid # For generating unique task IDs
import time # Added for the minimal test SSE stream

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse # ADDED
from sqlalchemy.orm import Session, joinedload # Import joinedload
from sqlalchemy.ext.asyncio import AsyncSession # For async db sessions

from app.api.v1 import schemas # This now correctly refers to the schemas package
# from ..schemas import ag_ui_events # No longer needed, ag_ui_events are part of 'schemas' package
from app.db import models     # Import models
from app.db.session import get_db, get_async_db # <<< ENSURE get_async_db IS IMPORTED HERE
# We might need AI services later for question generation
from app.services.ai_services import generate_interview_questions, analyze_jd, parse_resume, generate_followup_questions_service, AIJsonParsingError # <<< ADDED generate_followup_questions_service
from app.utils.json_parser import extract_capability_assessment_json # Import the new parser
from app.services.ai_report_generator import generate_interview_report
from sqlalchemy import select # For SQLAlchemy 2.0 style queries if you use them
from sqlalchemy.sql import func # Added for SQLAlchemy functions
from jsonschema import validate, ValidationError

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
    questions = db_interview.questions
    
    # Add any additional logic like filtering or pagination if needed
    logger.debug(f"Interview {interview_id}: Fetched {len(questions)} questions from DB.")
    
    # Log the raw question data being returned
    logger.info(f"Interview {interview_id}: Returning {len(questions)} questions to frontend. Raw data: {questions}")
    
    return questions

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
async def generate_questions_for_interview_endpoint(
    interview_id: int, 
    db: Session = Depends(get_db)
) -> models.Interview:
    """
    Generates interview questions for a specific interview based on job description and candidate resume.
    """
    logger.info(f"Starting question generation for interview {interview_id}")
    
    # Get interview and validate
    db_interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if not db_interview:
        logger.warning(f"Interview {interview_id} not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Ensure job and candidate are loaded
    if not db_interview.job: 
        logger.debug(f"Lazy loading job for interview {interview_id}")
        db.refresh(db_interview, attribute_names=['job']) 
    if not db_interview.candidate:
        logger.debug(f"Lazy loading candidate for interview {interview_id}")
        db.refresh(db_interview, attribute_names=['candidate'])

    # Validate required data
    if not db_interview.job or not db_interview.job.description:
        logger.warning(f"Job description missing for interview {interview_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description (JD) not found for this interview.")
    if not db_interview.candidate or not db_interview.candidate.resume_text: 
        logger.warning(f"Candidate resume missing for interview {interview_id}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate resume text not found for this interview.")

    try:
        # Step 1: Analyze JD
        logger.info(f"Interview {interview_id}: Starting JD analysis")
        analyzed_jd_text = await analyze_jd(jd_text=db_interview.job.description)
        if analyzed_jd_text.startswith("Error:"):
            logger.error(f"AI service error analyzing JD for interview {interview_id}: {analyzed_jd_text}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI service failed to analyze JD: {analyzed_jd_text}")
        logger.info(f"Interview {interview_id}: JD analysis completed successfully")
        
        # Step 2: Parse Resume
        logger.info(f"Interview {interview_id}: Starting resume parsing")
        parsed_resume_text = await parse_resume(resume_text=db_interview.candidate.resume_text)
        if parsed_resume_text.startswith("Error:"):
            logger.error(f"AI service error parsing resume for interview {interview_id}: {parsed_resume_text}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI service failed to parse resume: {parsed_resume_text}")
        logger.info(f"Interview {interview_id}: Resume parsing completed successfully")

        # Step 3: Generate Questions
        logger.info(f"Interview {interview_id}: Starting question generation")
        generated_questions_text = await generate_interview_questions(
            analyzed_jd_info=analyzed_jd_text,
            structured_resume_info=parsed_resume_text
        )
        
        logger.info(f"Interview {interview_id}: ---- RAW LLM OUTPUT START ----")
        logger.info(generated_questions_text)
        logger.info(f"Interview {interview_id}: ---- RAW LLM OUTPUT END ---- (Length: {len(generated_questions_text)})" )

        # Attempt to extract JSON from markdown code block
        json_to_parse = generated_questions_text
        logger.info(f"Interview {interview_id}: Initial json_to_parse: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )

        match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", generated_questions_text, re.DOTALL)
        if match:
            json_to_parse = match.group(1)
            logger.info(f"Interview {interview_id}: Extracted JSON from markdown: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )
        else:
            logger.info(f"Interview {interview_id}: Regex did NOT match markdown block.")
            stripped_text = generated_questions_text.strip()
            if stripped_text.startswith("{") and stripped_text.endswith("}"):
                 json_to_parse = stripped_text
                 logger.info(f"Interview {interview_id}: Detected plain JSON: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )
            else:
                logger.info(f"Interview {interview_id}: No markdown or plain JSON detected, json_to_parse remains raw: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )
        
        # Process generated questions
        SCHEMA = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["questions"]
        }
        question_texts = []
        try:
            logger.info(f"Interview {interview_id}: Attempting json.loads on: '''{json_to_parse}'''")
            parsed = json.loads(json_to_parse) # Use json_to_parse here
            validate(instance=parsed, schema=SCHEMA)
            question_texts = [q.strip() for q in parsed["questions"] if isinstance(q, str) and q.strip()]
            logger.info(f"Interview {interview_id}: Parsed {len(question_texts)} questions from JSON object.")
        except Exception as e:
            logger.warning(f"Interview {interview_id}: JSON解析或schema校验失败. Reason: {e}", extra={"raw_output_type": type(generated_questions_text), "raw_output_len": len(generated_questions_text), "parsed_attempt_type": type(json_to_parse), "parsed_attempt_len": len(json_to_parse), "parsed_attempt_content": json_to_parse[:500] + "..." if len(json_to_parse) > 500 else json_to_parse})
            
            question_texts = [] # Ensure it's empty before fallback
            # Fallback logic: split the content that was attempted for JSON parsing (json_to_parse)
            raw_question_lines = [q.strip() for q in json_to_parse.split('\n') if q.strip()]
            
            # Filter out common JSON structural lines or markdown remnants from fallback
            for line in raw_question_lines:
                temp_line = line.strip()
                # More robustly skip JSON structural lines and markdown
                if temp_line in ["{", "}", "[", "]", "],", "```json", "```"] or temp_line.lower().startswith(('"questions":', 'questions:')):
                    continue
                
                # Remove typical list item prefixes (numbers, bullets) more carefully
                cleaned_line = re.sub(r"^\\s*([\\d\\.\\-\\\* 、>]+\\s*)+", "", line).strip()

                # Remove surrounding quotes if they are likely from JSON string representation
                if cleaned_line.startswith('"') and cleaned_line.endswith('"'):
                    cleaned_line = cleaned_line[1:-1].strip()
                # Remove trailing comma if it's likely from JSON array
                if cleaned_line.endswith(','):
                    cleaned_line = cleaned_line[:-1].strip()
                
                if cleaned_line: # Add if not empty after cleaning
                    question_texts.append(cleaned_line)
            logger.info(f"Interview {interview_id}: Fallback模式获得{len(question_texts)}个问题 after cleaning. Original lines: {len(raw_question_lines)}", extra={"cleaned_questions": question_texts})

        # Delete existing questions
        logger.debug(f"Interview {interview_id}: Deleting existing questions")
        db.query(models.Question).filter(models.Question.interview_id == interview_id).delete(synchronize_session=False)

        if not question_texts:
            logger.warning(f"Interview {interview_id}: AI generated an empty list of questions")
        else:
            # Add new questions
            logger.debug(f"Interview {interview_id}: Adding {len(question_texts)} new questions")
            for i, q_text in enumerate(question_texts):
                db_question = models.Question(
                    question_text=q_text, 
                    interview_id=db_interview.id,
                    order_num=i + 1
                )
                db.add(db_question)
        
        # Update interview status
        logger.debug(f"Interview {interview_id}: Updating status to QUESTIONS_GENERATED")
        db_interview.status = "QUESTIONS_GENERATED"
        db.add(db_interview)

        # Commit changes
        logger.debug(f"Interview {interview_id}: Committing changes to database")
        db.commit()
        db.refresh(db_interview)
        logger.info(f"Interview {interview_id}: Successfully generated {len(question_texts)} questions. Status updated to QUESTIONS_GENERATED")

    except HTTPException:
        logger.error(f"Interview {interview_id}: HTTP exception occurred", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Interview {interview_id}: Unexpected error during question generation: {e}", exc_info=True)
        db.rollback()
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
        db_report.source_dialogue = dialogue_for_report # ADDED
        db_report.updated_at = func.now() # Explicitly set for MariaDB/older MySQL if onupdate not reliable via ORM only on Base
    else:
        logger.info(f"Creating new report for interview ID: {interview_id}")
        db_report = models.Report(
            interview_id=interview_id, 
            generated_text=text_report_content, # Save the cleaned text
            source_dialogue=dialogue_for_report # ADDED
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

async def generate_question_events_stream(interview_id: int, db: Session, logger_instance: logging.Logger):
    """
    Async generator function that yields AG-UI events during the question generation process.
    """
    task_id = str(uuid.uuid4())
    logger_instance.info(f"Task {task_id}: Starting question generation stream for interview {interview_id}")
    await asyncio.sleep(0.01) # Ensure message is sent
    yield {
        "event": schemas.AgUiEventType.TASK_START.value,
        "data": json.dumps({"task_id": task_id, "message": "追问问题生成已开始。"})
    }

    try:
        # Simulate some delay or async operations if needed
        await asyncio.sleep(0.1)

        # Load interview with related data
        logger_instance.debug(f"Task {task_id}: Loading interview {interview_id} with related data")
        db_interview = db.query(models.Interview).options(
            joinedload(models.Interview.job),
            joinedload(models.Interview.candidate)
        ).filter(models.Interview.id == interview_id).first()

        if not db_interview:
            logger_instance.error(f"Task {task_id}: Interview {interview_id} not found")
            yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.ERROR, payload=schemas.AgUiErrorData(task_id=task_id, error_message=f"Interview {interview_id} not found.").model_dump()).to_sse_format()
            return

        yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.THOUGHT, payload=schemas.AgUiThoughtData(task_id=task_id, thought="Accessing job description and candidate resume...").model_dump()).to_sse_format()

        # Validate required data
        if not db_interview.job or not db_interview.job.description:
            logger_instance.error(f"Task {task_id}: Job description not found for interview {interview_id}")
            yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.ERROR, payload=schemas.AgUiErrorData(task_id=task_id, error_message="Job description not found.").model_dump()).to_sse_format()
            return
        if not db_interview.candidate or not db_interview.candidate.resume_text:
            logger_instance.error(f"Task {task_id}: Candidate resume not found for interview {interview_id}")
            yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.ERROR, payload=schemas.AgUiErrorData(task_id=task_id, error_message="Candidate resume not found.").model_dump()).to_sse_format()
            return

        # Stage 1: Analyze JD
        logger_instance.info(f"Task {task_id}: Starting JD analysis for interview {interview_id}")
        yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.THOUGHT, payload=schemas.AgUiThoughtData(task_id=task_id, thought="Analyzing job description...").model_dump()).to_sse_format()
        
        analyzed_jd_text = await analyze_jd(jd_text=db_interview.job.description)
        if analyzed_jd_text.startswith("Error:"):
            logger_instance.error(f"Task {task_id}: AI service failed to analyze JD for interview {interview_id}: {analyzed_jd_text}")
            yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.ERROR, payload=schemas.AgUiErrorData(task_id=task_id, error_message=f"AI service failed to analyze JD: {analyzed_jd_text}").model_dump()).to_sse_format()
            return
            
        # Yield thought with JD analysis preview
        jd_preview = (analyzed_jd_text[:100] + '...') if len(analyzed_jd_text) > 100 else analyzed_jd_text
        logger_instance.info(f"Task {task_id}: JD analysis completed for interview {interview_id}")
        yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.THOUGHT, payload=schemas.AgUiThoughtData(task_id=task_id, thought=f"JD analysis complete. Preview: {jd_preview}").model_dump()).to_sse_format()

        # Stage 2: Parse Resume
        logger_instance.info(f"Task {task_id}: Starting resume parsing for interview {interview_id}")
        yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.THOUGHT, payload=schemas.AgUiThoughtData(task_id=task_id, thought="Parsing candidate resume...").model_dump()).to_sse_format()
        
        parsed_resume_text = await parse_resume(resume_text=db_interview.candidate.resume_text)
        if parsed_resume_text.startswith("Error:"):
            logger_instance.error(f"Task {task_id}: AI service failed to parse resume for interview {interview_id}: {parsed_resume_text}")
            yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.ERROR, payload=schemas.AgUiErrorData(task_id=task_id, error_message=f"AI service failed to parse resume: {parsed_resume_text}").model_dump()).to_sse_format()
            return
            
        # Yield thought with resume parsing preview
        resume_preview = (parsed_resume_text[:100] + '...') if len(parsed_resume_text) > 100 else parsed_resume_text
        logger_instance.info(f"Task {task_id}: Resume parsing completed for interview {interview_id}")
        yield schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.THOUGHT, payload=schemas.AgUiThoughtData(task_id=task_id, thought=f"Resume parsing complete. Preview: {resume_preview}").model_dump()).to_sse_format()

        # Stage 3: Generate Questions
        logger_instance.info(f"Task {task_id}: Starting question generation for interview {interview_id}")
        generated_questions_text = await generate_interview_questions(
            analyzed_jd_info=analyzed_jd_text,
            structured_resume_info=parsed_resume_text
        )

        logger_instance.info(f"Task {task_id}: ---- RAW LLM OUTPUT START ----")
        logger_instance.info(generated_questions_text)
        logger.info(f"Task {task_id}: ---- RAW LLM OUTPUT END ---- (Length: {len(generated_questions_text)})" )

        # Attempt to extract JSON from markdown code block
        json_to_parse = generated_questions_text
        logger.info(f"Task {task_id}: Initial json_to_parse: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )

        match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", generated_questions_text, re.DOTALL)
        if match:
            json_to_parse = match.group(1)
            logger.info(f"Task {task_id}: Extracted JSON from markdown: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )
        else:
            logger.info(f"Task {task_id}: Regex did NOT match markdown block.")
            stripped_text = generated_questions_text.strip()
            if stripped_text.startswith("{") and stripped_text.endswith("}"):
                 json_to_parse = stripped_text
                 logger.info(f"Task {task_id}: Detected plain JSON: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )
            else:
                logger.info(f"Task {task_id}: No markdown or plain JSON detected, using raw output for parsing/fallback: '''{json_to_parse}''' (Length: {len(json_to_parse)})" )
        
        # Process generated questions
        SCHEMA = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["questions"]
        }
        question_texts = []
        try:
            logger.info(f"Task {task_id}: Attempting json.loads on: '''{json_to_parse}''' for interview {interview_id}.")
            parsed = json.loads(json_to_parse) # Use json_to_parse here
            validate(instance=parsed, schema=SCHEMA)
            question_texts = [q.strip() for q in parsed["questions"] if isinstance(q, str) and q.strip()]
            logger.info(f"Task {task_id}: Parsed {len(question_texts)} questions from JSON object for interview {interview_id}.")
        except Exception as e:
            logger.warning(f"Task {task_id}: JSON解析或schema校验失败 for interview {interview_id}. Reason: {e}", extra={"raw_output_type": type(generated_questions_text), "raw_output_len": len(generated_questions_text), "parsed_attempt_type": type(json_to_parse), "parsed_attempt_len": len(json_to_parse), "parsed_attempt_content": json_to_parse[:500] + "..." if len(json_to_parse) > 500 else json_to_parse})
            
            question_texts = [] # Ensure it's empty before fallback
            # Fallback logic: split the content that was attempted for JSON parsing (json_to_parse)
            raw_question_lines = [q.strip() for q in json_to_parse.split('\n') if q.strip()]
            
            # Filter out common JSON structural lines or markdown remnants from fallback
            for line in raw_question_lines:
                temp_line = line.strip()
                # More robustly skip JSON structural lines and markdown
                if temp_line in ["{", "}", "[", "]", "],", "```json", "```"] or temp_line.lower().startswith(('"questions":', 'questions:')):
                    continue
                
                # Remove typical list item prefixes (numbers, bullets) more carefully
                cleaned_line = re.sub(r"^\\s*([\\d\\.\\-\\\* 、>]+\\s*)+", "", line).strip()

                # Remove surrounding quotes if they are likely from JSON string representation
                if cleaned_line.startswith('"') and cleaned_line.endswith('"'):
                    cleaned_line = cleaned_line[1:-1].strip()
                # Remove trailing comma if it's likely from JSON array
                if cleaned_line.endswith(','):
                    cleaned_line = cleaned_line[:-1].strip()
                
                if cleaned_line: # Add if not empty after cleaning
                    question_texts.append(cleaned_line)
            logger.info(f"Task {task_id}: Fallback模式获得{len(question_texts)}个问题 for interview {interview_id} after cleaning. Original lines: {len(raw_question_lines)}", extra={"cleaned_questions": question_texts})
            
        # Proceed with DB operations and yielding events
        # Note: Using db.begin_nested() in an async function with a sync db session can be tricky.
        # FastAPI handles db session per request. If this causes issues, direct commit/rollback might be needed or pass an async session.
        # For now, assuming the existing structure with sync session in async endpoint handler context is managed by FastAPI.
        try: # Added try-finally for commit/rollback safety
            db.begin() # Explicit transaction start
            # Delete existing questions
            logger_instance.debug(f"Task {task_id}: Deleting existing questions for interview {interview_id}")
            db.query(models.Question).filter(models.Question.interview_id == interview_id).delete(synchronize_session=False)

            if not question_texts:
                logger_instance.warning(f"Task {task_id}: AI generated an empty list of questions for interview {interview_id}")
                db_interview.status = models.InterviewStatus.QUESTIONS_FAILED
            else:
                # Add new questions
                logger_instance.debug(f"Task {task_id}: Adding {len(question_texts)} new questions for interview {interview_id}")
                for i, q_text in enumerate(question_texts):
                    db_question = models.Question(
                        question_text=q_text,
                        interview_id=db_interview.id,
                        order_num=i + 1
                    )
                    db.add(db_question)
                    # Yield question generated event
                    yield schemas.AgUiSsePayload(
                        event_type=schemas.AgUiEventType.QUESTION_GENERATED,
                        payload=schemas.AgUiQuestionGeneratedData(
                            task_id=task_id,
                            question_text=q_text,
                            question_order=i+1,
                            total_questions=len(question_texts)
                        ).model_dump()
                    ).to_sse_format()
                db_interview.status = models.InterviewStatus.QUESTIONS_GENERATED
            
            # Update interview status
            logger_instance.debug(f"Task {task_id}: Updating interview status to {db_interview.status}")
            db.add(db_interview)
            db.commit()
        except Exception as commit_exc:
            logger_instance.error(f"Task {task_id}: Error during DB commit for interview {interview_id}: {commit_exc}", exc_info=True)
            db.rollback()
            raise # Re-raise the exception to be caught by the main try-except block
        finally:
            # The outer try/except handles the final rollback if necessary.
            # No specific db.close() here as FastAPI manages session lifecycle.
            pass
        
        db.refresh(db_interview)
        logger_instance.info(f"Task {task_id}: Successfully committed changes for interview {interview_id}. Final status: {db_interview.status}")

        # Prepare final questions list for task end event
        final_question_list_for_event = [{"text": q, "order": i+1} for i, q in enumerate(question_texts)]

        # Yield task end event
        yield schemas.AgUiSsePayload(
            event_type=schemas.AgUiEventType.TASK_END,
            payload=schemas.AgUiTaskEndData(
                task_id=task_id,
                status="success" if question_texts else "completed_with_no_questions",
                message=f"Generated {len(question_texts)} questions for interview {interview_id}.",
                final_questions=final_question_list_for_event
            ).model_dump()
        ).to_sse_format()
        logger_instance.info(f"Task {task_id}: Question generation stream for interview {interview_id} completed successfully")

    except Exception as e:
        logger_instance.error(f"Task {task_id}: Error during question generation stream for interview {interview_id}: {e}", exc_info=True)
        db.rollback()
        yield schemas.AgUiSsePayload(
            event_type=schemas.AgUiEventType.ERROR,
            payload=schemas.AgUiErrorData(
                task_id=task_id,
                error_message=f"An unexpected error occurred: {str(e)}"
            ).model_dump()
        ).to_sse_format()
    finally:
        logger_instance.debug(f"Task {task_id}: Closing stream for interview {interview_id}")


@router.post("/{interview_id}/generate-questions-stream", name="generate_questions_streaming")
async def generate_questions_for_interview_stream_endpoint( # Renamed to avoid conflict with the async generator
    interview_id: int,
    db: Session = Depends(get_db),
    # It's good practice to inject logger if it's used extensively inside the stream generator
    # logger_instance: logging.Logger = Depends(lambda: logging.getLogger(__name__)) # Example of logger injection
):
    # Use the module-level logger for the endpoint itself, pass to generator if needed.
    # The logger instance will be the one from the interviews.py module.
    return EventSourceResponse(
        generate_question_events_stream(interview_id=interview_id, db=db, logger_instance=logger)
    ) 

async def _minimal_test_sse_stream_impl(logger_instance: logging.Logger):
    logger_instance.info("Minimal Test SSE Stream: Generator started.")
    count = 0
    try:
        while True: # Keep sending indefinitely for testing
            count += 1
            event_data = {"count": count, "timestamp": time.time()}
            
            # Yield a PING-like event (or any custom event)
            sse_event_payload = schemas.AgUiSsePayload(
                event_type="PING_TEST", # Using a distinct event type
                payload=event_data
            )
            sse_formatted_event = sse_event_payload.to_sse_format()
            
            logger_instance.info(f"Minimal Test SSE Stream: Yielding event: {sse_formatted_event.strip()}")
            yield sse_formatted_event.encode('utf-8')
            
            # Add a small sleep to allow event loop to breathe and send data
            # Also acts as a periodic sender
            await asyncio.sleep(1) # Send an event every 1 second
            
    except asyncio.CancelledError:
        logger_instance.info("Minimal Test SSE Stream: Generator was cancelled (client disconnected).")
        raise
    except Exception as e:
        logger_instance.error(f"Minimal Test SSE Stream: Error in generator: {e}", exc_info=True)
        # Attempt to yield a final error to the client if possible
        try:
            error_payload = schemas.AgUiSsePayload(
                event_type=schemas.AgUiEventType.ERROR, 
                payload=schemas.AgUiErrorData(task_id="minimal_test_error", error_message=str(e)).model_dump()
            )
            yield error_payload.to_sse_format().encode('utf-8')
            await asyncio.sleep(0.001)
        except Exception as final_e:
            logger_instance.error(f"Minimal Test SSE Stream: Failed to yield final error event: {final_e}", exc_info=True)
        raise # Re-raise the original error
    finally:
        logger_instance.info("Minimal Test SSE Stream: Generator finishing.")


@router.api_route(
    "/test-sse-simple", # Using a new, simpler path for this test
    methods=["GET"], 
    summary="Minimal SSE endpoint for testing direct data streaming",
    tags=["Diagnostics"]
)
async def minimal_test_sse_endpoint(
    logger_instance: logging.Logger = Depends(lambda: logging.getLogger(__name__))
):
    logger_instance.info("Minimal Test SSE Endpoint: Endpoint called.")
    return EventSourceResponse(
        _minimal_test_sse_stream_impl(logger_instance=logger_instance)
    )

# --- Keep the original SSE endpoint but we will test the one above first ---

async def _generate_followup_events_stream_impl(
    interview_id: int,
    log_id: int,
    db: AsyncSession,
    logger_instance: logging.Logger
):
    """
    Core asynchronous generator implementation for followup questions SSE stream.
    Yields events for task start, thoughts, question chunks, full questions, and task end.
    """
    task_id = str(uuid.uuid4())
    logger_instance.info(f"Task {task_id}: Starting followup generation for interview_id={interview_id}, log_id={log_id}")

    try:
        # Yield task_start event
        yield {
            "event": schemas.AgUiEventType.TASK_START.value,
            "data": json.dumps({"task_id": task_id, "message": "追问问题生成已开始。"})
        }

        # Fetch the specific log entry
        log_entry_stmt = select(models.InterviewLog).where(models.InterviewLog.id == log_id, models.InterviewLog.interview_id == interview_id)
        log_entry_result = await db.execute(log_entry_stmt)
        db_log_entry = log_entry_result.scalar_one_or_none()

        if not db_log_entry:
            logger_instance.warning(f"Task {task_id}: InterviewLog with id {log_id} for interview {interview_id} not found.")
            yield {
                "event": schemas.AgUiEventType.ERROR.value,
                "data": json.dumps({"error": "Log entry not found", "details": f"InterviewLog id {log_id} not found."})
            }
            # Yield task_end event even on error, to signal completion of this attempt
            yield {
                "event": schemas.AgUiEventType.TASK_END.value,
                "data": json.dumps({"task_id": task_id, "success": False, "message": "Task failed: Log entry not found."})
            }
            await asyncio.sleep(0.1) # Recommended delay
            return

        # Corrected: Use speaker_role and compare with models.SpeakerRole enum member
        if not db_log_entry.speaker_role or db_log_entry.speaker_role != models.SpeakerRole.CANDIDATE:
            logger_instance.info(f"Task {task_id}: Log entry {log_id} is not a candidate utterance (speaker_role: {db_log_entry.speaker_role}). No followup needed.")
            yield {
                "event": schemas.AgUiEventType.TASK_END.value,
                "data": json.dumps({"task_id": task_id, "success": True, "message": "No followup needed for non-candidate utterance."})
            }
            await asyncio.sleep(0.1) # Recommended delay
            return
        
        # Corrected: Use full_dialogue_text instead of utterance_text
        candidate_answer = db_log_entry.full_dialogue_text 
        if not candidate_answer or not candidate_answer.strip():
            logger_instance.info(f"Task {task_id}: Candidate answer in log {log_id} is empty (full_dialogue_text). No followup needed.")
            yield {
                "event": schemas.AgUiEventType.TASK_END.value,
                "data": json.dumps({"task_id": task_id, "success": True, "message": "No followup needed for empty candidate answer."})
            }
            await asyncio.sleep(0.1) # Recommended delay
            return

        # Retrieve previous questions and context if necessary (simplified for now)
        # This would involve fetching earlier logs from the interview to understand the context of the candidate's answer.
        # For this example, let's assume we have the original question that led to this answer.
        # In a real scenario, you might need to fetch db_log_entry.parent_log_id or similar to get context.
        original_question_text = "(Context: Assume this was the preceding question related to the candidate's answer)"
        if db_log_entry.question_id:
            question_stmt = select(models.Question).where(models.Question.id == db_log_entry.question_id)
            question_result = await db.execute(question_stmt)
            db_question = question_result.scalar_one_or_none()
            if db_question:
                original_question_text = db_question.question_text
            else:
                logger_instance.warning(f"Task {task_id}: Original question with ID {db_log_entry.question_id} not found for log {log_id}.")
        else:
            logger_instance.info(f"Task {task_id}: Log entry {log_id} does not have an associated question_id. Context might be limited.")

        # Call the refactored service, ensuring all required arguments are passed.
        # analyzed_jd_info and structured_resume_info are not fetched here, passing empty strings.
        # These could be fetched from db_interview.job.analyzed_description and 
        # db_interview.candidate.structured_resume_info if the full interview object was loaded.
        async for event_data_dict in generate_followup_questions_service(
            original_question=original_question_text,
            candidate_answer=candidate_answer,
            task_id=task_id,
            logger_instance=logger_instance,
            analyzed_jd_info="", # Placeholder - fetch if needed for better followups
            structured_resume_info="" # Placeholder - fetch if needed for better followups
        ):
            # The service now yields dictionaries ready for EventSourceResponse
            yield event_data_dict 

        # After the service stream is exhausted, yield task_end
        logger_instance.info(f"Task {task_id}: Followup generation service stream completed.")
        yield {
            "event": schemas.AgUiEventType.TASK_END.value,
            "data": json.dumps({"task_id": task_id, "success": True, "message": "Followup question generation completed."})
        }
        await asyncio.sleep(0.1) # Recommended delay before the generator actually returns

    except AIJsonParsingError as e: # Specific error from the service
        logger_instance.error(f"Task {task_id}: AIJsonParsingError in followup generation: {e.message} - Invalid JSON: {e.invalid_json_string}", exc_info=True)
        yield {
            "event": schemas.AgUiEventType.ERROR.value,
            "data": json.dumps({"error": "AI Parsing Error", "details": e.message, "raw_ai_output": e.invalid_json_string})
        }
        yield {
            "event": schemas.AgUiEventType.TASK_END.value,
            "data": json.dumps({"task_id": task_id, "success": False, "message": f"Task failed: AI service parsing error - {e.message}"})
        }
        await asyncio.sleep(0.1) # Recommended delay
    except Exception as e:
        logger_instance.error(f"Task {task_id}: Unexpected error in followup generation stream: {str(e)}", exc_info=True)
        # Yield a general error event
        yield {
            "event": schemas.AgUiEventType.ERROR.value,
            "data": json.dumps({"error": "Internal Server Error", "details": str(e)})
        }
        # Yield task_end event to signal completion, even if it's an error state
        yield {
            "event": schemas.AgUiEventType.TASK_END.value,
            "data": json.dumps({"task_id": task_id, "success": False, "message": f"Task failed: Unexpected server error - {str(e)}"})
        }
        await asyncio.sleep(0.1) # Recommended delay
    finally:
        logger_instance.info(f"Task {task_id}: _generate_followup_events_stream_impl finished execution (reached finally block).")
        # Any final cleanup if necessary, though EventSourceResponse handles connection closing.


@router.api_route(
    "/{interview_id}/logs/{log_id}/generate-followup-stream",
    methods=["POST", "GET"],
    summary="Generate and stream followup questions based on a specific log entry (AG-UI)",
    tags=["Interview Management", "AG-UI"]
)
async def stream_followup_questions_events_endpoint(
    interview_id: int,
    log_id: int,
    db: AsyncSession = Depends(get_async_db),
    logger_instance: logging.Logger = Depends(lambda: logging.getLogger(__name__))
):
    logger_instance.info(f"Endpoint stream_followup_questions_events_endpoint called for interview {interview_id}, log {log_id} - USING EventSourceResponse") # Log change
    return EventSourceResponse( # MODIFIED
        _generate_followup_events_stream_impl(interview_id=interview_id, log_id=log_id, db=db, logger_instance=logger_instance)
    )

print("DEBUG_INTERVIEWS: interviews.py MODULE EXECUTION COMPLETED (if no errors before this)")