from fastapi.testclient import TestClient
from fastapi import status

# client fixture is automatically available from tests/conftest.py

VALID_CANDIDATE_EMAIL = "test.candidate@example.com"
VALID_CANDIDATE_NAME = "Test Candidate"
VALID_CANDIDATE_RESUME = "This is a test resume."

def test_create_candidate_success(client: TestClient):
    """Test successfully creating a new candidate."""
    candidate_data = {
        "name": VALID_CANDIDATE_NAME,
        "email": VALID_CANDIDATE_EMAIL,
        "resume_text": VALID_CANDIDATE_RESUME
    }
    response = client.post("/api/v1/candidates/", json=candidate_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == candidate_data["name"]
    assert data["email"] == candidate_data["email"]
    assert data["resume_text"] == candidate_data["resume_text"]
    assert "id" in data
    assert "created_at" in data

def test_create_candidate_duplicate_email(client: TestClient):
    """Test creating a candidate with an email that already exists."""
    candidate_data = {
        "name": "Another Candidate",
        "email": "duplicate.email@example.com",
        "resume_text": "Another resume."
    }
    # Create first candidate
    response1 = client.post("/api/v1/candidates/", json=candidate_data)
    assert response1.status_code == status.HTTP_201_CREATED

    # Attempt to create second candidate with the same email
    candidate_data_dup = {
        "name": "Duplicate Name",
        "email": "duplicate.email@example.com", # Same email
        "resume_text": "Duplicate resume."
    }
    response2 = client.post("/api/v1/candidates/", json=candidate_data_dup)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response2.json()
    assert "already exists" in response2.json()["detail"]

def test_read_candidate_by_id_success(client: TestClient):
    """Test successfully reading a candidate by their ID."""
    candidate_data = {
        "name": "Readable Candidate",
        "email": "readable.candidate@example.com",
        "resume_text": "A resume to be read."
    }
    response_create = client.post("/api/v1/candidates/", json=candidate_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    created_candidate_id = response_create.json()["id"]
    
    response_read = client.get(f"/api/v1/candidates/{created_candidate_id}")
    assert response_read.status_code == status.HTTP_200_OK
    read_data = response_read.json()
    assert read_data["id"] == created_candidate_id
    assert read_data["name"] == candidate_data["name"]
    assert read_data["email"] == candidate_data["email"]

def test_read_candidate_by_id_not_found(client: TestClient):
    """Test reading a candidate by an ID that does not exist."""
    non_existent_id = 999888 # Assuming this ID won't exist
    response = client.get(f"/api/v1/candidates/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Candidate not found"}

def test_read_candidates_empty(client: TestClient):
    """Test reading candidates when the database is empty."""
    response = client.get("/api/v1/candidates/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_read_candidates_with_data_and_pagination(client: TestClient):
    """Test reading candidates with data and testing pagination."""
    # Create a few candidates
    base_email = "candidate.page.{index}@example.com"
    candidate_details = []
    for i in range(1, 6): # Create 5 candidates
        email = base_email.format(index=i)
        data = {"name": f"Candidate Page {i}", "email": email, "resume_text": f"Resume for {email}"}
        response = client.post("/api/v1/candidates/", json=data)
        assert response.status_code == status.HTTP_201_CREATED
        candidate_details.append(response.json()) # Store created candidate details (including ID)

    # Test case 1: Get all candidates (we have 5)
    response = client.get("/api/v1/candidates/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 5

    # Test case 2: Limit to 2 candidates
    response = client.get("/api/v1/candidates/?limit=2")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == candidate_details[0]["id"]
    assert data[1]["id"] == candidate_details[1]["id"]

    # Test case 3: Skip 2 candidates, limit 2 candidates
    response = client.get("/api/v1/candidates/?skip=2&limit=2")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == candidate_details[2]["id"]
    assert data[1]["id"] == candidate_details[3]["id"]

    # Test case 4: Skip all but one
    response = client.get(f"/api/v1/candidates/?skip={len(candidate_details) - 1}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == candidate_details[-1]["id"]

    # Test case 5: Skip more than available - should return empty list
    response = client.get(f"/api/v1/candidates/?skip={len(candidate_details) + 5}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # Test case 6: Limit 0 - should return empty list
    response = client.get("/api/v1/candidates/?limit=0")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_update_candidate_success(client: TestClient):
    """Test successfully updating an existing candidate."""
    # Create a candidate first
    initial_data = {"name": "Original Name", "email": "update.success@example.com", "resume_text": "Original resume"}
    response_create = client.post("/api/v1/candidates/", json=initial_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    created_candidate = response_create.json()
    candidate_id = created_candidate["id"]

    update_payload = {"name": "Updated Name", "resume_text": "Updated resume"}
    response_update = client.put(f"/api/v1/candidates/{candidate_id}", json=update_payload)
    
    assert response_update.status_code == status.HTTP_200_OK
    updated_data = response_update.json()
    assert updated_data["id"] == candidate_id
    assert updated_data["name"] == update_payload["name"]
    assert updated_data["email"] == initial_data["email"] # Email should not change
    assert updated_data["resume_text"] == update_payload["resume_text"]
    assert updated_data["created_at"] == created_candidate["created_at"]

def test_update_candidate_partial(client: TestClient):
    """Test partially updating a candidate (only name)."""
    initial_data = {"name": "Partial Original", "email": "partial.update@example.com", "resume_text": "Partial resume"}
    response_create = client.post("/api/v1/candidates/", json=initial_data)
    created_candidate = response_create.json()
    candidate_id = created_candidate["id"]

    update_payload = {"name": "Partial Updated Name"}
    response_update = client.put(f"/api/v1/candidates/{candidate_id}", json=update_payload)
    
    assert response_update.status_code == status.HTTP_200_OK
    updated_data = response_update.json()
    assert updated_data["name"] == update_payload["name"]
    assert updated_data["resume_text"] == initial_data["resume_text"] # Resume text should be unchanged
    assert updated_data["email"] == initial_data["email"] # Email should be unchanged

def test_update_candidate_not_found(client: TestClient):
    """Test updating a candidate that does not exist."""
    non_existent_id = 777666
    update_payload = {"name": "Ghost Candidate"}
    response = client.put(f"/api/v1/candidates/{non_existent_id}", json=update_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Candidate not found"}

def test_delete_candidate_success(client: TestClient):
    """Test successfully deleting an existing candidate."""
    # Create a candidate to delete
    candidate_data = {"name": "ToDelete Candidate", "email": "todelete@example.com", "resume_text": "Delete this resume."}
    response_create = client.post("/api/v1/candidates/", json=candidate_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    candidate_id_to_delete = response_create.json()["id"]

    # Delete the candidate
    response_delete = client.delete(f"/api/v1/candidates/{candidate_id_to_delete}")
    assert response_delete.status_code == status.HTTP_204_NO_CONTENT

    # Try to get the deleted candidate, should be 404
    response_get = client.get(f"/api/v1/candidates/{candidate_id_to_delete}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND

def test_delete_candidate_not_found(client: TestClient):
    """Test deleting a candidate that does not exist."""
    non_existent_id = 555444
    response = client.delete(f"/api/v1/candidates/{non_existent_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Candidate not found"}

# All CRUD for Candidate now have basic tests.
# Further tests could include more complex scenarios or edge cases if needed. 