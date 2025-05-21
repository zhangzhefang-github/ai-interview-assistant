from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class AgUiEventType(str, Enum):
    TASK_START = "task_start"
    THOUGHT = "thought" # For intermediate steps or reasoning
    QUESTION_CHUNK = "question_chunk" # For streaming parts of a question
    QUESTION_GENERATED = "question_generated" # When a full question is ready
    TASK_END = "task_end"
    ERROR = "error"

class AgUiBaseEventData(BaseModel):
    task_id: str
    task_name: Optional[str] = None

class AgUiTaskStartData(AgUiBaseEventData):
    message: Optional[str] = None

class AgUiThoughtData(AgUiBaseEventData):
    thought: str

class AgUiQuestionChunkData(AgUiBaseEventData):
    chunk_text: str
    is_partial: bool = True

class AgUiQuestionGeneratedData(AgUiBaseEventData):
    question_text: str
    question_order: Optional[int] = None
    total_questions: int
    category: Optional[str] = None
    # Potentially other metadata about the question

class QuestionDetail(BaseModel):
    text: str
    order: int

class AgUiTaskEndData(AgUiBaseEventData):
    status: str # e.g., "success", "failure"
    message: Optional[str] = None
    final_questions: Optional[List[QuestionDetail]] = None

class AgUiErrorData(AgUiBaseEventData):
    error_message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AgUiEvent(BaseModel):
    event: AgUiEventType
    data: Dict[str, Any] # Using Dict for flexibility, will be one of the above data models serialized

# Example of how one might structure the actual SSE data payload
class AgUiSsePayload(BaseModel):
    event_type: AgUiEventType
    payload: Dict[str, Any] # This would be AgUiTaskStartData, AgUiThoughtData etc.

    def to_sse_format(self) -> str:
        import json
        return f"event: {self.event_type.value}\\ndata: {json.dumps(self.payload)}\\n\\n"

# More specific event models for clarity if preferred over generic AgUiEvent
class AgUiTaskStartEvent(BaseModel):
    event: AgUiEventType = AgUiEventType.TASK_START
    data: AgUiTaskStartData

class AgUiThoughtEvent(BaseModel):
    event: AgUiEventType = AgUiEventType.THOUGHT
    data: AgUiThoughtData

class AgUiQuestionChunkEvent(BaseModel):
    event: AgUiEventType = AgUiEventType.QUESTION_CHUNK
    data: AgUiQuestionChunkData

class AgUiQuestionGeneratedEvent(BaseModel):
    event: AgUiEventType = AgUiEventType.QUESTION_GENERATED
    data: AgUiQuestionGeneratedData

class AgUiTaskEndEvent(BaseModel):
    event: AgUiEventType = AgUiEventType.TASK_END
    data: AgUiTaskEndData

class AgUiErrorEvent(BaseModel):
    event: AgUiEventType = AgUiEventType.ERROR
    data: AgUiErrorData 