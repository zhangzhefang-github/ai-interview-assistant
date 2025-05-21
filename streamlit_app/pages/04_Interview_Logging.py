import streamlit as st
from streamlit_app.utils.api_client import APIError, get_interviews, get_interview_logs_api, create_interview_log_api, BACKEND_API_URL # Added BACKEND_API_URL
from streamlit_app.utils.logger_config import get_logger
from datetime import datetime
from streamlit_app.utils.api_client import get_jobs, get_candidates # Re-import for job/candidate maps
from streamlit_app.utils.api_client import get_questions_for_interview
from streamlit_app.utils.api_client import update_interview_api
from app.core.prompts import COMMON_FOLLOW_UP_QUESTIONS # Import the new list
import json # For parsing SSE data
from sseclient import SSEClient # For handling SSE stream
import httpx # SSEClient might use requests, ensure robust http client for API calls if needed elsewhere
from urllib.parse import urljoin # Ensure urljoin is available for constructing SSE URL
from app.api.v1 import schemas # schemas is imported here

# Logger Setup
logger = get_logger(__name__)

logger.info("04_Interview_Logging.py script execution started.")

# st.set_page_config(
#     page_title="面试过程记录 - AI面试助手",
#     page_icon="🎤",
#     layout="wide"
# )

# --- Session State Initialization (if needed for this page) ---
if 'selected_interview_for_logging_id' not in st.session_state:
    st.session_state.selected_interview_for_logging_id = None
if 'selected_interview_display_name' not in st.session_state: # For storing friendly name
    st.session_state.selected_interview_display_name = ""
if 'messages' not in st.session_state: # For chat messages
    st.session_state.messages = []
if 'current_interview_status' not in st.session_state:
    st.session_state.current_interview_status = None

# New session state variables for followup suggestions
if 'followup_suggestions_data' not in st.session_state: # Stores {log_id: {task_id, status, thoughts, suggestions, error}}
    st.session_state.followup_suggestions_data = {}
if 'generating_followup_for_log_id' not in st.session_state: # Tracks which log_id is currently loading suggestions
    st.session_state.generating_followup_for_log_id = None
if 'active_sse_source' not in st.session_state: # To store the active EventSource object if any
    st.session_state.active_sse_source = None
if 'current_chat_input_key' not in st.session_state:
    st.session_state.current_chat_input_key = "chat_input_default" # Key for st.chat_input
if 'last_used_log_id_for_suggestion' not in st.session_state: # Tracks the log_id for which suggestions were last shown expanded
    st.session_state.last_used_log_id_for_suggestion = None
# Placeholders for streaming UI, keyed by log_id
if 'streaming_placeholders' not in st.session_state:
    st.session_state.streaming_placeholders = {}

STATUS_DISPLAY_MAPPING = {
    "PENDING_QUESTIONS": "待生成问题",
    "QUESTIONS_GENERATED": "问题已生成",
    "SCHEDULED": "已安排",
    "LOGGING_COMPLETED": "记录完成",
    "PENDING_REPORT": "待生成报告",
    "REPORT_GENERATED": "报告已生成",
    "ARCHIVED": "已归档",
    "CANCELLED": "已取消",
}

# Helper function to add a message to chat and save to API
def add_message_and_save(interview_id: int, role: str, content: str, speaker_role_value: str, question_id: int = None, question_text_snapshot_override: str = None):
    logger.debug(f"[add_message_and_save] Called for interview_id={interview_id}, role={role}, speaker_role_value={speaker_role_value}, question_id={question_id}, snapshot_override_provided={question_text_snapshot_override is not None}, content snippet: {content[:30]}...")
    # Add to session state for immediate display
    # Determine order_num based on existing messages for this interview
    # This simple order_num might need refinement if messages are fetched paginated or out of order
    current_messages_for_interview = [msg for msg in st.session_state.messages if msg.get('interview_id') == interview_id]
    order_num = len(current_messages_for_interview) + 1
    # Try to get the actual log_id from the API response if this function is called after a save
    # However, this function is called *before* the API call to create_interview_log_api in the current flow
    # So, log_id will be None here for new messages. It will be populated when fetching historical logs.
    log_id_from_creation = None 

    logger.debug(f"[add_message_and_save] Current messages count for interview {interview_id}: {len(current_messages_for_interview)}. New order_num: {order_num}")
    
    new_message_for_display = {
        "interview_id": interview_id, 
        "role": role, 
        "content": content, 
        "question_id": question_id, 
        "order_num": order_num, # Add order_num for display and potential future sorting
        "log_id": log_id_from_creation # Will be None for new messages initially
    }
    # If it's a candidate's answer and we have a snapshot override, add it to display model too for consistency
    if speaker_role_value == "CANDIDATE" and question_text_snapshot_override:
        new_message_for_display['question_text_snapshot'] = question_text_snapshot_override
    elif question_id: # If there's a question_id, try to find its text for display (for interviewer turns)
        # This part might be complex if questions are not pre-loaded or if it's a re-asked q
        # For now, assume pre-loaded questions in sidebar or that content itself for interviewer is the question text.
        pass # Simple display for now.

    st.session_state.messages.append(new_message_for_display)

    # Prepare payload for API
    log_payload = {
        "full_dialogue_text": content,
        "question_id": question_id, 
        "order_num": order_num,
        "speaker_role": speaker_role_value # ADDED speaker_role for backend
    }
    if question_text_snapshot_override:
        log_payload["question_text_snapshot"] = question_text_snapshot_override

    logger.debug(f"[add_message_and_save] Preparing log_payload: {log_payload}")
    try:
        logger.info(f"Saving message for interview {interview_id}: Role: {role}, Content: {content[:50]}..., QID: {question_id}, Order: {order_num}, SnapshotOver: {question_text_snapshot_override is not None}")
        created_log_entry = create_interview_log_api(interview_id, log_payload)
        logger.info(f"Message saved successfully for interview {interview_id}. Log ID: {created_log_entry.get('id')}")
        # Update the message in st.session_state.messages with the actual log_id from response
        for msg in reversed(st.session_state.messages):
            if msg.get('interview_id') == interview_id and msg.get('order_num') == order_num and msg.get('log_id') is None:
                msg['log_id'] = created_log_entry.get('id')
                logger.debug(f"Updated newly added message in session_state with log_id: {created_log_entry.get('id')}")
                break
    except APIError as e:
        st.error(f"保存消息失败: {e.message}")
        logger.error(f"Failed to save message for interview {interview_id}: {e}", exc_info=True)
        # Optionally remove the message from st.session_state.messages if save fails, or mark it as unsaved
        # For simplicity, we'll leave it for now, but a production app might need robust error handling here.
        st.session_state.messages.pop() # Remove optimistic update if save fails

def request_followup_suggestions(interview_id: int, log_id: int):
    logger.critical(f"CRITICAL_DEBUG: BACKEND_API_URL is: '{BACKEND_API_URL}'") # Log the value
    logger.critical(f"CRITICAL_DEBUG: request_followup_suggestions called for interview_id={interview_id}, log_id={log_id}. Button click was registered!")
    logger.info(f"Requesting followup suggestions for interview_id={interview_id}, log_id={log_id}")
    st.session_state.generating_followup_for_log_id = log_id
    st.session_state.followup_suggestions_data[log_id] = {
        "task_id": None,
        "status": "loading", 
        "thoughts": [], 
        "suggestions": [], 
        "error": None
    }
    st.session_state.last_used_log_id_for_suggestion = log_id # Auto-expand for this one

    # Prepare placeholders for this specific log_id if not already done
    # These will be created by show_interview_logging_page when it first renders the expander in loading state
    # Here, we just ensure the keys are initialized in session_state for clarity if needed,
    # but actual st.empty() objects are best managed by the rendering part of the script.
    # It's safer for request_followup_suggestions to just update data in st.session_state,
    # and have the main UI rendering loop pick up these changes when it re-runs or when specific
    # st.empty() instances are updated directly if passed or globally accessible (which is not typical for callbacks).

    # Let's rely on st.empty() instances being updated if they are accessible.
    # The main change will be how these placeholders are populated.

    # Ensure BACKEND_API_URL (e.g. http://localhost:8000) does not end with a slash for this logic
    cleaned_base_url = BACKEND_API_URL.rstrip('/') 

    # BACKEND_API_URL is 'http://localhost:8000/api/v1', so path_segment should start from the next part.
    path_segment = f"/interviews/{interview_id}/logs/{log_id}/generate-followup-stream"
    sse_url = f"{cleaned_base_url}{path_segment}"
    
    logger.debug(f"Attempting to connect to SSE stream with constructed URL: {sse_url}")

    _final_status_for_logging = "unknown" # Variable to hold status for logging in finally block

    try:
        # Using httpx to manually process SSE stream for better control
        with httpx.Client(timeout=None) as client: # Client-level timeout, can be None for no timeout on client ops unless specified in request
            with client.stream("GET", sse_url, timeout=60.0) as response: # Request-specific timeout (e.g., 60 seconds for the entire stream duration if no data for a long time)
                response.raise_for_status() # Check for initial HTTP errors
                logger.info(f"SSE stream connection successful for {sse_url}. Status: {response.status_code}")
                
                current_event_name = None
                current_data_lines = []

                for line in response.iter_lines():
                    line = line.strip()
                    logger.debug(f"SSE raw line: {line}")
                    if not line: # Empty line signifies end of an event
                        if current_event_name and current_data_lines: # current_event_name is the type from "event:"
                            data_str = "\n".join(current_data_lines)
                            logger.debug(f"FRONTEND_SSE_DEBUG: Raw Event Name: '{current_event_name}', Raw Data: '{data_str[:300]}...'") # DETAILED DEBUG LOG
                            try:
                                # data_str is the JSON string from the 'data:' field of the SSE event.
                                # This JSON itself is a serialized AgUiSsePayload.
                                ag_ui_payload_dict = json.loads(data_str) 
                                
                                # The actual business payload for the event (like TaskStartData, ThoughtData, etc.)
                                # IS ag_ui_payload_dict itself, not nested under a "payload" key for sse-starlette.
                                event_data_for_processing = ag_ui_payload_dict # CORRECTED LINE

                                current_data_state = st.session_state.followup_suggestions_data.get(log_id)
                                if not current_data_state: 
                                    logger.warning(f"Log ID {log_id} data disappeared from session state during SSE processing.")
                                    _final_status_for_logging = "error_state_disappeared"
                                    break # Exit loop if state is gone

                                # Use current_event_name (from "event:" line) to determine how to process event_data_for_processing
                                if current_event_name == schemas.AgUiEventType.TASK_START.value:
                                    current_data_state["task_id"] = event_data_for_processing.get("task_id")
                                    current_data_state["status"] = "thinking" # Set status to thinking on task start
                                    current_data_state["thoughts"].append(event_data_for_processing.get("message", "Task started..."))
                                elif current_event_name == schemas.AgUiEventType.THOUGHT.value:
                                    current_data_state["thoughts"].append(event_data_for_processing.get("thought", "Thinking..."))
                                # After updating thoughts in session_state, update the placeholder
                                thoughts_ph = st.session_state.streaming_placeholders.get(log_id, {}).get("thoughts")
                                if thoughts_ph:
                                    thoughts_md = "⏳ AI 思考过程...\n" + "\\n".join([f"> 🧠 {thought}" for thought in current_data_state["thoughts"]])
                                    if current_data_state.get("status") in ["loading", "thinking"]:
                                        thoughts_md += "\\n\\nAI 正在分析并生成追问建议，请稍候..."
                                    thoughts_ph.markdown(thoughts_md)
                                
                                elif current_event_name == schemas.AgUiEventType.QUESTION_CHUNK.value:
                                    # For QUESTION_CHUNK, the payload (event_data_for_processing) is AgUiQuestionChunkData
                                    chunk_text = event_data_for_processing.get("chunk_text", "")
                                    # Optionally update a "thinking/streaming" message here with chunk_text
                                    # current_data_state["thoughts"].append(f"Chunk: {chunk_text[:30]}...") 
                                elif current_event_name == schemas.AgUiEventType.QUESTION_GENERATED.value:
                                    # For QUESTION_GENERATED, the payload (event_data_for_processing) is AgUiQuestionGeneratedData
                                    q_text = event_data_for_processing.get("question_text")
                                    if q_text and q_text not in current_data_state["suggestions"]:
                                        current_data_state["suggestions"].append(q_text)
                                        logger.info(f"LogID {log_id}: Added suggestion: {q_text}")
                                        # After updating suggestions, update the placeholder
                                        suggestions_ph = st.session_state.streaming_placeholders.get(log_id, {}).get("suggestions")
                                        if suggestions_ph:
                                            with suggestions_ph.container():
                                                if current_data_state["suggestions"]: # Check if there are any suggestions
                                                    st.write("AI 建议您可以这样追问：")
                                                    for idx, suggestion_text in enumerate(current_data_state["suggestions"]):
                                                        cols = st.columns([0.85, 0.15])
                                                        with cols[0]:
                                                            st.markdown(f"- {suggestion_text}")
                                                        with cols[1]:
                                                            if st.button("📌 提问", key=f"ask_suggestion_{log_id}_{idx}_{current_event_name}", help="使用此建议提问"): # Added event name to key for more uniqueness
                                                                logger.info(f"User chose to ask AI suggestion for log_id {log_id}: '{suggestion_text}'")
                                                                add_message_and_save(
                                                                    selected_interview_id, 
                                                                    "user",
                                                                    suggestion_text, 
                                                                    speaker_role_value="INTERVIEWER"
                                                                )
                                                                current_data_state["status"] = "used" # Mark as used
                                                                st.session_state.last_used_log_id_for_suggestion = None 
                                                                # Clear placeholders after action
                                                                if st.session_state.streaming_placeholders.get(log_id, {}).get("thoughts"):
                                                                    st.session_state.streaming_placeholders[log_id]["thoughts"].empty()
                                                                if st.session_state.streaming_placeholders.get(log_id, {}).get("suggestions"):
                                                                    st.session_state.streaming_placeholders[log_id]["suggestions"].empty()
                                                                st.rerun() 
                                                else: # No suggestions yet, placeholder should be empty or show a mild "waiting" message
                                                    st.caption("等待AI生成建议...")
                                elif current_event_name == schemas.AgUiEventType.TASK_END.value:
                                    task_successful = event_data_for_processing.get("success", False)
                                    task_message = event_data_for_processing.get("message", "Task ended.")

                                    if task_successful:
                                        current_data_state["status"] = "completed_success"
                                        if not current_data_state["suggestions"]:
                                            current_data_state["error"] = task_message # Or a more specific message like "AI generated no specific suggestions."
                                    else: # Task not successful
                                        current_data_state["status"] = "completed_error"
                                        if not current_data_state["error"]: # Set error only if not already set by a previous ERROR event
                                            current_data_state["error"] = task_message # Message from task_end
                                    
                                    _final_status_for_logging = f"completed_task_end_event_success_{task_successful}"
                                    # Do not break here, let the loop naturally end or timeout if backend keeps stream open
                                elif current_event_name == schemas.AgUiEventType.ERROR.value:
                                    current_data_state["status"] = "error"
                                    current_data_state["error"] = event_data_for_processing.get("error_message", "Unknown error during generation.")
                                    _final_status_for_logging = "error_from_sse_event" 
                                    # Break on explicit error from backend might be desired
                                    # break 
                                
                            except json.JSONDecodeError:
                                logger.warning(f"SSE JSON Decode Error for data: {data_str}")
                                if log_id in st.session_state.followup_suggestions_data: # Check if log_id still exists
                                    st.session_state.followup_suggestions_data[log_id]["error"] = f"Invalid data from AI: {data_str[:50]}"
                                    st.session_state.followup_suggestions_data[log_id]["status"] = "error"
                                _final_status_for_logging = "error_json_decode"
                                break # Break loop on JSON error
                            except Exception as e_proc: # Catch-all for other processing errors
                                logger.error(f"Error processing prepared SSE data '{data_str}': {e_proc}", exc_info=True)
                                if log_id in st.session_state.followup_suggestions_data: # Check if log_id still exists
                                    st.session_state.followup_suggestions_data[log_id]["error"] = f"Client error processing data: {str(e_proc)[:100]}" # Limit error message length
                                    st.session_state.followup_suggestions_data[log_id]["status"] = "error"
                                _final_status_for_logging = "error_processing_event"
                                break # Break loop on other processing error
                        current_data_lines = []
                        current_event_name = None # Reset for next event
                    elif line.startswith("event:"):
                        current_event_name = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        current_data_lines.append(line[len("data:"):].strip())
                    # Ignoring id: and retry: fields for now
        
        # After loop, finalize status if still processing
        if log_id in st.session_state.followup_suggestions_data and \
           st.session_state.followup_suggestions_data[log_id]["status"] in ["loading", "thinking"]:
            st.session_state.followup_suggestions_data[log_id]["status"] = "completed_stream_ended"
            if not st.session_state.followup_suggestions_data[log_id]["suggestions"] and \
               not st.session_state.followup_suggestions_data[log_id]["error"]:
                 st.session_state.followup_suggestions_data[log_id]["error"] = "AI stream ended without suggestions or specific error."
            _final_status_for_logging = st.session_state.followup_suggestions_data[log_id].get("status", "completed_try_block")

    except httpx.HTTPStatusError as http_err_sse:
        logger.error(f"HTTP error connecting to SSE stream {sse_url}: {http_err_sse}", exc_info=True)
        if log_id in st.session_state.followup_suggestions_data:
            st.session_state.followup_suggestions_data[log_id]["error"] = f"Failed to connect to AI suggestion service: {http_err_sse.response.status_code} - {http_err_sse.response.text[:100]}"
            st.session_state.followup_suggestions_data[log_id]["status"] = "error"
            st.session_state.followup_suggestions_data[log_id]["thoughts"] = [] # Clear thoughts
            st.session_state.followup_suggestions_data[log_id]["suggestions"] = [] # Clear suggestions
        _final_status_for_logging = "error_http_status"
    except Exception as e_sse:
        logger.error(f"Generic error with SSE connection or processing for {sse_url}: {e_sse}", exc_info=True)
        if log_id in st.session_state.followup_suggestions_data:
            st.session_state.followup_suggestions_data[log_id]["error"] = f"Error during AI suggestion generation: {str(e_sse)[:100]}"
            st.session_state.followup_suggestions_data[log_id]["status"] = "error"
            st.session_state.followup_suggestions_data[log_id]["thoughts"] = [] # Clear thoughts
            st.session_state.followup_suggestions_data[log_id]["suggestions"] = [] # Clear suggestions
        _final_status_for_logging = "error_generic_exception"
    finally:
        st.session_state.generating_followup_for_log_id = None
        final_status_to_log = _final_status_for_logging if _final_status_for_logging != "unknown" else st.session_state.followup_suggestions_data.get(log_id, {}).get("status", "unknown_fallback")
        logger.info(f"Finished followup suggestion request for log_id={log_id}. Final status for logging: {final_status_to_log}")
        
        # Clear placeholders for this log_id from session_state after stream ends or on error
        # to ensure they are recreated fresh if the user tries again.
        if log_id in st.session_state.streaming_placeholders:
            if st.session_state.streaming_placeholders[log_id].get("thoughts"):
                st.session_state.streaming_placeholders[log_id]["thoughts"].empty() # Clear content
            if st.session_state.streaming_placeholders[log_id].get("suggestions"):
                st.session_state.streaming_placeholders[log_id]["suggestions"].empty() # Clear content
            # Optionally delete the placeholder keys from streaming_placeholders[log_id] itself
            # or just rely on them being empty for next run. For now, emptying content is fine.
            # del st.session_state.streaming_placeholders[log_id] # This would remove the log_id entry

        st.rerun() # Final rerun to clear loading state and show final result/error

def show_interview_logging_page():
    st.header("🎤 面试过程记录 (聊天模式)")
    st.markdown("""
    通过聊天方式记录面试过程。您可以从侧边栏选择预设问题提问，并在下方输入候选人的回答或进行追问。
    """)

    # 1. Select an interview to log
    st.sidebar.subheader("1. 选择面试")
    
    try:
        interviews_for_logging = get_interviews()
    except APIError as e:
        st.error(f"加载面试列表失败：{e.message}")
        return

    if not interviews_for_logging:
        st.info("目前没有已安排或可记录的面试。请先在\"面试管理\"中安排面试并生成问题。")
        return

    try:
        jobs_data = get_jobs()
        candidates_data = get_candidates()
        job_map = {job['id']: job['title'] for job in jobs_data}
        candidate_map = {cand['id']: cand['name'] for cand in candidates_data}
    except APIError:
        job_map = {}
        candidate_map = {}
        st.warning("无法加载职位或候选人信息，部分显示将受影响。")

    interview_options = []
    for interview in interviews_for_logging:
        # Filter for statuses relevant to logging
        if interview.get('status') in ["QUESTIONS_GENERATED", "SCHEDULED", "LOGGING_COMPLETED", "PENDING_REPORT"]:
            candidate_id = interview.get('candidate_id')
            job_id = interview.get('job_id')
            status_key = interview.get('status', "")
            
            candidate_name = candidate_map.get(candidate_id, f"候选人ID:{candidate_id}")
            job_title = job_map.get(job_id, f"职位ID:{job_id}")
            status_display = STATUS_DISPLAY_MAPPING.get(status_key, status_key) # Fallback to key if not in map
            
            # Store a more detailed name for the subheader later
            # And a display name for the selectbox
            option_display_name = f"{candidate_name} ({job_title}) - {status_display}"
            subheader_name = f"{candidate_name} ({job_title})"

            interview_options.append({
                "id": interview.get('id'),
                "display_name": option_display_name,
                "subheader_name": subheader_name, # For the main page subheader
                "status": status_key 
            })

    if not interview_options:
        st.info("当前没有状态适合记录的面试。")
        return

    selected_interview_dict = st.sidebar.selectbox(
        "选择一个面试进行记录",
        options=interview_options,
        format_func=lambda x: x['display_name'] if isinstance(x, dict) else "请选择...",
        index=None,
        key="logging_interview_select_chat"
    )

    if selected_interview_dict:
        selected_interview_id = selected_interview_dict['id']
        current_interview_status = selected_interview_dict['status']

        # If selection changes, clear old messages and load new ones
        if st.session_state.selected_interview_for_logging_id != selected_interview_id:
            st.session_state.messages = [] # Clear messages from previous interview
            st.session_state.selected_interview_for_logging_id = selected_interview_id
            st.session_state.current_interview_status = current_interview_status
            # Store the friendly name for the subheader
            st.session_state.selected_interview_display_name = selected_interview_dict.get("subheader_name", f"面试ID: {selected_interview_id}")
            logger.info(f"Interview selection changed to ID: {selected_interview_id}. Clearing and loading messages.")
            try:
                logger.info(f"Fetching logs for interview ID: {selected_interview_id}")
                historical_logs = get_interview_logs_api(selected_interview_id)
                logger.info(f"Fetched {len(historical_logs)} raw historical log entries for interview ID: {selected_interview_id}.")
                # Backend logs are stored with 'full_dialogue_text'. We need to infer 'role'.
                # Simple inference: if question_id is present, it's likely a 'user' (interviewer) message.
                # Otherwise, assume it's an 'assistant' (candidate) response. This is a heuristic.
                # A more robust way would be to store 'role' in the backend or use a clearer convention.
                # For now, we'll alternate or use question_id as a hint.
                # For simplicity, let's assume logs are already ordered by 'order_num' from backend
                # and we can try to reconstruct role or simply display them sequentially.
                # Let's try a simple alternating role for now, or base it on question_id presence.
                is_question_turn = True # Start by assuming first log might be a question
                for i, log_entry in enumerate(historical_logs):
                    role_for_display = "user" # Default to user/interviewer
                    log_content_snippet = str(log_entry.get("full_dialogue_text", ""))[:30]
                    log_question_id = log_entry.get("question_id")
                    logger.debug(f"  Processing historical log #{i+1}: QID={log_question_id}, Content='{log_content_snippet}...', is_question_turn_before_eval={is_question_turn}")
                    if log_question_id:
                        role_for_display = "user" # Explicitly a question from interviewer
                        is_question_turn = False # Next one is likely an answer
                        logger.debug(f"    Log #{i+1} inferred as USER (has question_id). Next turn is_question_turn={is_question_turn}.")
                    elif not is_question_turn: # If the last was a question, this is an answer
                        role_for_display = "assistant" # Candidate's answer
                        is_question_turn = True # Next one is likely a question
                        logger.debug(f"    Log #{i+1} inferred as ASSISTANT (follows a question). Next turn is_question_turn={is_question_turn}.")
                    else: # Fallback or if it's a user-initiated non-question comment, or first entry without QID
                        role_for_display = "user" # Or could be assistant if it's the very first and no QID
                        is_question_turn = False # Assume next is an answer
                        logger.debug(f"    Log #{i+1} inferred as USER (fallback/first no QID). Next turn is_question_turn={is_question_turn}.")
                       
                    st.session_state.messages.append({
                        "interview_id": selected_interview_id, 
                        "role": role_for_display, 
                        "content": log_entry.get("full_dialogue_text"), 
                        "question_id": log_entry.get("question_id"),
                        "order_num": log_entry.get("order_num", 0), # Use order_num from backend
                        "log_id": log_entry.get("id") # <<< STORE THE ACTUAL LOG ID FROM BACKEND
                    })
                # Ensure messages are sorted by order_num, as they might come unordered or be appended later
                st.session_state.messages.sort(key=lambda x: x.get('order_num', 0))
                logger.info(f"Loaded {len(st.session_state.messages)} historical messages for interview {selected_interview_id}.")
            except APIError as e:
                st.error(f"加载历史聊天记录失败: {e.message}")
                st.session_state.messages = [] # Clear on error too
            logger.info(f"Skipping explicit st.rerun() after loading messages for interview {selected_interview_id} to test responsiveness.")

        # Define common follow-up questions
        # COMMON_FOLLOW_UPS = [
        #     "能否详细说明一下您在其中扮演的具体角色？",
        #     "在这个过程中，您遇到的最大挑战是什么？您是如何克服的？",
        #     "这个项目/经验给您带来的最主要的收获是什么？",
        #     "如果可以重新来一次，您会在哪些方面做得不同？为什么？",
        #     "您是如何量化您提到的这个成果的？有哪些具体数据支撑吗？",
        #     "针对您提到的[某一点]，能再展开讲讲吗？" 
        # ]

        # --- Sidebar: Predefined Questions ---
        st.sidebar.subheader("2. 预设问题")
        try:
            questions = get_questions_for_interview(selected_interview_id)
            if questions:
                for q in questions:
                    question_text = q.get('question_text')
                    question_actual_id = q.get('id') # This is the actual Question.id
                    if st.sidebar.button(f"提问: {question_text[:50]}...", key=f"ask_q_{selected_interview_id}_{question_actual_id}"):
                        logger.info(f"Sidebar '提问' button clicked for interview {selected_interview_id}, question_id {question_actual_id} ('{question_text[:30]}...').")
                        # Check if this question was already asked (by checking messages)
                        # This simple check might not be perfect if questions can be re-asked deliberately
                        already_asked = any(msg.get('question_id') == question_actual_id and msg.get('role') == 'user' for msg in st.session_state.messages if msg.get('interview_id') == selected_interview_id)
                        if not already_asked or st.checkbox("再次提问此问题？", key=f"reask_confirm_{question_actual_id}", value=False):
                            add_message_and_save(selected_interview_id, "user", question_text, speaker_role_value="INTERVIEWER", question_id=question_actual_id)
                            st.rerun()
                        elif already_asked:
                            st.sidebar.warning("此问题已提问过。")
            else:
                st.sidebar.info("该面试没有找到预设问题。")
        except APIError as e:
            st.sidebar.warning(f"加载面试问题失败: {e.message}")

        # --- Main Area: Chat Interface ---
        # Use the stored friendly name for the subheader
        subheader_title = st.session_state.get("selected_interview_display_name", f"记录面试对话 (面试ID: {st.session_state.selected_interview_for_logging_id})")
        st.subheader(subheader_title)
        
        # Display chat messages from history
        chat_container = st.container()
        with chat_container:
            for message_idx, message in enumerate(st.session_state.messages):
                # Only display messages for the currently selected interview
                if message.get("interview_id") == selected_interview_id:
                    # Use a unique key for each chat message block if needed, e.g. f"chat_msg_block_{selected_interview_id}_{message.get('log_id', message_idx)}"
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        if message.get("question_id") and message["role"] == "user":
                            st.caption(f"(基于预设问题 ID: {message['question_id']}) Log ID: {message.get('log_id')}")
                        elif message["role"] == "assistant": # Candidate's answer
                            st.caption(f"Log ID: {message.get('log_id')}") # Display log_id for candidate answers too

                    # AI Followup Suggestions Section for candidate's answers
                    if message["role"] == "assistant" and message.get("log_id") is not None:
                        log_id = message.get("log_id")
                        suggestion_data = st.session_state.followup_suggestions_data.get(log_id)
                        
                        # Determine if this expander should be open by default
                        is_active_suggestion_log = (st.session_state.last_used_log_id_for_suggestion == log_id)
                        expand_this = is_active_suggestion_log

                        # Button to trigger suggestion generation
                        if st.session_state.generating_followup_for_log_id == log_id and suggestion_data and suggestion_data.get("status") == "loading":
                            st.button("✨ AI正在生成追问建议...", disabled=True, key=f"loading_followup_btn_{log_id}")
                        elif not suggestion_data or suggestion_data.get("status") == "initial" or suggestion_data.get("status") == "used": # Allow re-generation if used
                            if st.button("✨ 获取AI追问建议", key=f"get_followup_btn_{log_id}", on_click=request_followup_suggestions, args=(selected_interview_id, log_id)):
                                # When button is clicked, request_followup_suggestions will set generating_followup_for_log_id
                                # And the next rerun will create the placeholders.
                                pass 
                        
                        if suggestion_data:
                            with st.expander("AI 追问建议", expanded=expand_this):
                                if st.session_state.generating_followup_for_log_id == log_id :
                                    # Create/get placeholders if we are actively generating for this log_id
                                    if log_id not in st.session_state.streaming_placeholders:
                                        st.session_state.streaming_placeholders[log_id] = {
                                            "thoughts": st.empty(),
                                            "suggestions": st.empty()
                                        }
                                    
                                    # Initial rendering of placeholders (will be updated by the callback)
                                    # Thoughts placeholder will be populated by the callback
                                    st.session_state.streaming_placeholders[log_id]["thoughts"].markdown("⏳ AI 思考过程...\nAI 正在分析并生成追问建议，请稍候...")
                                    # Suggestions placeholder initially empty or with a waiting message
                                    with st.session_state.streaming_placeholders[log_id]["suggestions"].container():
                                        st.caption("等待AI生成建议...")

                                elif suggestion_data.get("error"): # PRIORITIZE ERROR DISPLAY if not loading
                                    st.error(f"无法获取追问建议: {suggestion_data['error']}")
                                
                                elif suggestion_data.get("suggestions"): # Display suggestions if already generated and not currently loading
                                    st.write("AI 建议您可以这样追问：")
                                    for idx, suggestion_text in enumerate(suggestion_data["suggestions"]):
                                        cols = st.columns([0.85, 0.15])
                                        with cols[0]:
                                            st.markdown(f"- {suggestion_text}")
                                        with cols[1]:
                                            if st.button("📌 提问", key=f"ask_suggestion_{log_id}_{idx}_static", help="使用此建议提问"):
                                                logger.info(f"User chose to ask AI suggestion for log_id {log_id}: '{suggestion_text}'")
                                                add_message_and_save(
                                                    selected_interview_id, 
                                                    "user", 
                                                    suggestion_text, 
                                                    speaker_role_value="INTERVIEWER"
                                                )
                                                suggestion_data["status"] = "used" # Mark as used
                                                st.session_state.last_used_log_id_for_suggestion = None 
                                                st.rerun()
                                elif suggestion_data.get("status") not in ["loading", "thinking", "used"] and not suggestion_data.get("error"):
                                    st.caption("AI 未能生成具体的追问建议，或建议已被使用。")

        # Popover for common follow-up questions - MOVED OUT OF THE LOOP
        # Placed before chat input for visibility.
        with st.popover("💡 常用追问角度", help="点击选择一个常用追问问题发送", use_container_width=False):
            # The label of st.popover itself is the button.
            # The use_container_width=False here applies to the popover's button appearance.
            # You can adjust use_container_width for the button if needed, or use st.columns for layout.
            st.markdown("点击下方问题可直接作为您的问题发送：")
            for i, followup_text in enumerate(COMMON_FOLLOW_UP_QUESTIONS):
                # Ensure unique keys for buttons inside the popover, even if popover is re-rendered.
                # The selected_interview_id makes it unique per interview session if multiple are somehow on page.
                button_key = f"popover_followup_{selected_interview_id}_{i}"
                if st.button(followup_text, key=button_key, use_container_width=True):
                    logger.info(f"Popover follow-up button clicked: '{followup_text}' for interview {selected_interview_id}.")
                    add_message_and_save(selected_interview_id, "user", followup_text, speaker_role_value="INTERVIEWER")
                    # Popovers auto-close on button click inside them if that button causes a rerun.
                    st.rerun() # Rerun to update the main chat display

        # Chat input
        # Determine the role for the next input. Simplistic: if last message was user (question), next is assistant (answer).
        # This needs to be more robust for free-form conversation.
        last_message_role = st.session_state.messages[-1]["role"] if st.session_state.messages and st.session_state.messages[-1].get("interview_id") == selected_interview_id else None
        
        input_prompt = "记录候选人回答..."
        current_input_role = "assistant" # Default to assistant (candidate's answer)
        
        if not last_message_role or last_message_role == "assistant":
            input_prompt = "输入面试官问题/追问..."
            current_input_role = "user"
        logger.debug(f"Chat input ready for interview {selected_interview_id}. last_message_role: '{last_message_role}', determined current_input_role: '{current_input_role}', prompt: '{input_prompt}'.")

        if prompt := st.chat_input(input_prompt, key=f"chat_input_{selected_interview_id}"):
            logger.info(f"Chat input submitted for interview {selected_interview_id}. Role: '{current_input_role}', Prompt: '{prompt[:50]}...'.")
            
            backend_speaker_role = "INTERVIEWER" if current_input_role == "user" else "CANDIDATE"
            
            # Variables to pass to add_message_and_save
            q_id_for_log = None
            q_text_snapshot_for_log = None

            if backend_speaker_role == "CANDIDATE":
                # This is a candidate's answer. Try to find the last interviewer question.
                for msg_idx in range(len(st.session_state.messages) - 1, -1, -1):
                    prev_msg = st.session_state.messages[msg_idx]
                    if prev_msg.get("interview_id") == selected_interview_id and prev_msg.get("role") == "user": # "user" is INTERVIEWER in chat
                        q_id_for_log = prev_msg.get("question_id") # May be None if ad-hoc
                        q_text_snapshot_for_log = prev_msg.get("content") # Always get content as snapshot for ad-hoc
                        logger.debug(f"Candidate answer for interview {selected_interview_id}. Associated with QID: {q_id_for_log}, QText: '{q_text_snapshot_for_log[:30]}...'")
                        break
                # If q_id_for_log is None (i.e., it was an ad-hoc interviewer question), 
                # q_text_snapshot_for_log (the ad-hoc question text) will be passed as override.
                # If q_id_for_log is NOT None, backend will use it to fetch snapshot if override is not provided.
                # So, if we have q_id_for_log, we don't *need* to send q_text_snapshot_for_log, 
                # but sending it if available (especially for ad-hoc) is safer.
                add_message_and_save(
                    selected_interview_id, 
                    current_input_role,  
                    prompt, 
                    speaker_role_value=backend_speaker_role,
                    question_id=q_id_for_log,
                    question_text_snapshot_override=q_text_snapshot_for_log # Pass the snapshot
                )
            else: # INTERVIEWER's message (a question or a comment)
                # If interviewer types a question, it won't have a question_id from DB initially.
                # The question_text_snapshot will be its own content if a candidate answers it later.
                add_message_and_save(
                    selected_interview_id, 
                    current_input_role, 
                    prompt, 
                    speaker_role_value=backend_speaker_role
                    # question_id is None here, question_text_snapshot_override is None
                )
            st.rerun()
        
        st.divider()
        # --- End Interview Section ---
        if st.session_state.current_interview_status != "LOGGING_COMPLETED":
            if st.button('结束并标记为"记录完成"', key=f"complete_logging_{selected_interview_id}"):
                logger.info(f"'结束并标记为记录完成' button clicked for interview ID: {selected_interview_id}.")
                try:
                    update_payload = {"status": "LOGGING_COMPLETED"}
                    logger.debug(f"Updating interview {selected_interview_id} status with payload: {update_payload}")
                    update_interview_api(selected_interview_id, update_payload)
                    st.success(f'面试 ID {selected_interview_id} 已标记为"记录完成"。')
                    st.session_state.current_interview_status = "LOGGING_COMPLETED" # Update local status
                    logger.info(f"Interview {selected_interview_id} status successfully updated to LOGGING_COMPLETED locally and via API.")
                    # Optionally, disable further input or refresh interview options
                    st.rerun()
                except APIError as e:
                    st.error(f"更新面试状态失败: {e.message}")
                    logger.error(f"Failed to update interview {selected_interview_id} status to LOGGING_COMPLETED: {e}", exc_info=True)
        else:
            st.info('此面试已标记为"记录完成"。如需修改，请在其他地方调整状态。')

    else:
        st.info("请从侧边栏选择一个面试开始记录。")

def main():
    show_interview_logging_page()

if __name__ == "__main__":
    main()

logger.info("04_Interview_Logging.py script execution completed.") 