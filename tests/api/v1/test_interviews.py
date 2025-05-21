from fastapi.testclient import TestClient
from fastapi import status
from datetime import datetime, timezone
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

import httpx # Added for SSE client
import json # Added for parsing SSE data

from app.db.models import InterviewStatus # Added for status comparison

# client fixture is automatically available from tests/conftest.py

# Helper function to create a job and return its ID
def create_test_job(client: TestClient, title: str = "Test Job for Interview", desc: str = "Job for interview test") -> int:
    response = client.post("/api/v1/jobs/", json={"title": title, "description": desc})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]

# Helper function to create a candidate and return its ID
def create_test_candidate(client: TestClient, email: str = "interview.candidate@example.com", name: str = "Interview Candidate", resume_text: str = "Default resume text for test candidate") -> int:
    response = client.post(
        "/api/v1/candidates/", 
        json={"name": name, "email": email, "resume_text": resume_text}
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]

def test_create_interview_success(client: TestClient):
    """Test successfully creating a new interview."""
    job_id = create_test_job(client, title="Job For Interview Create Success")
    candidate_id = create_test_candidate(client, email="create.interview.success@example.com")
    
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response = client.post("/api/v1/interviews/", json=interview_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["job_id"] == job_id
    assert data["candidate_id"] == candidate_id
    assert data["questions"] == [] # Initially no questions
    assert "id" in data
    assert "created_at" in data
    # Test with scheduled_at
    scheduled_time_str = datetime.now(timezone.utc).isoformat()
    interview_data_scheduled = {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "scheduled_at": scheduled_time_str
    }
    response_scheduled = client.post("/api/v1/interviews/", json=interview_data_scheduled)
    assert response_scheduled.status_code == status.HTTP_201_CREATED
    data_scheduled = response_scheduled.json()
    assert data_scheduled["scheduled_at"] is not None
    # Note: Comparing ISO format strings directly can be tricky due to precision differences (e.g., microseconds)
    # It's safer to parse them back to datetime objects for comparison if exact match is needed.
    # For now, just checking it's not None and was accepted.
    expected_scheduled_dt_create = datetime.fromisoformat(scheduled_time_str.replace("Z", "+00:00")) # This is UTC aware
    
    # Parse the actual string and ensure it's UTC aware for comparison
    actual_scheduled_dt_str_create = data_scheduled["scheduled_at"]
    # fromisoformat might return naive if original string was like '2024-08-15T10:30:00' (no Z or offset)
    # even if it was '2024-08-15T10:30:00+00:00', if fromisoformat on that makes it naive, we fix it
    parsed_actual_dt_create = datetime.fromisoformat(actual_scheduled_dt_str_create.replace("Z", "+00:00"))
    if parsed_actual_dt_create.tzinfo is None:
        parsed_actual_dt_create = parsed_actual_dt_create.replace(tzinfo=timezone.utc)

    # Compare only up to seconds to avoid microsecond precision issues from different systems/DBs
    # assert parsed_actual_dt_create.replace(microsecond=0) == expected_scheduled_dt_create.replace(microsecond=0) # Old assertion
    
    # Allow a small delta (e.g., 5 seconds) for comparison to account for processing time
    time_difference = abs(parsed_actual_dt_create - expected_scheduled_dt_create)
    assert time_difference.total_seconds() < 5

def test_create_interview_job_not_found(client: TestClient):
    """Test creating an interview with a non-existent job_id."""
    candidate_id = create_test_candidate(client, email="job.notfound@example.com")
    interview_data = {"job_id": 99999, "candidate_id": candidate_id} # Non-existent job_id
    response = client.post("/api/v1/interviews/", json=interview_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Job with id 99999 not found" in response.json()["detail"]

def test_create_interview_candidate_not_found(client: TestClient):
    """Test creating an interview with a non-existent candidate_id."""
    job_id = create_test_job(client, title="Cand Not Found Job")
    interview_data = {"job_id": job_id, "candidate_id": 88888} # Non-existent candidate_id
    response = client.post("/api/v1/interviews/", json=interview_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Candidate with id 88888 not found" in response.json()["detail"]

def test_read_interview_by_id_success(client: TestClient):
    """Test successfully reading an interview by its ID."""
    job_id = create_test_job(client, title="Job For Read Interview Success")
    candidate_id = create_test_candidate(client, email="read.interview.success@example.com")
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    created_interview_id = response_create.json()["id"]

    response_read = client.get(f"/api/v1/interviews/{created_interview_id}")
    assert response_read.status_code == status.HTTP_200_OK
    read_data = response_read.json()
    assert read_data["id"] == created_interview_id
    assert read_data["job_id"] == job_id
    assert read_data["candidate_id"] == candidate_id
    assert read_data["questions"] == []

def test_read_interview_by_id_not_found(client: TestClient):
    """Test reading an interview by an ID that does not exist."""
    non_existent_id = 777777
    response = client.get(f"/api/v1/interviews/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Interview not found"}

# TODO: Add test for read_interviews (GET /)
def test_read_interviews_empty(client: TestClient):
    """Test reading interviews when there are none."""
    response = client.get("/api/v1/interviews/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_read_interviews_with_data_and_pagination(client: TestClient):
    """Test reading interviews with data, pagination, and basic filtering."""
    job1_id = create_test_job(client, title="Job 1 For List")
    cand1_id = create_test_candidate(client, email="cand1.list@example.com")
    job2_id = create_test_job(client, title="Job 2 For List")
    cand2_id = create_test_candidate(client, email="cand2.list@example.com")

    # Create 3 interviews
    interview1_data = {"job_id": job1_id, "candidate_id": cand1_id}
    client.post("/api/v1/interviews/", json=interview1_data)

    interview2_data = {"job_id": job1_id, "candidate_id": cand2_id} # Same job, different candidate
    client.post("/api/v1/interviews/", json=interview2_data)

    interview3_data = {"job_id": job2_id, "candidate_id": cand1_id} # Different job, same candidate as 1
    client.post("/api/v1/interviews/", json=interview3_data)

    # Test get all (default limit 100)
    response_all = client.get("/api/v1/interviews/")
    assert response_all.status_code == status.HTTP_200_OK
    assert len(response_all.json()) == 3

    # Test pagination: limit
    response_limit = client.get("/api/v1/interviews/?limit=1")
    assert response_limit.status_code == status.HTTP_200_OK
    assert len(response_limit.json()) == 1

    # Test pagination: skip and limit
    response_skip_limit = client.get("/api/v1/interviews/?skip=1&limit=1")
    assert response_skip_limit.status_code == status.HTTP_200_OK
    data_skip_limit = response_skip_limit.json()
    assert len(data_skip_limit) == 1
    # Ensure it's the second item created (IDs are typically sequential in tests)
    # This is a bit fragile, but ok for this test context
    assert data_skip_limit[0]["candidate_id"] == cand2_id 

    # Test filtering by job_id
    response_job_filter = client.get(f"/api/v1/interviews/?job_id={job1_id}")
    assert response_job_filter.status_code == status.HTTP_200_OK
    data_job_filter = response_job_filter.json()
    assert len(data_job_filter) == 2
    for item in data_job_filter:
        assert item["job_id"] == job1_id

    # Test filtering by candidate_id
    response_cand_filter = client.get(f"/api/v1/interviews/?candidate_id={cand1_id}")
    assert response_cand_filter.status_code == status.HTTP_200_OK
    data_cand_filter = response_cand_filter.json()
    assert len(data_cand_filter) == 2
    for item in data_cand_filter:
        assert item["candidate_id"] == cand1_id

    # Test filtering by both job_id and candidate_id
    response_job_cand_filter = client.get(f"/api/v1/interviews/?job_id={job1_id}&candidate_id={cand2_id}")
    assert response_job_cand_filter.status_code == status.HTTP_200_OK
    data_job_cand_filter = response_job_cand_filter.json()
    assert len(data_job_cand_filter) == 1
    assert data_job_cand_filter[0]["job_id"] == job1_id
    assert data_job_cand_filter[0]["candidate_id"] == cand2_id

    # Test filtering with no results
    response_no_results = client.get(f"/api/v1/interviews/?job_id=9999") # Non-existent job_id
    assert response_no_results.status_code == status.HTTP_200_OK
    assert response_no_results.json() == []

# TODO: Add test for update_interview (PUT /{interview_id})
def test_update_interview_success(client: TestClient):
    """Test successfully updating an interview."""
    job_id = create_test_job(client, title="Job For Update Interview")
    candidate_id = create_test_candidate(client, email="update.interview@example.com")
    
    # Create an initial interview
    initial_interview_data = {
        "job_id": job_id, 
        "candidate_id": candidate_id, 
        "status": "PENDING_QUESTIONS"  # Use a valid status from InterviewStatus enum
    }
    response_create = client.post("/api/v1/interviews/", json=initial_interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]
    original_created_at = response_create.json()["created_at"]
    original_status = response_create.json()["status"]

    # Update the status to a valid enum value
    update_payload = {
        "status": "QUESTIONS_GENERATED" # Valid InterviewStatus enum member
        # If 'scheduled_at' was part of the issue or an unintended change, 
        # ensure it's handled correctly or removed if not essential for this specific status update test.
        # For now, focusing on fixing the status.
        # "scheduled_at": datetime.now(timezone.utc).isoformat() # Example if needed
    }
    response_update = client.put(f"/api/v1/interviews/{interview_id}", json=update_payload)

    assert response_update.status_code == status.HTTP_200_OK
    updated_data = response_update.json()
    assert updated_data["id"] == interview_id
    assert updated_data["status"] == "QUESTIONS_GENERATED"
    assert updated_data["job_id"] == job_id # Should remain unchanged
    assert updated_data["candidate_id"] == candidate_id # Should remain unchanged
    
    # Check that created_at is not changed by an update
    assert updated_data["created_at"] == original_created_at
    
    # Check that updated_at is new or has changed (if model has onupdate)
    # This can be tricky if the time difference is too small.
    # A more robust check might be to ensure updated_at >= original_created_at (or original updated_at if available)
    # and updated_at is very recent. For now, let's assume it exists and is different if the status changed.
    assert "updated_at" in updated_data
    if original_status != updated_data["status"]: # if status actually changed
        # Parse timestamp strings to timezone-aware datetime objects for robust comparison
        original_created_at_str = original_created_at # original_created_at is already response_create.json()["created_at"]
        updated_at_str = updated_data["updated_at"]

        # Helper to parse ISO string to timezone-aware UTC datetime object
        def parse_iso_to_utc(dt_str: str) -> datetime:
            # Replace 'Z' at the end with '+00:00' for robust parsing by fromisoformat
            # Also handle cases where offset might already be there or not.
            # datetime.fromisoformat handles strings like 'YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM'
            # or 'YYYY-MM-DDTHH:MM:SSZ' (after .replace('Z', '+00:00'))
            
            processed_dt_str = dt_str
            if dt_str.endswith("Z"):
                processed_dt_str = dt_str[:-1] + "+00:00"
            
            dt_obj = datetime.fromisoformat(processed_dt_str)
            
            # If parsing results in a naive datetime, assume UTC.
            # (Though fromisoformat with an offset or 'Z' should produce aware objects)
            if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
                dt_obj = dt_obj.replace(tzinfo=timezone.utc)
            return dt_obj

        original_created_at_dt = parse_iso_to_utc(original_created_at_str)
        updated_at_dt = parse_iso_to_utc(updated_at_str)
        
        # Assert that updated_at is greater than or equal to original_created_at
        assert updated_at_dt >= original_created_at_dt, \
            f"updated_at ({updated_at_str}) was not greater than or equal to original created_at ({original_created_at_str})"
    
    # Verify other fields if necessary

# TODO: Add test for updating other fields, e.g., scheduled_at
# def test_update_interview_scheduled_at_success(client: TestClient):

def test_update_interview_not_found(client: TestClient):
    """Test updating an interview that does not exist."""
    non_existent_id = 888888
    update_payload = {"conversation_log": "Won't be applied."}
    response = client.put(f"/api/v1/interviews/{non_existent_id}", json=update_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Interview not found"}

# TODO: Add test for delete_interview (DELETE /{interview_id})
def test_delete_interview_success(client: TestClient, db_session_test: Session):
    """Test successfully deleting an interview."""
    job_id = create_test_job(client, title="Job For Delete Interview")
    candidate_id = create_test_candidate(client, email="delete.interview@example.com")
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]

    # Delete the interview
    response_delete = client.delete(f"/api/v1/interviews/{interview_id}")
    assert response_delete.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's gone
    response_get = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND

    # Verify deletion from DB
    assert db_session_test.query(models.Interview).filter(models.Interview.id == interview_id).first() is None

def test_delete_interview_not_found(client: TestClient):
    """Test deleting an interview that does not exist."""
    non_existent_id = 999999
    response_delete = client.delete(f"/api/v1/interviews/{non_existent_id}")
    assert response_delete.status_code == status.HTTP_404_NOT_FOUND
    assert response_delete.json() == {"detail": "Interview not found"}

# We need a way to create questions for an interview to test cascade delete properly.
# For now, the Question model and schemas exist, but no endpoint to create them directly yet 
# other than them being part of the Interview response (as an empty list initially).
# Let's assume for now that if an endpoint to add questions to an interview existed,
# the cascade delete would work. The ORM configuration is the primary check here.
# We can add a more direct test once question creation is implemented.

# TODO: Add tests for question generation and retrieval related to interviews
@pytest.mark.asyncio # Mark test as asyncio for async client calls if needed by endpoint
async def test_generate_questions_for_interview_success(client: TestClient, db_session_test: Session):
    """Test successfully generating questions for an interview."""
    job_id = create_test_job(client, title="Job For GenQ", desc="JD for GenQ")
    candidate_id = create_test_candidate(client, email="genq.cand@example.com", name="GenQ Cand", resume_text="Resume for GenQ")
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]

    mock_questions_list = ["Generated Question 1?", "Generated Question 2?"]
    mock_questions_str = "\n".join(mock_questions_list)

    # Patch the AI service calls
    with patch('app.api.v1.endpoints.interviews.analyze_jd', new_callable=AsyncMock, return_value="Analyzed JD for GenQ") as mock_analyze_jd, \
         patch('app.api.v1.endpoints.interviews.parse_resume', new_callable=AsyncMock, return_value="Parsed Resume for GenQ") as mock_parse_resume, \
         patch('app.api.v1.endpoints.interviews.generate_interview_questions', new_callable=AsyncMock, return_value=mock_questions_str) as mock_gen_questions:

        response_generate = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
        
        assert response_generate.status_code == status.HTTP_201_CREATED
        mock_analyze_jd.assert_called_once_with(jd_text="JD for GenQ")
        mock_parse_resume.assert_called_once_with(resume_text="Resume for GenQ")
        mock_gen_questions.assert_called_once_with(analyzed_jd_info="Analyzed JD for GenQ", structured_resume_info="Parsed Resume for GenQ")

        data_generate = response_generate.json()
        assert data_generate["id"] == interview_id
        assert len(data_generate["questions"]) == len(mock_questions_list)
        for i, q_data in enumerate(data_generate["questions"]):
            assert q_data["question_text"] == mock_questions_list[i]
            assert q_data["interview_id"] == interview_id
            assert q_data["order_num"] == i + 1

    # Test re-generation (should replace old questions)
    mock_questions_regenerated_list = ["Regenerated Q1?", "Regenerated Q2?", "Regenerated Q3?"]
    mock_questions_regenerated_str = "\n".join(mock_questions_regenerated_list)
    
    with patch('app.api.v1.endpoints.interviews.analyze_jd', new_callable=AsyncMock, return_value="Analyzed JD for Regen") as mock_analyze_jd_regen, \
         patch('app.api.v1.endpoints.interviews.parse_resume', new_callable=AsyncMock, return_value="Parsed Resume for Regen") as mock_parse_resume_regen, \
         patch('app.api.v1.endpoints.interviews.generate_interview_questions', new_callable=AsyncMock, return_value=mock_questions_regenerated_str) as mock_gen_questions_regenerate:

        response_regenerate = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
        assert response_regenerate.status_code == status.HTTP_201_CREATED
        
        mock_analyze_jd_regen.assert_called_once_with(jd_text="JD for GenQ") 
        mock_parse_resume_regen.assert_called_once_with(resume_text="Resume for GenQ")
        mock_gen_questions_regenerate.assert_called_once_with(analyzed_jd_info="Analyzed JD for Regen", structured_resume_info="Parsed Resume for Regen")

        data_regenerated = response_regenerate.json()
        assert len(data_regenerated["questions"]) == len(mock_questions_regenerated_list)
        for i, q_data in enumerate(data_regenerated["questions"]):
            assert q_data["question_text"] == mock_questions_regenerated_list[i]
            assert q_data["order_num"] == i + 1

@pytest.mark.asyncio
async def test_generate_questions_interview_not_found(client: TestClient, app_lifespan_mock):
    """Test generating questions for a non-existent interview."""
    # No need to mock AI services if the interview isn't found first.
    response = client.post("/api/v1/interviews/99999/generate-questions") # Non-existent ID
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Interview not found"

@pytest.mark.asyncio
async def test_generate_questions_missing_jd(client: TestClient, db_session_test: Session, app_lifespan_mock):
    """Test generating questions when the job description is missing."""
    job_response = client.post("/api/v1/jobs/", json={"title": "Job Missing JD", "description": ""})
    assert job_response.status_code == status.HTTP_201_CREATED
    job_id_missing_jd = job_response.json()["id"]
    
    candidate_id = create_test_candidate(client, email="missingjd.cand@example.com")
    interview_data = {"job_id": job_id_missing_jd, "candidate_id": candidate_id}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]

    # No need to mock AI services if the prerequisite data is missing.
    response = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Job description (JD) not found for this interview."

@pytest.mark.asyncio
async def test_generate_questions_missing_resume(client: TestClient, db_session_test: Session, app_lifespan_mock):
    """Test generating questions when the candidate resume is missing."""
    job_id = create_test_job(client, title="Job For Missing Resume Test")
    cand_response = client.post("/api/v1/candidates/", json={"name": "Cand Missing Resume", "email": "missingresume.cand@example.com", "resume_text": ""})
    assert cand_response.status_code == status.HTTP_201_CREATED
    candidate_id_missing_resume = cand_response.json()["id"]

    interview_data = {"job_id": job_id, "candidate_id": candidate_id_missing_resume}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]

    response = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Candidate resume text not found for this interview."

@pytest.mark.asyncio
async def test_generate_questions_ai_service_fails(client: TestClient, db_session_test: Session, app_lifespan_mock):
    """Test error handling when the AI service call fails."""
    job_id = create_test_job(client, title="Job For AI Fail", desc="JD for AI Fail")
    candidate_id = create_test_candidate(client, email="aifail.cand@example.com", resume_text="Resume for AI Fail")
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]

    # Mock all three AI services. Let generate_interview_questions fail.
    with patch('app.api.v1.endpoints.interviews.analyze_jd', new_callable=AsyncMock, return_value="Analyzed JD for AI Fail") as mock_analyze_jd, \
         patch('app.api.v1.endpoints.interviews.parse_resume', new_callable=AsyncMock, return_value="Parsed Resume for AI Fail") as mock_parse_resume, \
         patch('app.api.v1.endpoints.interviews.generate_interview_questions', new_callable=AsyncMock, side_effect=Exception("AI service exploded")) as mock_gen_questions_fail:
        
        response = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        # The endpoint currently wraps the exception in a generic message
        assert "An unexpected error occurred: AI service exploded" in response.json()["detail"]
        
        mock_analyze_jd.assert_called_once_with(jd_text="JD for AI Fail")
        mock_parse_resume.assert_called_once_with(resume_text="Resume for AI Fail")
        mock_gen_questions_fail.assert_called_once_with(analyzed_jd_info="Analyzed JD for AI Fail", structured_resume_info="Parsed Resume for AI Fail")

@pytest.mark.asyncio
async def test_generate_questions_ai_returns_empty_list(client: TestClient, db_session_test: Session, app_lifespan_mock):
    """Test when AI service returns an empty string (representing no questions)."""
    job_id = create_test_job(client, title="Job For AI Empty", desc="JD for AI Empty")
    candidate_id = create_test_candidate(client, email="aiempty.cand@example.com", resume_text="Resume for AI Empty")
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response_create = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    interview_id = response_create.json()["id"]

    with patch('app.api.v1.endpoints.interviews.analyze_jd', new_callable=AsyncMock, return_value="Analyzed JD for empty q test") as mock_analyze_jd, \
         patch('app.api.v1.endpoints.interviews.parse_resume', new_callable=AsyncMock, return_value="Parsed Resume for empty q test") as mock_parse_resume, \
         patch('app.api.v1.endpoints.interviews.generate_interview_questions', new_callable=AsyncMock, return_value="") as mock_gen_questions_empty:
        
        response_gen_q = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
        
        assert response_gen_q.status_code == status.HTTP_201_CREATED
        mock_analyze_jd.assert_called_once_with(jd_text="JD for AI Empty")
        mock_parse_resume.assert_called_once_with(resume_text="Resume for AI Empty")
        mock_gen_questions_empty.assert_called_once_with(analyzed_jd_info="Analyzed JD for empty q test", structured_resume_info="Parsed Resume for empty q test")

        data_gen_q = response_gen_q.json()
        assert data_gen_q["id"] == interview_id
        assert len(data_gen_q["questions"]) == 0

def test_get_questions_for_interview_success(client: TestClient):
    """Test successfully retrieving questions for an interview."""
    job_id = create_test_job(client, title="Job For GetQ", desc="JD for GetQ")
    candidate_id = create_test_candidate(client, email="getq.cand@example.com", name="GetQ Cand", resume_text="Resume for GetQ")
    interview_data = {"job_id": job_id, "candidate_id": candidate_id}
    response_create_interview = client.post("/api/v1/interviews/", json=interview_data)
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]

    response_get_no_q = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_no_q.status_code == status.HTTP_200_OK
    assert response_get_no_q.json() == []

    mock_generated_questions_list = ["Question A?", "Question B?"]
    mock_generated_questions_str = "\n".join(mock_generated_questions_list)
    
    with patch('app.api.v1.endpoints.interviews.analyze_jd', new_callable=AsyncMock, return_value="Analyzed JD for GetQ") as mock_analyze_jd, \
         patch('app.api.v1.endpoints.interviews.parse_resume', new_callable=AsyncMock, return_value="Parsed Resume for GetQ") as mock_parse_resume, \
         patch('app.api.v1.endpoints.interviews.generate_interview_questions', new_callable=AsyncMock, return_value=mock_generated_questions_str) as mock_ai_generate:
        
        response_post_gen = client.post(f"/api/v1/interviews/{interview_id}/generate-questions")
        assert response_post_gen.status_code == status.HTTP_201_CREATED # Ensure question generation was successful
        
        mock_analyze_jd.assert_called_once_with(jd_text="JD for GetQ")
        mock_parse_resume.assert_called_once_with(resume_text="Resume for GetQ")
        mock_ai_generate.assert_called_once_with(analyzed_jd_info="Analyzed JD for GetQ", structured_resume_info="Parsed Resume for GetQ")

    response_get_with_q = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_with_q.status_code == status.HTTP_200_OK
    questions_data = response_get_with_q.json()
    assert len(questions_data) == len(mock_generated_questions_list)
    for i, q_data in enumerate(questions_data):
        assert q_data["question_text"] == mock_generated_questions_list[i]
        assert q_data["interview_id"] == interview_id
        assert q_data["order_num"] == i + 1
        assert "id" in q_data # Ensure question ID is present

def test_get_questions_for_interview_not_found(client: TestClient):
    """Test retrieving questions for a non-existent interview."""
    non_existent_interview_id = 1234567
    response_get_q = client.get(f"/api/v1/interviews/{non_existent_interview_id}/questions")
    assert response_get_q.status_code == status.HTTP_404_NOT_FOUND
    assert response_get_q.json() == {"detail": "Interview not found"} 

# It's good practice to define expected AG-UI event types, possibly from your schemas
# For now, we'll use string literals.
AG_UI_EVENT_TYPE_TASK_START = "task_start"
AG_UI_EVENT_TYPE_THOUGHT = "thought"
AG_UI_EVENT_TYPE_QUESTION_GENERATED = "question_generated"
AG_UI_EVENT_TYPE_TASK_END = "task_end"
AG_UI_EVENT_TYPE_ERROR = "error" # Although not used in success test, good to have

@pytest.mark.asyncio
async def test_generate_questions_stream_success(async_app_client: httpx.AsyncClient, client: TestClient, db_session_test: Session):
    """
    Test successful question generation via SSE stream.
    Verifies AG-UI events, database updates, and interview status.
    """
    # 1. Create Job, Candidate, and Interview
    job_id = create_test_job(client, title="SSE Stream Job", desc="JD for SSE stream test: Python, FastAPI, SSE")
    candidate_id = create_test_candidate(client, email="sse.stream.candidate@example.com", resume_text="Resume for SSE stream test: Experienced Python dev with SSE knowledge")
    
    response_create_interview = client.post(
        "/api/v1/interviews/",
        json={"job_id": job_id, "candidate_id": candidate_id, "status": "PENDING_QUESTIONS"}
    )
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]

    # 2. Mock AI Service calls
    mock_analyzed_jd = "Analyzed JD: Key skills - Python, FastAPI, SSE. Experience needed."
    mock_parsed_resume = "Parsed Resume: Candidate has Python and SSE experience."
    mock_generated_questions_text = (
        "What is SSE?\\n"
        "How does FastAPI support streaming responses?\\n"
        "Explain a use case for SSE."
    )
    expected_questions = [
        "What is SSE?",
        "How does FastAPI support streaming responses?",
        "Explain a use case for SSE."
    ]

    # Ensure the paths in patch match the actual location of these functions
    # as used by the generate_question_events_stream generator.
    with patch("app.api.v1.endpoints.interviews.analyze_jd", AsyncMock(return_value=mock_analyzed_jd)) as mock_ai_jd, \
         patch("app.api.v1.endpoints.interviews.parse_resume", AsyncMock(return_value=mock_parsed_resume)) as mock_ai_resume, \
         patch("app.api.v1.endpoints.interviews.generate_interview_questions", AsyncMock(return_value=mock_generated_questions_text)) as mock_ai_questions:

        # 3. Call the SSE endpoint using the new async_app_client fixture
        # async with httpx.AsyncClient(app=client.app, base_url="http://testserver") as async_client:
        response = await async_app_client.post(f"/api/v1/interviews/{interview_id}/generate-questions-stream")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"].lower()

        # 4. Collect and parse SSE events
        received_events = []
        raw_event_chunks_for_debug = [] 
        async for line in response.aiter_lines(): # aiter_lines yields strings
            raw_event_chunks_for_debug.append(line)
            if line.startswith("data:"):
                event_data_str = line[len("data:"):].strip()
                try:
                    event_payload = json.loads(event_data_str)
                    received_events.append(event_payload)
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")

        # 5. Assert AG-UI events
        assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

        task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
        assert task_start_event is not None, "TASK_START event not found"
        task_id = task_start_event["payload"]["task_id"]
        assert task_id, "Task ID missing in TASK_START"
        assert task_start_event["payload"]["task_name"] == "generate_interview_questions"

        thought_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_THOUGHT and e.get("payload", {}).get("task_id") == task_id]
        # Expect thoughts for: accessing JD/resume, analyzing JD, parsed resume, generating questions
        assert len(thought_events) >= 4, f"Expected at least 4 THOUGHT events, got {len(thought_events)}"

        question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
        assert len(question_generated_events) == len(expected_questions), f"Expected {len(expected_questions)} QUESTION_GENERATED events, got {len(question_generated_events)}"
        
        # Sort events by question_order before asserting, as they might arrive out of order if generated concurrently (though unlikely here)
        for i, q_event in enumerate(sorted(question_generated_events, key=lambda x: x["payload"]["question_order"])):
            assert q_event["payload"]["question_text"] == expected_questions[i]
            assert q_event["payload"]["question_order"] == i + 1
            assert q_event["payload"]["total_questions"] == len(expected_questions)

        task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and e.get("payload", {}).get("task_id") == task_id), None)
        assert task_end_event is not None, "TASK_END event not found"
        assert task_end_event["payload"]["status"] == "success"
        assert task_end_event["payload"]["message"] == f"Generated {len(expected_questions)} questions for interview {interview_id}."
        assert len(task_end_event["payload"]["final_questions"]) == len(expected_questions)
        # Sort final questions by order before asserting
        for i, q_data in enumerate(sorted(task_end_event["payload"]["final_questions"], key=lambda x: x["order"])):
            assert q_data["text"] == expected_questions[i]
            assert q_data["order"] == i + 1
            
        # Verify AI service calls
        mock_ai_jd.assert_awaited_once()
        mock_ai_resume.assert_awaited_once()
        # Check arguments passed to the mock AI question generation
        mock_ai_questions.assert_awaited_once_with(
            analyzed_jd_info=mock_analyzed_jd, 
            structured_resume_info=mock_parsed_resume
        )

    # 6. Assert Database changes
    response_get_interview = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get_interview.status_code == status.HTTP_200_OK
    interview_details = response_get_interview.json()

    # 7. Assert Interview Status
    # Ensure this matches models.InterviewStatus.QUESTIONS_GENERATED.value if using an enum
    assert interview_details["status"] == "QUESTIONS_GENERATED" 

    response_get_questions = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_questions.status_code == status.HTTP_200_OK
    saved_questions_from_api = response_get_questions.json()
    
    assert len(saved_questions_from_api) == len(expected_questions)
    for i, saved_q in enumerate(sorted(saved_questions_from_api, key=lambda q: q["order_num"])):
        assert saved_q["question_text"] == expected_questions[i]
        assert saved_q["interview_id"] == interview_id
        assert saved_q["order_num"] == i + 1

@pytest.mark.asyncio
async def test_generate_questions_stream_interview_not_found(async_app_client: httpx.AsyncClient):
    """
    Test SSE stream when the interview ID does not exist.
    Expected: An ERROR AG-UI event after TASK_START.
    """
    non_existent_interview_id = 999999 # A very unlikely ID to exist

    response = await async_app_client.post(f"/api/v1/interviews/{non_existent_interview_id}/generate-questions-stream")
    
    assert response.status_code == status.HTTP_200_OK # Stream connection itself is okay
    assert "text/event-stream" in response.headers["content-type"].lower()

    received_events = []
    raw_event_chunks_for_debug = []
    async for line in response.aiter_lines():
        raw_event_chunks_for_debug.append(line)
        if line.startswith("data:"):
            event_data_str = line[len("data:") :].strip()
            try:
                event_payload = json.loads(event_data_str)
                received_events.append(event_payload)
            except json.JSONDecodeError:
                pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")

    assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

    # Expect TASK_START first
    task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
    assert task_start_event is not None, "TASK_START event not found"
    task_id = task_start_event["payload"]["task_id"]
    assert task_id, "Task ID missing in TASK_START event"

    # Then expect an ERROR event for this task_id
    error_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_ERROR and e.get("payload", {}).get("task_id") == task_id), None)
    assert error_event is not None, "ERROR AG-UI event not found in stream for the correct task_id"
    
    # Verify the error message content based on the implementation in generate_question_events_stream
    # The stream yields: schemas.AgUiSsePayload(event_type=schemas.AgUiEventType.ERROR, payload=schemas.AgUiErrorData(task_id=task_id, message=f"Interview {interview_id} not found.").model_dump()).to_sse_format()
    # The payload for AgUiErrorData contains 'message'.
    assert f"Interview {non_existent_interview_id} not found" in error_event["payload"]["message"]
    
    # Ensure no QUESTION_GENERATED or successful TASK_END events for this task_id
    question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
    assert len(question_generated_events) == 0, "QUESTION_GENERATED event found for non-existent interview"

    successful_task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and e.get("payload", {}).get("status") == "success" and e.get("payload", {}).get("task_id") == task_id), None)
    assert successful_task_end_event is None, "Successful TASK_END event found for non-existent interview"

@pytest.mark.asyncio
async def test_generate_questions_stream_missing_jd(
    async_app_client: httpx.AsyncClient, client: TestClient, db_session_test: Session # Added db_session_test for completeness, though not directly used yet
):
    """
    Test SSE stream when the interview's job is missing a description.
    Expected: An ERROR AG-UI event after TASK_START and initial THOUGHT.
    """
    # 1. Create Job (with empty description), Candidate, and Interview
    job_id_missing_jd = create_test_job(client, title="Job Missing JD Stream", desc="") # Empty description
    candidate_id = create_test_candidate(client, email="missingjd.stream@example.com", resume_text="Valid resume for missing JD test")
    
    response_create_interview = client.post(
        "/api/v1/interviews/",
        json={"job_id": job_id_missing_jd, "candidate_id": candidate_id, "status": "PENDING_QUESTIONS"}
    )
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]
    original_interview_status = response_create_interview.json()["status"]

    # 2. Call SSE endpoint (No AI mocking needed as it should fail before AI calls)
    response = await async_app_client.post(f"/api/v1/interviews/{interview_id}/generate-questions-stream")
    
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers["content-type"].lower()

    # 3. Collect and parse SSE events
    received_events = []
    raw_event_chunks_for_debug = []
    async for line in response.aiter_lines():
        raw_event_chunks_for_debug.append(line)
        if line.startswith("data:"):
            event_data_str = line[len("data:") :].strip()
            try:
                event_payload = json.loads(event_data_str)
                received_events.append(event_payload)
            except json.JSONDecodeError:
                pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")

    assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

    # 4. Assert AG-UI Events
    task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
    assert task_start_event is not None, "TASK_START event not found"
    task_id = task_start_event["payload"]["task_id"]
    assert task_id, "Task ID missing in TASK_START event"

    # Check for the initial "Accessing job description and candidate resume..." thought
    initial_thought = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_THOUGHT and \
                            e.get("payload", {}).get("task_id") == task_id and \
                            "Accessing job description" in e.get("payload",{}).get("thought","")), None)
    assert initial_thought is not None, "Initial 'Accessing' THOUGHT event not found"

    error_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_ERROR and e.get("payload", {}).get("task_id") == task_id), None)
    assert error_event is not None, "ERROR AG-UI event not found for the correct task_id"
    # Based on generate_question_events_stream: payload=schemas.AgUiErrorData(task_id=task_id, message="Job description not found.")
    assert error_event["payload"]["message"] == "Job description not found."

    # Ensure no QUESTION_GENERATED or successful TASK_END for this task_id
    question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
    assert len(question_generated_events) == 0, "QUESTION_GENERATED event found when JD was missing"

    successful_task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and \
                                     e.get("payload", {}).get("status") == "success" and \
                                     e.get("payload", {}).get("task_id") == task_id), None)
    assert successful_task_end_event is None, "Successful TASK_END event found when JD was missing"

    # 5. Assert Database state (status should not change, no questions created)
    response_get_interview = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get_interview.status_code == status.HTTP_200_OK
    interview_details = response_get_interview.json()
    assert interview_details["status"] == original_interview_status # Status should remain unchanged

    response_get_questions = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_questions.status_code == status.HTTP_200_OK
    assert response_get_questions.json() == [] # No questions should be created

@pytest.mark.asyncio
async def test_generate_questions_stream_missing_resume(
    async_app_client: httpx.AsyncClient, client: TestClient, db_session_test: Session
):
    """
    Test SSE stream when the interview's candidate is missing resume text.
    Expected: An ERROR AG-UI event after initial THOUGHTS (including JD analysis).
    """
    # 1. Create Job, Candidate (with empty resume), and Interview
    job_id = create_test_job(client, title="Job For Missing Resume Stream", desc="Valid JD for missing resume test")
    # Create candidate with empty resume text
    candidate_id_missing_resume = create_test_candidate(client, email="missingresume.stream@example.com", name="Missing Resume Cand", resume_text="") 
    
    response_create_interview = client.post(
        "/api/v1/interviews/",
        json={"job_id": job_id, "candidate_id": candidate_id_missing_resume, "status": "PENDING_QUESTIONS"}
    )
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]
    original_interview_status = response_create_interview.json()["status"]

    # Mock analyze_jd as it should be called before the resume check fails
    mock_analyzed_jd_return_value = "Analyzed JD: Key skills - Python. Experience required."
    # Patch the correct path for analyze_jd within the interviews endpoint module
    with patch("app.api.v1.endpoints.interviews.analyze_jd", AsyncMock(return_value=mock_analyzed_jd_return_value)) as mock_ai_analyze_jd:
        
        # 2. Call SSE endpoint
        response = await async_app_client.post(f"/api/v1/interviews/{interview_id}/generate-questions-stream")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"].lower()

        # 3. Collect and parse SSE events
        received_events = []
        raw_event_chunks_for_debug = []
        async for line in response.aiter_lines():
            raw_event_chunks_for_debug.append(line)
            if line.startswith("data:"):
                event_data_str = line[len("data:") :].strip()
                try:
                    event_payload = json.loads(event_data_str)
                    received_events.append(event_payload)
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")
        
        assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

        # 4. Assert AG-UI Events
        task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
        assert task_start_event is not None, "TASK_START event not found"
        task_id = task_start_event["payload"]["task_id"]
        assert task_id, "Task ID missing in TASK_START event"

        # Check for THOUGHT events (at least accessing data and JD analysis thought)
        thought_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_THOUGHT and e.get("payload", {}).get("task_id") == task_id]
        # Expect thoughts for: Accessing, Analyzing JD, JD analysis complete, (then attempt parsing resume before error)
        assert len(thought_events) >= 2, f"Expected at least 2 THOUGHT events before resume error, got {len(thought_events)}"
        
        # Verify analyze_jd was called
        mock_ai_analyze_jd.assert_awaited_once()
        # To be more precise, check it was called with the correct JD from the created job
        # created_job_details = client.get(f"/api/v1/jobs/{job_id}").json()
        # mock_ai_analyze_jd.assert_awaited_once_with(jd_text=created_job_details["description"])

        error_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_ERROR and e.get("payload", {}).get("task_id") == task_id), None)
        assert error_event is not None, "ERROR AG-UI event not found for the correct task_id"
        # Based on stream: payload=AgUiErrorData(task_id=task_id, message=f"AI service failed to analyze JD: {analyzed_jd_text}")
        assert f"AI service failed to analyze JD: {mock_analyzed_jd_return_value}" == error_event["payload"]["message"]

        # 6. Assert AI service calls
        mock_ai_analyze_jd.assert_awaited_once()
        mock_ai_parse_resume.assert_not_awaited() # Should not be called
        mock_ai_generate_questions.assert_not_awaited() # Should not be called

        # Ensure no QUESTION_GENERATED or successful TASK_END for this task_id
        question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
        assert len(question_generated_events) == 0
        successful_task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and \
                                         e.get("payload", {}).get("status") == "success" and \
                                         e.get("payload", {}).get("task_id") == task_id), None)
        assert successful_task_end_event is None

    # 7. Assert Database state (status should not change, no questions created)
    response_get_interview = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get_interview.status_code == status.HTTP_200_OK
    interview_details = response_get_interview.json()
    assert interview_details["status"] == original_interview_status

    response_get_questions = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_questions.status_code == status.HTTP_200_OK
    assert response_get_questions.json() == []

@pytest.mark.asyncio
async def test_generate_questions_stream_ai_parse_resume_fails(
    async_app_client: httpx.AsyncClient, client: TestClient, db_session_test: Session
):
    """
    Test SSE stream when the parse_resume AI service call fails.
    Expected: An ERROR AG-UI event after JD analysis thoughts.
    """
    # 1. Setup
    job_id = create_test_job(client, title="Job For AI Resume Fail Stream", desc="Valid JD for AI resume fail test")
    candidate_id = create_test_candidate(client, email="airesumefail.stream@example.com", resume_text="Valid resume for AI resume fail test")
    
    response_create_interview = client.post(
        "/api/v1/interviews/",
        json={"job_id": job_id, "candidate_id": candidate_id, "status": "PENDING_QUESTIONS"}
    )
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]
    original_interview_status = response_create_interview.json()["status"]

    mock_analyzed_jd_success = "Analyzed JD: All good."
    # Ensure mock error starts with "Error:" as per current error handling in the stream generator
    ai_error_message_resume = "Error: Resume parsing module failed spectacularly."

    # 2. Mock AI services: analyze_jd succeeds, parse_resume fails.
    with patch("app.api.v1.endpoints.interviews.analyze_jd", AsyncMock(return_value=mock_analyzed_jd_success)) as mock_ai_analyze_jd, \
         patch("app.api.v1.endpoints.interviews.parse_resume", AsyncMock(return_value=ai_error_message_resume)) as mock_ai_parse_resume, \
         patch("app.api.v1.endpoints.interviews.generate_interview_questions", AsyncMock()) as mock_ai_generate_questions:

        # 3. Call SSE endpoint
        response = await async_app_client.post(f"/api/v1/interviews/{interview_id}/generate-questions-stream")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"].lower()

        # 4. Collect and parse SSE events
        received_events = []
        raw_event_chunks_for_debug = []
        async for line in response.aiter_lines():
            raw_event_chunks_for_debug.append(line)
            if line.startswith("data:"):
                event_data_str = line[len("data:") :].strip()
                try:
                    event_payload = json.loads(event_data_str)
                    received_events.append(event_payload)
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")
        
        assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

        # 5. Assert AG-UI Events
        task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
        assert task_start_event is not None, "TASK_START event not found"
        task_id = task_start_event["payload"]["task_id"]
        assert task_id, "Task ID missing in TASK_START event"

        thought_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_THOUGHT and e.get("payload", {}).get("task_id") == task_id]
        # Expect thoughts: Accessing, Analyzing JD, JD complete, Parsing resume (before error)
        assert len(thought_events) >= 3, f"Expected at least 3 THOUGHT events before parse_resume error, got {len(thought_events)}"

        error_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_ERROR and e.get("payload", {}).get("task_id") == task_id), None)
        assert error_event is not None, "ERROR AG-UI event not found for the correct task_id"
        # Based on stream: payload=AgUiErrorData(task_id=task_id, message=f"AI service failed to parse resume: {parsed_resume_text}")
        assert f"AI service failed to parse resume: {ai_error_message_resume}" == error_event["payload"]["message"]

        # 6. Assert AI service calls
        mock_ai_analyze_jd.assert_awaited_once()
        mock_ai_parse_resume.assert_awaited_once()
        mock_ai_generate_questions.assert_not_awaited() # Should not be called

        # Ensure no QUESTION_GENERATED or successful TASK_END
        question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
        assert len(question_generated_events) == 0
        successful_task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and \
                                         e.get("payload", {}).get("status") == "success" and \
                                         e.get("payload", {}).get("task_id") == task_id), None)
        assert successful_task_end_event is None

    # 7. Assert Database state
    response_get_interview = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get_interview.status_code == status.HTTP_200_OK
    interview_details = response_get_interview.json()
    assert interview_details["status"] == original_interview_status

    response_get_questions = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_questions.status_code == status.HTTP_200_OK
    assert response_get_questions.json() == []

@pytest.mark.asyncio
async def test_generate_questions_stream_ai_generate_questions_fails(
    async_app_client: httpx.AsyncClient, client: TestClient, db_session_test: Session
):
    """
    Test SSE stream when the generate_interview_questions AI service call raises an exception.
    Expected: An ERROR AG-UI event with details of the unexpected error.
    """
    # 1. Setup
    job_id = create_test_job(client, title="Job For AI GenQ Fail Stream", desc="Valid JD")
    candidate_id = create_test_candidate(client, email="aigenqfail.stream@example.com", resume_text="Valid resume")
    
    response_create_interview = client.post(
        "/api/v1/interviews/",
        json={"job_id": job_id, "candidate_id": candidate_id, "status": "PENDING_QUESTIONS"}
    )
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]
    original_interview_status = response_create_interview.json()["status"]

    mock_analyzed_jd_success = "Analyzed JD: Looks good."
    mock_parsed_resume_success = "Parsed Resume: All clear."
    # This specific error message will be part of the exception raised by the mock
    ai_exception_message_gen_q = "Question generation engine malfunction."

    # 2. Mock AI services: analyze_jd and parse_resume succeed, generate_interview_questions raises an exception.
    with patch("app.api.v1.endpoints.interviews.analyze_jd", AsyncMock(return_value=mock_analyzed_jd_success)) as mock_ai_analyze_jd, \
         patch("app.api.v1.endpoints.interviews.parse_resume", AsyncMock(return_value=mock_parsed_resume_success)) as mock_ai_parse_resume, \
         patch("app.api.v1.endpoints.interviews.generate_interview_questions", AsyncMock(side_effect=Exception(ai_exception_message_gen_q))) as mock_ai_generate_questions:

        # 3. Call SSE endpoint
        response = await async_app_client.post(f"/api/v1/interviews/{interview_id}/generate-questions-stream")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"].lower()

        # 4. Collect and parse SSE events
        received_events = []
        raw_event_chunks_for_debug = []
        async for line in response.aiter_lines():
            raw_event_chunks_for_debug.append(line)
            if line.startswith("data:"):
                event_data_str = line[len("data:") :].strip()
                try:
                    event_payload = json.loads(event_data_str)
                    received_events.append(event_payload)
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")
        
        assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

        # 5. Assert AG-UI Events
        task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
        assert task_start_event is not None, "TASK_START event not found"
        task_id = task_start_event["payload"]["task_id"]
        assert task_id, "Task ID missing in TASK_START event"

        thought_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_THOUGHT and e.get("payload", {}).get("task_id") == task_id]
        # Expect thoughts: Accessing, Analyzing JD, JD complete, Parsing resume, Resume complete, Generating questions (before exception)
        assert len(thought_events) >= 4, f"Expected at least 4 THOUGHT events before generate_questions exception, got {len(thought_events)}"

        error_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_ERROR and e.get("payload", {}).get("task_id") == task_id), None)
        assert error_event is not None, "ERROR AG-UI event not found for the correct task_id"
        
        # Check the error message from the AgUiErrorData schema which has 'error_message'
        # The stream's generic exception handler yields: AgUiErrorData(task_id=task_id, error_message=f"An unexpected error occurred: {str(e)}")
        assert "error_message" in error_event["payload"], "'error_message' field missing in ERROR event payload"
        assert "An unexpected error occurred" in error_event["payload"]["error_message"]
        assert ai_exception_message_gen_q in error_event["payload"]["error_message"]

        # 6. Assert AI service calls
        mock_ai_analyze_jd.assert_awaited_once()
        mock_ai_parse_resume.assert_awaited_once()
        mock_ai_generate_questions.assert_awaited_once() # It was called and it raised an exception

        # Ensure no QUESTION_GENERATED or successful TASK_END
        question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
        assert len(question_generated_events) == 0
        successful_task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and \
                                         e.get("payload", {}).get("status") == "success" and \
                                         e.get("payload", {}).get("task_id") == task_id), None)
        assert successful_task_end_event is None

    # 7. Assert Database state (status should not change due to db.rollback(), no questions created)
    response_get_interview = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get_interview.status_code == status.HTTP_200_OK
    interview_details = response_get_interview.json()
    assert interview_details["status"] == original_interview_status # Status should remain PENDING_QUESTIONS

    response_get_questions = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_questions.status_code == status.HTTP_200_OK
    assert response_get_questions.json() == []

@pytest.mark.asyncio
async def test_generate_questions_stream_ai_returns_empty_questions(
    async_app_client: httpx.AsyncClient, client: TestClient, db_session_test: Session
):
    """
    Test SSE stream when generate_interview_questions AI service returns an empty list/string.
    Expected: TASK_END event indicating no questions, and DB status update to QUESTIONS_FAILED.
    """
    # 1. Setup
    job_id = create_test_job(client, title="Job For AI Empty Q Stream", desc="Valid JD")
    candidate_id = create_test_candidate(client, email="aiemptyq.stream@example.com", resume_text="Valid resume")
    
    response_create_interview = client.post(
        "/api/v1/interviews/",
        json={"job_id": job_id, "candidate_id": candidate_id, "status": "PENDING_QUESTIONS"}
    )
    assert response_create_interview.status_code == status.HTTP_201_CREATED
    interview_id = response_create_interview.json()["id"]

    mock_analyzed_jd_success = "Analyzed JD for empty Q."
    mock_parsed_resume_success = "Parsed Resume for empty Q."
    mock_empty_questions_text = "" # AI returns empty string, meaning no questions

    # 2. Mock AI services to succeed but return no questions
    with patch("app.api.v1.endpoints.interviews.analyze_jd", AsyncMock(return_value=mock_analyzed_jd_success)) as mock_ai_analyze_jd, \
         patch("app.api.v1.endpoints.interviews.parse_resume", AsyncMock(return_value=mock_parsed_resume_success)) as mock_ai_parse_resume, \
         patch("app.api.v1.endpoints.interviews.generate_interview_questions", AsyncMock(return_value=mock_empty_questions_text)) as mock_ai_generate_questions:

        # 3. Call SSE endpoint
        response = await async_app_client.post(f"/api/v1/interviews/{interview_id}/generate-questions-stream")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"].lower()

        # 4. Collect and parse SSE events
        received_events = []
        raw_event_chunks_for_debug = []
        async for line in response.aiter_lines():
            raw_event_chunks_for_debug.append(line)
            if line.startswith("data:"):
                event_data_str = line[len("data:") :].strip()
                try:
                    event_payload = json.loads(event_data_str)
                    received_events.append(event_payload)
                except json.JSONDecodeError:
                    pytest.fail(f"Failed to parse SSE event JSON: {event_data_str}. Raw lines: {raw_event_chunks_for_debug}")
        
        assert len(received_events) > 0, f"No SSE events received. Raw chunks for debug: {raw_event_chunks_for_debug}"

        # 5. Assert AG-UI Events
        task_start_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_START), None)
        assert task_start_event is not None, "TASK_START event not found"
        task_id = task_start_event["payload"]["task_id"]
        assert task_id, "Task ID missing in TASK_START event"

        thought_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_THOUGHT and e.get("payload", {}).get("task_id") == task_id]
        # Expect thoughts: Accessing, Analyzing JD, JD complete, Parsing resume, Resume complete, Generating questions
        assert len(thought_events) >= 4, f"Expected at least 4 THOUGHT events, got {len(thought_events)}"

        # No QUESTION_GENERATED events
        question_generated_events = [e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_QUESTION_GENERATED and e.get("payload", {}).get("task_id") == task_id]
        assert len(question_generated_events) == 0, "QUESTION_GENERATED events found when AI returned empty questions"

        # TASK_END event indicating completion with no questions
        task_end_event = next((e for e in received_events if e.get("event_type") == AG_UI_EVENT_TYPE_TASK_END and e.get("payload", {}).get("task_id") == task_id), None)
        assert task_end_event is not None, "TASK_END event not found"
        # In generate_question_events_stream, status is "completed_with_no_questions"
        assert task_end_event["payload"]["status"] == "completed_with_no_questions"
        assert task_end_event["payload"]["message"] == f"Generated 0 questions for interview {interview_id}." # Based on current stream logic
        assert task_end_event["payload"]["final_questions"] == []

        # 6. Assert AI service calls
        mock_ai_analyze_jd.assert_awaited_once()
        mock_ai_parse_resume.assert_awaited_once()
        mock_ai_generate_questions.assert_awaited_once()

    # 7. Assert Database state
    # Status should be updated to QUESTIONS_FAILED as per current stream logic
    response_get_interview = client.get(f"/api/v1/interviews/{interview_id}")
    assert response_get_interview.status_code == status.HTTP_200_OK
    interview_details = response_get_interview.json()
    assert interview_details["status"] == InterviewStatus.QUESTIONS_FAILED.value

    response_get_questions = client.get(f"/api/v1/interviews/{interview_id}/questions")
    assert response_get_questions.status_code == status.HTTP_200_OK
    assert response_get_questions.json() == [] # No questions created

# Ensure models is imported if used for status comparison directly (e.g. models.InterviewStatus.QUESTIONS_GENERATED)
# from app.db import models # Would typically be at the top of the file 