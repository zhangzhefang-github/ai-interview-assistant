# streamlit_app/utils/api_client.py
import streamlit as st # Required for st.error
import requests
from streamlit_app.core_ui_config import BACKEND_API_URL
from streamlit_app.utils.logger_config import get_logger
from io import BytesIO
from urllib.parse import urljoin # Added for robust URL joining
from typing import Optional # Ensure Optional is imported
from datetime import datetime # Ensure datetime is imported for type hint if not already

# 使用 __name__ 作为 logger 的名称，符合Python的习惯
logger = get_logger(__name__) 

# --- Custom API Error ---
class APIError(Exception):
    """Custom exception for API request errors."""
    def __init__(self, message, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details # To store more detailed error info if available

    def __str__(self):
        if self.status_code:
            return f"[API Error {self.status_code}] {self.message}"
        return f"[API Error] {self.message}"

# --- Job API Functions ---
def get_jobs() -> list:
    endpoint_path = "v1/jobs/"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to fetch jobs from {full_url}")
    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        jobs_list = response.json()
        logger.info(f"Successfully fetched {len(jobs_list)} jobs.")
        logger.debug(f"Fetched jobs data: {jobs_list}")
        return jobs_list
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while fetching jobs: {http_err} - Status: {http_err.response.status_code} - Response: {http_err.response.text}")
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass # Keep original text if not JSON
        raise APIError(
            message=f"获取职位列表失败: 服务器返回错误",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Connection error occurred while fetching jobs: {conn_err}")
        raise APIError(message=f"获取职位列表失败: 无法连接到后端服务 at {full_url}")
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout error occurred while fetching jobs: {timeout_err}")
        raise APIError(message="获取职位列表失败: 请求超时")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"An unexpected request error occurred while fetching jobs: {req_err}", exc_info=True)
        raise APIError(message=f"获取职位列表时发生请求错误: {req_err}")
    except ValueError as ve: # Includes JSONDecodeError
        logger.error(f"JSON decoding error occurred while fetching jobs: {ve}", exc_info=True)
        raise APIError(message="获取职位列表失败: 服务器返回无效的数据格式")

def create_job(title: str, description: str) -> dict:
    endpoint_path = "v1/jobs/"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to create job with title: '{title}' at {full_url}")
    payload = {"title": title, "description": description}
    logger.debug(f"Create job payload: {payload}")
    try:
        response = requests.post(full_url, json=payload, timeout=10)
        response.raise_for_status()
        created_job_data = response.json()
        logger.info(f"Successfully created job. Response: {created_job_data}")
        return created_job_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while creating job: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"创建职位失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while creating job: {e}", exc_info=True)
        raise APIError(message=f"创建职位时发生意外错误: {e}")

def delete_job_api(job_id: int) -> None: # Returns None on success, raises APIError on failure
    endpoint_path = f"v1/jobs/{job_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to delete job with ID: {job_id} at {full_url}")
    try:
        response = requests.delete(full_url, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully deleted job ID: {job_id}. Status: {response.status_code}")
        return # Explicitly return None on success
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while deleting job ID {job_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"删除职位失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while deleting job ID {job_id}: {e}", exc_info=True)
        raise APIError(message=f"删除职位时发生意外错误: {e}")

def update_job_api(job_id: int, title: str, description: str) -> dict:
    endpoint_path = f"v1/jobs/{job_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to update job ID {job_id} with title: '{title}' at {full_url}")
    payload = {"title": title, "description": description}
    logger.debug(f"Update job payload for ID {job_id}: {payload}")
    try:
        response = requests.put(full_url, json=payload, timeout=10)
        response.raise_for_status()
        updated_job_data = response.json()
        logger.info(f"Successfully updated job ID {job_id}. Response: {updated_job_data}")
        return updated_job_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while updating job ID {job_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"更新职位失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while updating job ID {job_id}: {e}", exc_info=True)
        raise APIError(message=f"更新职位时发生意外错误: {e}")

# TODO: Add API functions for Candidates, Interviews, etc. as they are developed.
# Example:
# def get_candidates(job_id: int = None):
#     pass 

def create_candidate_with_resume(name: str, email: str, resume_file: BytesIO, filename: str) -> dict:
    endpoint_path = "v1/candidates/upload-resume/"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to create candidate '{name}' with resume '{filename}' from {full_url}")
    
    files = {'resume_file': (filename, resume_file, resume_file.type if hasattr(resume_file, 'type') else None)} # Pass content type if available from Streamlit's UploadedFile
    data = {'name': name, 'email': email}
    
    try:
        response = requests.post(full_url, data=data, files=files, timeout=30) # Increased timeout for file upload
        response.raise_for_status()
        candidate_data = response.json()
        logger.info(f"Successfully created candidate '{name}' with resume '{filename}'.")
        return candidate_data
            
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.warning(f"Failed to create candidate '{name}'. Status: {http_err.response.status_code}. Response: {error_detail}")
        raise APIError(
            message=f"创建候选人失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for create_candidate_with_resume: {e}", exc_info=True)
        raise APIError(message=f"调用创建候选人接口失败: {e}")
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred in create_candidate_with_resume: {e}", exc_info=True)
        raise APIError(message=f"创建候选人时发生意外后端错误: {e}")

# Placeholder for other candidate-related API calls
def get_candidates(skip: int = 0, limit: int = 100) -> list:
    endpoint_path = "v1/candidates/"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Fetching candidates from API (skip={skip}, limit={limit}) from {full_url}")
    try:
        response = requests.get(full_url, params={"skip": skip, "limit": limit}, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error on get_candidates: {http_err.response.status_code} - {http_err.response.text}", exc_info=True)
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        raise APIError(
            message=f"获取候选人列表失败: 服务器返回错误",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for get_candidates: {e}", exc_info=True)
        raise APIError(message=f"获取候选人列表失败: {e}")

def get_candidate_by_id(candidate_id: int) -> dict:
    endpoint_path = f"v1/candidates/{candidate_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Fetching candidate with ID {candidate_id} from {full_url}")
    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status() # This will raise for 404 as well
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error on get_candidate_by_id for ID {candidate_id}: {http_err.response.status_code} - {http_err.response.text}", exc_info=True)
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        if http_err.response.status_code == 404:
            raise APIError(message=f"候选人 ID {candidate_id} 未找到。", status_code=404, details=error_detail)
        else:
            raise APIError(
                message=f"获取候选人 {candidate_id} 失败: 服务器返回错误",
                status_code=http_err.response.status_code,
                details=error_detail
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for get_candidate_by_id for ID {candidate_id}: {e}", exc_info=True)
        raise APIError(f"获取候选人 {candidate_id} 失败: {e}")

def update_candidate_api(candidate_id: int, name: str, email: str, resume_text: str = None) -> dict:
    endpoint_path = f"v1/candidates/{candidate_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to update candidate ID {candidate_id} with name: '{name}', email: '{email}' at {full_url}")
    payload = {"name": name, "email": email}
    if resume_text is not None: # Only include resume_text if provided
        payload["resume_text"] = resume_text
    
    logger.debug(f"Update candidate payload for ID {candidate_id}: {payload}")
    try:
        response = requests.put(full_url, json=payload, timeout=10)
        response.raise_for_status()
        updated_candidate_data = response.json()
        logger.info(f"Successfully updated candidate ID {candidate_id}. Response: {updated_candidate_data}")
        return updated_candidate_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while updating candidate ID {candidate_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"更新候选人失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while updating candidate ID {candidate_id}: {e}", exc_info=True)
        raise APIError(message=f"更新候选人时发生意外错误: {e}")

def delete_candidate_api(candidate_id: int) -> None: # Returns None on success
    endpoint_path = f"v1/candidates/{candidate_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to delete candidate with ID: {candidate_id} at {full_url}")
    try:
        response = requests.delete(full_url, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully deleted candidate ID: {candidate_id}. Status: {response.status_code}")
        return # Explicitly return None on success
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while deleting candidate ID {candidate_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        if http_err.response.status_code == 404:
             raise APIError(message=f"删除候选人失败: 候选人 ID {candidate_id} 未找到。", status_code=404, details=error_detail)
        else:
            raise APIError(
                message="删除候选人失败，请查看详细信息。",
                status_code=http_err.response.status_code,
                details=error_detail
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while deleting candidate ID {candidate_id}: {e}", exc_info=True)
        raise APIError(message=f"删除候选人时发生意外错误: {e}")

# --- Interview API Functions ---
def create_interview(job_id: int, candidate_id: int, scheduled_at: Optional[str] = None, status: str = "PENDING_QUESTIONS") -> dict:
    endpoint_path = "v1/interviews/"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    payload = {
        "job_id": job_id, 
        "candidate_id": candidate_id, 
        "status": status
    }
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at # Expecting ISO format string
        
    logger.info(f"Attempting to create interview for job ID {job_id} and candidate ID {candidate_id} with status '{status}' and scheduled_at '{scheduled_at}' at {full_url}")
    logger.debug(f"Create interview payload: {payload}")
    try:
        response = requests.post(full_url, json=payload, timeout=10)
        response.raise_for_status()
        created_interview_data = response.json()
        logger.info(f"Successfully created interview. Response: {created_interview_data}")
        return created_interview_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while creating interview: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        # Check for specific error messages from backend if job_id or candidate_id is invalid
        if "Job not found" in error_detail:
            raise APIError(message=f"安排面试失败: 职位 ID {job_id} 未找到。", status_code=http_err.response.status_code, details=error_detail)
        elif "Candidate not found" in error_detail:
            raise APIError(message=f"安排面试失败: 候选人 ID {candidate_id} 未找到。", status_code=http_err.response.status_code, details=error_detail)
        raise APIError(
            message=f"安排面试失败: {error_detail}", 
            status_code=http_err.response.status_code, 
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while creating interview: {e}", exc_info=True)
        raise APIError(message=f"安排面试时发生意外错误: {e}")

# Placeholder for other interview-related API calls like get_interviews, generate_questions etc.

def get_interviews(skip: int = 0, limit: int = 100) -> list:
    endpoint_path = "v1/interviews/"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Fetching interviews from API (skip={skip}, limit={limit}) from {full_url}")
    try:
        response = requests.get(full_url, params={"skip": skip, "limit": limit}, timeout=10)
        response.raise_for_status()
        interviews_list = response.json()
        logger.info(f"Successfully fetched {len(interviews_list)} interviews.")
        logger.debug(f"Fetched interviews data: {interviews_list}")
        return interviews_list
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error on get_interviews: {http_err.response.status_code} - {http_err.response.text}", exc_info=True)
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass # Keep original text if not JSON
        raise APIError(
            message=f"获取面试列表失败: 服务器返回错误",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for get_interviews: {e}", exc_info=True)
        raise APIError(message=f"获取面试列表失败: {e}")
    except ValueError as ve: # Includes JSONDecodeError
        logger.error(f"JSON decoding error occurred while fetching interviews: {ve}", exc_info=True)
        raise APIError(message="获取面试列表失败: 服务器返回无效的数据格式")

def generate_interview_questions_for_interview(interview_id: int) -> dict:
    endpoint_path = f"v1/interviews/{interview_id}/generate-questions"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to generate interview questions for interview ID {interview_id} at {full_url}")
    try:
        response = requests.post(full_url, timeout=60) # Increased timeout for potentially long AI generation
        response.raise_for_status()
        result_data = response.json()
        logger.info(f"Successfully triggered question generation for interview ID {interview_id}. Response: {result_data}")
        return result_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while generating questions for interview ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"生成面试问题失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while generating questions for interview ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"生成面试问题时发生意外错误: {e}")
    except ValueError as ve: # Includes JSONDecodeError
        logger.error(f"JSON decoding error occurred after generating questions for interview ID {interview_id}: {ve}", exc_info=True)
        raise APIError(message="生成面试问题失败: 服务器返回无效的数据格式")

def get_questions_for_interview(interview_id: int) -> list: # Changed return type hint
    endpoint_path = f"v1/interviews/{interview_id}/questions"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to fetch questions for interview ID {interview_id} from {full_url}")
    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        questions_list = response.json()
        logger.info(f"Successfully fetched {len(questions_list)} questions for interview ID {interview_id}.")
        logger.debug(f"Fetched questions data: {questions_list}")
        return questions_list
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while fetching questions for interview ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        if http_err.response.status_code == 404:
            # This specific check might be useful if an interview exists but has no questions yet, 
            # though the backend currently returns questions from an existing interview, which could be an empty list.
            # For now, a general error is fine.
            pass # Let general error handling proceed
        raise APIError(
            message=f"获取面试问题失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while fetching questions for interview ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"获取面试问题时发生意外错误: {e}")
    except ValueError as ve: # Includes JSONDecodeError
        logger.error(f"JSON decoding error occurred while fetching questions for interview ID {interview_id}: {ve}", exc_info=True)
        raise APIError(message="获取面试问题失败: 服务器返回无效的数据格式")

def update_interview_api(interview_id: int, interview_data: dict) -> dict:
    endpoint_path = f"v1/interviews/{interview_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to update interview ID {interview_id} at {full_url} with data: {interview_data}")
    try:
        response = requests.put(full_url, json=interview_data, timeout=10)
        response.raise_for_status()
        updated_interview = response.json()
        logger.info(f"Successfully updated interview ID {interview_id}. Response: {updated_interview}")
        return updated_interview
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while updating interview ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"更新面试信息失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while updating interview ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"更新面试信息时发生意外错误: {e}")
    except ValueError as ve: # Includes JSONDecodeError
        logger.error(f"JSON decoding error occurred after updating interview ID {interview_id}: {ve}", exc_info=True)
        raise APIError(message="更新面试信息失败: 服务器返回无效的数据格式")

def delete_interview_api(interview_id: int) -> None:
    endpoint_path = f"v1/interviews/{interview_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to delete interview ID {interview_id} at {full_url}")
    try:
        response = requests.delete(full_url, timeout=10)
        response.raise_for_status() # Raises HTTPError for 4xx/5xx status codes
        logger.info(f"Successfully deleted interview ID {interview_id}. Status: {response.status_code}")
        return # No content to return on successful deletion (204)
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError: # If response is not JSON
            pass
        logger.error(f"HTTP error occurred while deleting interview ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        if http_err.response.status_code == 404:
            raise APIError(message=f"删除面试失败: 面试 ID {interview_id} 未找到。", status_code=404, details=error_detail)
        else:
            raise APIError(
                message=f"删除面试失败: {error_detail}",
                status_code=http_err.response.status_code,
                details=error_detail
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while deleting interview ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"删除面试时发生意外错误: {e}")

# Function to get full details of a single interview (including report, questions, etc.)
def get_interview_details(interview_id: int) -> dict:
    endpoint_path = f"v1/interviews/{interview_id}"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Fetching details for interview ID {interview_id} from {full_url}")
    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        interview_details = response.json()
        logger.info(f"Successfully fetched details for interview ID {interview_id}.")
        logger.debug(f"Fetched interview details: {interview_details}")
        return interview_details
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass 
        logger.error(f"HTTP error occurred while fetching details for interview ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        if http_err.response.status_code == 404:
            raise APIError(message=f"获取面试详情失败: 面试 ID {interview_id} 未找到。", status_code=404, details=error_detail)
        raise APIError(
            message=f"获取面试详情失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while fetching details for interview ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"获取面试详情时发生意外错误: {e}")
    except ValueError as ve:
        logger.error(f"JSON decoding error occurred while fetching details for interview ID {interview_id}: {ve}", exc_info=True)
        raise APIError(message="获取面试详情失败: 服务器返回无效的数据格式")

def generate_report_for_interview_api(interview_id: int) -> dict:
    endpoint_path = f"v1/interviews/{interview_id}/generate-report"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Attempting to trigger report generation for interview ID: {interview_id} at {full_url}")
    try:
        response = requests.post(full_url, timeout=180) # Increased timeout for potentially long AI generation
        response.raise_for_status()
        report_data = response.json()
        logger.info(f"Successfully triggered report generation for interview ID: {interview_id}. Report data: {report_data}")
        return report_data
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while triggering report generation for interview ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"生成AI评估报告失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while triggering report generation for interview ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"调用生成AI评估报告接口时发生意外错误: {e}")

# --- Interview Log API Functions ---
def get_interview_logs_api(interview_id: int) -> list:
    endpoint_path = f"v1/interviews/{interview_id}/logs"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Fetching interview logs for interview ID {interview_id} from {full_url}")
    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        logs = response.json()
        logger.info(f"Successfully fetched {len(logs)} logs for interview ID {interview_id}.")
        return logs
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error on get_interview_logs_api for ID {interview_id}: {http_err.response.status_code} - {http_err.response.text}", exc_info=True)
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        raise APIError(
            message=f"获取面试过程记录失败: 服务器返回错误",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for get_interview_logs_api for ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"获取面试过程记录失败: {e}")

def create_interview_log_api(interview_id: int, log_data: dict) -> dict:
    endpoint_path = f"v1/interviews/{interview_id}/logs"
    full_url = urljoin(BACKEND_API_URL, endpoint_path)
    logger.info(f"Creating interview log for interview ID {interview_id} at {full_url} with payload: {log_data}")
    try:
        response = requests.post(full_url, json=log_data, timeout=10)
        response.raise_for_status()
        created_log = response.json()
        logger.info(f"Successfully created interview log for ID {interview_id}. Response: {created_log}")
        return created_log
    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        try:
            error_detail = http_err.response.json().get("detail", http_err.response.text)
        except ValueError:
            pass
        logger.error(f"HTTP error occurred while creating interview log for ID {interview_id}: {http_err} - Status: {http_err.response.status_code} - Detail: {error_detail}")
        raise APIError(
            message=f"保存面试过程记录失败: {error_detail}",
            status_code=http_err.response.status_code,
            details=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"An unexpected error occurred while creating interview log for ID {interview_id}: {e}", exc_info=True)
        raise APIError(message=f"保存面试过程记录时发生意外错误: {e}")

# Make sure to add new functions to __all__ if you use it for explicit exports
# Example for __all__ if it existed at the top of the file:
# __all__ = ["APIError", "get_jobs", "create_job", ..., "get_interview_logs_api", "create_interview_log_api"] 