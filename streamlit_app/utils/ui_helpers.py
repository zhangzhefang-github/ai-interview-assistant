from typing import Optional

# Define InterviewStatus Enum values as used in the backend
# This helps with code completion and reduces typos.
# These should ideally match the app.db.models.InterviewStatus enum members.
class InterviewStatusKey:
    PENDING_QUESTIONS = "PENDING_QUESTIONS"
    QUESTIONS_GENERATED = "QUESTIONS_GENERATED"
    QUESTIONS_FAILED = "QUESTIONS_FAILED"  # Added based on backend logic
    LOGGING_COMPLETED = "LOGGING_COMPLETED"
    REPORT_GENERATED = "REPORT_GENERATED"
    # Add other statuses here as they are defined in the backend

INTERVIEW_STATUS_MAP_ZH = {
    InterviewStatusKey.PENDING_QUESTIONS: "📝 待处理：生成问题中", # Emoji for visual cue
    InterviewStatusKey.QUESTIONS_GENERATED: "✅ 问题已生成",
    InterviewStatusKey.QUESTIONS_FAILED: "❌ 问题生成失败",
    InterviewStatusKey.LOGGING_COMPLETED: "🗣️ 面试已记录", # More user-friendly than "Logging Completed"
    InterviewStatusKey.REPORT_GENERATED: "📊 报告已生成",
    # Default fallback message for unknown statuses
    "UNKNOWN_STATUS": "🤷 未知状态" 
}

def get_status_display_name_zh(status_key: Optional[str]) -> str:
    """
    Returns the Chinese display name for a given interview status key.
    Returns a default 'Unknown Status' message if the key is not found or is None.
    """
    if status_key is None:
        return INTERVIEW_STATUS_MAP_ZH.get("UNKNOWN_STATUS", "状态未知")
    return INTERVIEW_STATUS_MAP_ZH.get(status_key, INTERVIEW_STATUS_MAP_ZH.get("UNKNOWN_STATUS", f"状态: {status_key}"))

# Example usage (for testing or if this file is run directly):
if __name__ == '__main__':
    print(f"'{InterviewStatusKey.PENDING_QUESTIONS}' -> '{get_status_display_name_zh(InterviewStatusKey.PENDING_QUESTIONS)}'")
    print(f"'{InterviewStatusKey.REPORT_GENERATED}' -> '{get_status_display_name_zh(InterviewStatusKey.REPORT_GENERATED)}'")
    print(f"'NON_EXISTENT_STATUS' -> '{get_status_display_name_zh('NON_EXISTENT_STATUS')}'")
    print(f"None -> '{get_status_display_name_zh(None)}'") 