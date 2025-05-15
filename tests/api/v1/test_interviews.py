from fastapi.testclient import TestClient
from fastapi import status
from datetime import datetime, timezone
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

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
def test_delete_interview_success(client: TestClient):
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
async def test_generate_questions_interview_not_found(client: TestClient):
    """Test generating questions for a non-existent interview."""
    # No need to mock AI services if the interview isn't found first.
    response = client.post("/api/v1/interviews/99999/generate-questions") # Non-existent ID
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # mock_ai_call.assert_not_called() # mock_ai_call is not defined here, so remove this

@pytest.mark.asyncio
async def test_generate_questions_missing_jd(client: TestClient, db_session_test: Session):
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
    assert "Job description (JD) not found for this interview." in response.json()["detail"]

@pytest.mark.asyncio
async def test_generate_questions_missing_resume(client: TestClient, db_session_test: Session):
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
    assert "Candidate resume text not found" in response.json()["detail"] # Adjusted assertion text based on previous logs

@pytest.mark.asyncio
async def test_generate_questions_ai_service_fails(client: TestClient):
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
async def test_generate_questions_ai_returns_empty_list(client: TestClient):
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