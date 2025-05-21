from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, TIMESTAMP, Enum as DBEnum, JSON
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

# 职位模型
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    analyzed_description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    interviews = relationship("Interview", back_populates="job")

# 候选人模型
class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    resume_text = Column(Text, nullable=False)
    structured_resume_info = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    interviews = relationship("Interview", back_populates="candidate")

# Define InterviewStatus Enum
class InterviewStatus(enum.Enum):
    PENDING_QUESTIONS = "PENDING_QUESTIONS"
    QUESTIONS_GENERATED = "QUESTIONS_GENERATED"
    LOGGING_COMPLETED = "LOGGING_COMPLETED" # Indicates logs are present and report can be generated
    REPORT_GENERATED = "REPORT_GENERATED"
    # Potentially: AWAITING_LOGS, INTERVIEW_IN_PROGRESS

# Define SpeakerRole Enum for InterviewLog
class SpeakerRole(enum.Enum):
    INTERVIEWER = "INTERVIEWER" # AI Interviewer
    CANDIDATE = "CANDIDATE"
    SYSTEM = "SYSTEM" # For system messages, if any

# 新的 InterviewLog 模型
class InterviewLog(Base):
    __tablename__ = "interview_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True) # Link to the specific question if applicable
    
    speaker_role = Column(DBEnum(SpeakerRole), nullable=False) # ADDED SPEAKER_ROLE

    # Stores the actual text of the question at the time of logging,
    # useful if predefined questions can change or if it's an ad-hoc question.
    question_text_snapshot = Column(Text, nullable=True)
    
    # Stores the candidate's answer or a segment of dialogue.
    # For a multi-turn dialogue within one "question", you might have multiple logs
    # or a more complex structure for full_dialogue_text.
    # For MVP, let's assume this holds a significant chunk of dialogue related to a question.
    full_dialogue_text = Column(Text, nullable=False) # Renamed from dialogue_turn_text for consistency with generator

    order_num = Column(Integer, nullable=True) # Order of this log entry within the interview
    created_at = Column(TIMESTAMP, server_default=func.now())
    # updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now()) # If logs can be edited

    interview = relationship("Interview", back_populates="logs")
    question = relationship("Question") # Relationship to Question model

# 新的 Report 模型
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), unique=True, nullable=False) # One report per interview
    generated_text = Column(Text, nullable=False)
    source_dialogue = Column(Text, nullable=True) # ADDED: To store the dialogue used for report generation
    # llm_model_used = Column(String(100), nullable=True) # Optional: track model used
    # report_version = Column(Integer, default=1) # Optional: if reports can be re-generated and versioned
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    interview = relationship("Interview", back_populates="generated_report") # Changed relationship name

# 面试模型 - 更新
class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    status = Column(DBEnum(InterviewStatus), nullable=False, default=InterviewStatus.PENDING_QUESTIONS)
    conversation_log = Column(Text, nullable=True) # ADDED (or uncommented) for MVP single log
    # report = Column(Text, nullable=True) # REMOVED
    radar_data = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now()) # ADDED

    job = relationship("Job", back_populates="interviews")
    candidate = relationship("Candidate", back_populates="interviews")
    questions = relationship("Question", back_populates="interview", cascade="all, delete-orphan")
    
    # 新的关联关系
    logs = relationship("InterviewLog", back_populates="interview", cascade="all, delete-orphan", order_by="InterviewLog.order_num")
    generated_report = relationship("Report", back_populates="interview", uselist=False, cascade="all, delete-orphan") # Renamed relationship

# 面试问题模型
class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    order_num = Column(Integer, nullable=True)

    interview = relationship("Interview", back_populates="questions")
    # Optional: if you want to navigate from Question to its logs, though less common
    # logs = relationship("InterviewLog", back_populates="question") 

# You might want to add __repr__ methods to your models for easier debugging, e.g.:
# def __repr__(self):
#     return f"<Job(id={self.id}, title='{self.title}')>" 