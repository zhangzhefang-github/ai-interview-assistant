from fastapi.testclient import TestClient
from fastapi import status

# Note: No need to import db_session_test directly in test files,
# the client fixture in conftest.py handles the database session.

def test_create_job(client: TestClient):
    """Test creating a new job."""
    job_data = {"title": "Software Test Engineer", "description": "Tests software applications."}
    response = client.post("/api/v1/jobs/", json=job_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == job_data["title"]
    assert data["description"] == job_data["description"]
    assert "id" in data
    assert "created_at" in data

def test_read_jobs_empty(client: TestClient):
    """Test reading jobs when the database is empty."""
    response = client.get("/api/v1/jobs/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_read_jobs_with_data(client: TestClient):
    """Test reading jobs when there is data."""
    # Create a job first
    job_data1 = {"title": "Senior Developer", "description": "Leads development projects."}
    response_create1 = client.post("/api/v1/jobs/", json=job_data1)
    assert response_create1.status_code == status.HTTP_201_CREATED
    created_job1 = response_create1.json()

    job_data2 = {"title": "DevOps Engineer", "description": "Manages CI/CD pipelines."}
    response_create2 = client.post("/api/v1/jobs/", json=job_data2)
    assert response_create2.status_code == status.HTTP_201_CREATED
    created_job2 = response_create2.json()

    # Now, read all jobs
    response_read = client.get("/api/v1/jobs/")
    assert response_read.status_code == status.HTTP_200_OK
    jobs_list = response_read.json()
    
    assert len(jobs_list) == 2
    
    # Check if the created jobs are in the list
    # Order might not be guaranteed unless specified in the query, so check for presence
    titles_in_response = [job["title"] for job in jobs_list]
    assert job_data1["title"] in titles_in_response
    assert job_data2["title"] in titles_in_response

    ids_in_response = [job["id"] for job in jobs_list]
    assert created_job1["id"] in ids_in_response
    assert created_job2["id"] in ids_in_response

def test_read_job_by_id_success(client: TestClient):
    """Test successfully reading a job by its ID."""
    job_data = {"title": "Data Scientist", "description": "Analyzes complex data sets."}
    response_create = client.post("/api/v1/jobs/", json=job_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    created_job_id = response_create.json()["id"]
    created_job_title = response_create.json()["title"]

    response_read = client.get(f"/api/v1/jobs/{created_job_id}")
    assert response_read.status_code == status.HTTP_200_OK
    read_job_data = response_read.json()
    assert read_job_data["id"] == created_job_id
    assert read_job_data["title"] == created_job_title
    assert read_job_data["description"] == job_data["description"]

def test_read_job_by_id_not_found(client: TestClient):
    """Test reading a job by an ID that does not exist."""
    non_existent_job_id = 99999 # Assuming this ID won't exist
    response = client.get(f"/api/v1/jobs/{non_existent_job_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Job not found"}

def test_update_job_success(client: TestClient):
    """Test successfully updating an existing job."""
    # First, create a job to update
    initial_job_data = {"title": "Junior Developer", "description": "Assists with development tasks."}
    response_create = client.post("/api/v1/jobs/", json=initial_job_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    created_job = response_create.json()
    job_id_to_update = created_job["id"]

    # Now, update the job
    update_payload = {"title": "Mid-Level Developer", "description": "Works independently on features."}
    response_update = client.put(f"/api/v1/jobs/{job_id_to_update}", json=update_payload)
    
    assert response_update.status_code == status.HTTP_200_OK
    updated_job_data = response_update.json()
    assert updated_job_data["id"] == job_id_to_update
    assert updated_job_data["title"] == update_payload["title"]
    assert updated_job_data["description"] == update_payload["description"]
    # Check if created_at is still the same (or handle if it should change)
    assert updated_job_data["created_at"] == created_job["created_at"]

def test_update_job_partial(client: TestClient):
    """Test partially updating an existing job (e.g., only title)."""
    initial_job_data = {"title": "Project Manager", "description": "Manages project timelines."}
    response_create = client.post("/api/v1/jobs/", json=initial_job_data)
    created_job = response_create.json()
    job_id_to_update = created_job["id"]

    update_payload = {"title": "Senior Project Manager"} # Only updating title
    response_update = client.put(f"/api/v1/jobs/{job_id_to_update}", json=update_payload)
    
    assert response_update.status_code == status.HTTP_200_OK
    updated_job_data = response_update.json()
    assert updated_job_data["title"] == update_payload["title"]
    assert updated_job_data["description"] == initial_job_data["description"] # Description should remain unchanged

def test_update_job_not_found(client: TestClient):
    """Test updating a job that does not exist."""
    non_existent_job_id = 88888
    update_payload = {"title": "Ghost Job"}
    response = client.put(f"/api/v1/jobs/{non_existent_job_id}", json=update_payload)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Job not found"}

def test_delete_job_success(client: TestClient):
    """Test successfully deleting an existing job."""
    # First, create a job to delete
    job_data = {"title": "Temporary Role", "description": "A role to be deleted."}
    response_create = client.post("/api/v1/jobs/", json=job_data)
    assert response_create.status_code == status.HTTP_201_CREATED
    job_id_to_delete = response_create.json()["id"]

    # Delete the job
    response_delete = client.delete(f"/api/v1/jobs/{job_id_to_delete}")
    assert response_delete.status_code == status.HTTP_204_NO_CONTENT

    # Try to get the deleted job, should be 404
    response_get = client.get(f"/api/v1/jobs/{job_id_to_delete}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND

def test_delete_job_not_found(client: TestClient):
    """Test deleting a job that does not exist."""
    non_existent_job_id = 77777
    response = client.delete(f"/api/v1/jobs/{non_existent_job_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Job not found"}

def test_read_jobs_pagination(client: TestClient):
    """Test pagination for reading jobs."""
    # Create a few jobs for testing pagination
    job_titles = [f"Paginated Job {i}" for i in range(1, 6)] # Create 5 jobs
    created_job_ids = []
    for title in job_titles:
        response = client.post("/api/v1/jobs/", json={"title": title, "description": "Test pagination"})
        assert response.status_code == status.HTTP_201_CREATED
        created_job_ids.append(response.json()["id"])
    
    # Test case 1: Get all jobs (default limit is often 100, we have 5)
    response = client.get("/api/v1/jobs/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 5

    # Test case 2: Limit to 2 jobs
    response = client.get("/api/v1/jobs/?limit=2")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == created_job_ids[0]
    assert data[1]["id"] == created_job_ids[1]

    # Test case 3: Skip 2 jobs, limit 2 jobs
    response = client.get("/api/v1/jobs/?skip=2&limit=2")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == created_job_ids[2]
    assert data[1]["id"] == created_job_ids[3]

    # Test case 4: Skip all but one
    response = client.get(f"/api/v1/jobs/?skip={len(created_job_ids) - 1}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == created_job_ids[-1]

    # Test case 5: Skip more than available - should return empty list
    response = client.get(f"/api/v1/jobs/?skip={len(created_job_ids) + 5}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # Test case 6: Limit 0 - should return empty list (or handle as per API design)
    # FastAPI/SQLAlchemy typically handles limit=0 by returning no rows.
    response = client.get("/api/v1/jobs/?limit=0")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

# TODO: Further tests could include invalid skip/limit values (e.g., negative)
# if the API has specific error handling for them, though FastAPI often handles this with validation errors.

# TODO: Add tests for pagination (skip, limit) for read_jobs
# def test_read_jobs_pagination(client: TestClient):
#     pass 