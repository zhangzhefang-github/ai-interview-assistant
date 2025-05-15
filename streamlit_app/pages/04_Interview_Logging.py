import streamlit as st
from streamlit_app.utils.api_client import APIError, get_interviews # Placeholder for new API client functions
from streamlit_app.utils.logger_config import get_logger
from datetime import datetime
from streamlit_app.utils.api_client import get_jobs, get_candidates # Re-import for job/candidate maps
from streamlit_app.utils.api_client import get_questions_for_interview
from streamlit_app.utils.api_client import update_interview_api

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
if 'current_log_text' not in st.session_state: # To hold text area content
    st.session_state.current_log_text = ""


def show_interview_logging_page():
    st.header("🎤 面试过程记录")
    st.markdown("""
    在此页面记录面试过程中的关键对话、候选人回答、以及您的观察和笔记。
    这些记录将用于后续生成 AI 评估报告。
    """)

    # 1. Select an interview to log
    st.subheader("1. 选择要记录的面试")
    
    try:
        # We need a way to filter interviews that are ready for logging 
        # (e.g., status 'QUESTIONS_GENERATED' or 'SCHEDULED')
        # For MVP, let's get all interviews and let user pick.
        # Potentially, api_client.get_interviews could take a status filter.
        interviews_for_logging = get_interviews() # Assuming this fetches necessary details or we make another call
    except APIError as e:
        st.error(f"加载面试列表失败：{e.message}")
        logger.error(f"Failed to load interviews for logging page: {e}", exc_info=True)
        return

    if not interviews_for_logging:
        st.info("目前没有已安排或可记录的面试。请先在\"面试管理\"中安排面试并生成问题。")
        return

    # Prepare interview options for selectbox
    # We need job title and candidate name for display
    # This might require get_interviews to return enriched data or make additional calls
    # For now, let's assume interview objects have job_id, candidate_id, and we have job_map, candidate_map logic similar to 03_Interview_Management
    
    # Simplified: Using a helper or fetching all jobs/candidates again (not ideal for performance but ok for MVP)
    try:
        jobs_data = get_jobs()
        candidates_data = get_candidates()
        job_map = {job['id']: job['title'] for job in jobs_data}
        candidate_map = {cand['id']: cand['name'] for cand in candidates_data}
    except APIError: # Handle error if job/candidate fetching fails
        job_map = {}
        candidate_map = {}
        st.warning("无法加载职位或候选人信息，面试选择可能不完整。")


    interview_options = []
    for interview in interviews_for_logging:
        # Filter for statuses that make sense for logging
        if interview.get('status') in ["QUESTIONS_GENERATED", "SCHEDULED", "PENDING_REPORT", "LOGGING_COMPLETED"]: # Added more states
            job_title = job_map.get(interview.get('job_id'), f"Job ID: {interview.get('job_id')}")
            candidate_name = candidate_map.get(interview.get('candidate_id'), f"Cand. ID: {interview.get('candidate_id')}")
            scheduled_at_str = interview.get('scheduled_at')
            display_time = ""
            if scheduled_at_str:
                try:
                    dt_obj = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
                    display_time = f"({dt_obj.strftime('%Y-%m-%d %H:%M')})"
                except ValueError:
                    display_time = "(时间格式错误)"
            
            interview_options.append({
                "id": interview.get('id'),
                "display_name": f"ID: {interview.get('id')} - {job_title} / {candidate_name} {display_time}"
            })

    if not interview_options:
        st.info("当前没有状态适合记录的面试（如：问题已生成、已安排等）。")
        return

    selected_interview_dict = st.selectbox(
        "选择一个面试进行记录",
        options=interview_options,
        format_func=lambda x: x['display_name'] if isinstance(x, dict) else "请选择...",
        index=None, # Allow no selection initially
        key="logging_interview_select" 
    )

    if selected_interview_dict:
        selected_interview_id = selected_interview_dict['id']
        
        st.divider()
        st.subheader(f"2. 面试问题与记录区 (面试 ID: {selected_interview_id})")

        # Placeholder: Fetch and display interview details (Job, Candidate, Questions)
        # For MVP, we might just show questions. An API like get_interview_details(interview_id) would be good.
        # This API should return interview obj, job obj, candidate obj, list of questions.
        
        # For now, let's assume we have a way to get questions (e.g., from 03_Interview_Management's API client)
        try:
            questions = get_questions_for_interview(selected_interview_id)
            if questions:
                st.markdown("**参考面试问题:**")
                with st.expander("点击展开/折叠问题列表", expanded=False):
                    for q in questions:
                        st.markdown(f"- {q.get('question_text')}")
            else:
                st.info("该面试没有找到关联的问题。")
        except APIError as e:
            st.warning(f"加载面试问题失败: {e.message}")
            questions = []


        # 3. Logging Area
        session_key_for_log = f"interview_log_{selected_interview_id}"
        retrieved_log_value = st.session_state.get(session_key_for_log, "")

        current_log = st.text_area(
            "在此记录面试过程", 
            value=retrieved_log_value, 
            height=400,
            key=f"log_text_area_{selected_interview_id}"
        )
        
        if st.button("💾 保存面试记录", key=f"save_log_{selected_interview_id}"):
            if not current_log.strip():
                st.warning("面试记录不能为空。")
            else:
                try:
                    update_payload = {"conversation_log": current_log, "status": "LOGGING_COMPLETED"}
                    
                    logger.info(f"Calling update_interview_api for interview_id: {selected_interview_id} to save log.") # Adjusted log message
                    update_interview_api(selected_interview_id, update_payload)
                    st.success(f"面试 ID {selected_interview_id} 的记录已保存！状态更新为 LOGGING_COMPLETED.")
                    
                    st.session_state[session_key_for_log] = current_log
                    
                except APIError as e:
                    st.error(f"保存面试记录失败: {e.message}")
    else:
        st.info("请从上方选择一个面试开始记录。")


def main():
    show_interview_logging_page()

if __name__ == "__main__":
    main()

logger.info("04_Interview_Logging.py script execution completed.") 