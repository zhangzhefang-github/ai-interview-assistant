import streamlit as st
from streamlit_app.utils.api_client import APIError, get_interviews, get_interview_logs_api, create_interview_log_api # Added new log APIs
from streamlit_app.utils.logger_config import get_logger
from datetime import datetime
from streamlit_app.utils.api_client import get_jobs, get_candidates # Re-import for job/candidate maps
from streamlit_app.utils.api_client import get_questions_for_interview
from streamlit_app.utils.api_client import update_interview_api
from app.core.prompts import COMMON_FOLLOW_UP_QUESTIONS # Import the new list

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
def add_message_and_save(interview_id: int, role: str, content: str, question_id: int = None):
    logger.debug(f"[add_message_and_save] Called for interview_id={interview_id}, role={role}, question_id={question_id}, content snippet: {content[:30]}...")
    # Add to session state for immediate display
    # Determine order_num based on existing messages for this interview
    # This simple order_num might need refinement if messages are fetched paginated or out of order
    current_messages_for_interview = [msg for msg in st.session_state.messages if msg.get('interview_id') == interview_id]
    order_num = len(current_messages_for_interview) + 1
    logger.debug(f"[add_message_and_save] Current messages count for interview {interview_id}: {len(current_messages_for_interview)}. New order_num: {order_num}")
    
    new_message_for_display = {
        "interview_id": interview_id, 
        "role": role, 
        "content": content, 
        "question_id": question_id, 
        "order_num": order_num # Add order_num for display and potential future sorting
    }
    st.session_state.messages.append(new_message_for_display)

    # Prepare payload for API
    log_payload = {
        "full_dialogue_text": content,
        # "role": role, # Our backend schema for InterviewLogCreate expects full_dialogue_text, not role directly.
        # The 'role' is more for display logic on the frontend or if the backend wants to store it separately.
        # For now, full_dialogue_text will contain the Q or A.
        # We can infer Q/A based on the order or a convention (e.g. user=Q, assistant=A)
        "question_id": question_id, 
        "order_num": order_num
    }

    logger.debug(f"[add_message_and_save] Preparing log_payload: {log_payload}")
    try:
        logger.info(f"Saving message for interview {interview_id}: Role: {role}, Content: {content[:50]}..., QID: {question_id}, Order: {order_num}")
        create_interview_log_api(interview_id, log_payload)
        logger.info(f"Message saved successfully for interview {interview_id}.")
    except APIError as e:
        st.error(f"保存消息失败: {e.message}")
        logger.error(f"Failed to save message for interview {interview_id}: {e}", exc_info=True)
        # Optionally remove the message from st.session_state.messages if save fails, or mark it as unsaved
        # For simplicity, we'll leave it for now, but a production app might need robust error handling here.
        st.session_state.messages.pop() # Remove optimistic update if save fails

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
                        "order_num": log_entry.get("order_num", 0) # Use order_num from backend
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
                            add_message_and_save(selected_interview_id, "user", question_text, question_id=question_actual_id)
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
            for message in st.session_state.messages:
                # Only display messages for the currently selected interview
                if message.get("interview_id") == selected_interview_id:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        if message.get("question_id") and message["role"] == "user":
                            st.caption(f"(基于预设问题 ID: {message['question_id']})")
                    
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
                    add_message_and_save(selected_interview_id, "user", followup_text)
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
            add_message_and_save(selected_interview_id, current_input_role, prompt)
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