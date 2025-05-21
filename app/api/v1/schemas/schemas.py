from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
from app.db.models import SpeakerRole

# --- Job Schemas ---
class JobBase(BaseModel):
    title: str
    description: str
    analyzed_description: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    analyzed_description: Optional[str] = None

class JobRead(JobBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobInDBBase(JobBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Job(JobInDBBase): # Schema for returning a job
    pass

# --- Candidate Schemas ---
class CandidateBase(BaseModel):
    name: str
    email: EmailStr
    resume_text: str
    structured_resume_info: Optional[dict] = None

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    resume_text: Optional[str] = None
    structured_resume_info: Optional[dict] = None
    # Email is typically not updatable directly or requires a separate process

class CandidateInDBBase(CandidateBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Candidate(CandidateInDBBase): # Schema for returning a candidate
    pass 

# --- Question Schemas (used within Interview) ---
class QuestionBase(BaseModel):
    question_text: str
    order_num: Optional[int] = None

class QuestionCreate(QuestionBase):
    pass # interview_id will be set programmatically

class QuestionInDBBase(QuestionBase):
    id: int
    interview_id: int
    model_config = ConfigDict(from_attributes=True)

class Question(QuestionInDBBase): # Schema for returning a question
    pass 

# --- Report Schemas (forward declaration for Interview) ---
class ReportBase(BaseModel):
    generated_text: str
    source_dialogue: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class Report(ReportBase): 
    id: int
    interview_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ReportUpdate(BaseModel):
    generated_text: Optional[str] = None
    source_dialogue: Optional[str] = None

# --- InterviewLog Schemas (forward declaration for Interview) ---
class InterviewLogBase(BaseModel):
    question_id: Optional[int] = None
    full_dialogue_text: Optional[str] = None
    order_num: Optional[int] = None
    speaker_role: Optional[SpeakerRole] = Field(default=SpeakerRole.SYSTEM)
    question_text_snapshot: Optional[str] = None

    class Config:
        from_attributes = True

class InterviewLogCreate(InterviewLogBase):
    pass

class InterviewLog(InterviewLogBase):
    id: int
    interview_id: int
    created_at: datetime

# --- Interview Schemas ---
class InterviewBase(BaseModel):
    job_id: int
    candidate_id: int
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = "PENDING_QUESTIONS"

class InterviewCreate(InterviewBase):
    pass

class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    conversation_log: Optional[str] = None # Added for interview logging

class InterviewInDBBase(InterviewBase):
    id: int
    created_at: datetime
    updated_at: datetime
    conversation_log: Optional[str] = None
    questions: List[Question] = [] 
    logs: List[InterviewLog] = []
    generated_report: Optional[Report] = None
    job: Optional[JobRead] = None      
    candidate: Optional[Candidate] = None 
    radar_data: Optional[dict] = None  
    model_config = ConfigDict(from_attributes=True)

class Interview(InterviewInDBBase): 
    pass

class InterviewWithQuestions(Interview):
    pass

class InterviewCreateWithData(BaseModel):
    job_title: str
    job_description: str
    candidate_name: str
    candidate_email: EmailStr
    candidate_resume_text: str
    scheduled_at: Optional[datetime] = None

# --- Report Schemas (definitions moved up for clarity if not already) ---
# ReportBase, ReportCreate, Report, ReportUpdate are already defined above.

# Optional: If you need a schema for updating, though reports might be regenerated rather than partially updated
# ReportUpdate is already defined above. 