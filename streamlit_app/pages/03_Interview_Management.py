import streamlit as st
from streamlit_app.utils.api_client import APIError, get_jobs, get_candidates, create_interview, get_interviews, generate_interview_questions_for_interview, get_questions_for_interview, update_interview_api, delete_interview_api
from streamlit_app.utils.logger_config import get_logger
from datetime import datetime, date, time # Added date and time for input combination
from typing import Optional
# Import other necessary API client functions like get_jobs, get_candidates, create_interview etc. later

# Call st.set_page_config as the first Streamlit command - REMOVED FROM HERE
# st.set_page_config(page_title="面试管理 - AI助手", layout="wide") 

logger = get_logger(__name__)

logger.info("03_Interview_Management.py page loading...")

# --- Session State Initialization ---
if 'interview_form_job_id' not in st.session_state:
    st.session_state.interview_form_job_id = None
if 'interview_form_candidate_id' not in st.session_state:
    st.session_state.interview_form_candidate_id = None
if 'expanded_interview_questions' not in st.session_state: # For toggling question display
    st.session_state.expanded_interview_questions = None
if 'loaded_questions' not in st.session_state: # To store fetched questions
    st.session_state.loaded_questions = {}
if 'editing_interview_id' not in st.session_state: # For edit dialog
    st.session_state.editing_interview_id = None
if 'interview_to_delete' not in st.session_state: # For delete confirmation
    st.session_state.interview_to_delete = None

# Define status mapping
STATUS_DISPLAY_MAPPING = {
    "PENDING_QUESTIONS": "待生成问题",
    "QUESTIONS_GENERATED": "问题已生成",
    "SCHEDULED": "已安排",
    "COMPLETED": "已完成",
    "CANCELED": "已取消",
    # Add other statuses as needed
}

@st.dialog("编辑面试信息")
def edit_interview_dialog(interview: dict):
    st.subheader(f"编辑面试 ID: {interview.get('id')}")

    # Prepare current values
    current_scheduled_at_str = interview.get('scheduled_at')
    current_scheduled_date = None
    current_scheduled_time = None
    if current_scheduled_at_str:
        try:
            dt_obj = datetime.fromisoformat(current_scheduled_at_str.replace("Z", "+00:00"))
            current_scheduled_date = dt_obj.date()
            current_scheduled_time = dt_obj.time()
        except ValueError:
            logger.warning(f"Could not parse scheduled_at string '{current_scheduled_at_str}' for interview {interview.get('id')}")

    current_status = interview.get('status', "PENDING_QUESTIONS")
    
    # Status options for selectbox (use keys from mapping)
    status_options = list(STATUS_DISPLAY_MAPPING.keys())
    try:
        current_status_index = status_options.index(current_status) if current_status in status_options else 0
    except ValueError:
        current_status_index = 0


    with st.form("edit_interview_form_in_dialog"):
        new_interview_date = st.date_input(
            "新的面试日期", 
            value=current_scheduled_date, 
            min_value=date.today() if not current_scheduled_date or current_scheduled_date < date.today() else current_scheduled_date
        )
        new_interview_time = st.time_input("新的面试时间", value=current_scheduled_time)
        
        new_status = st.selectbox(
            "面试状态", 
            options=status_options, 
            index=current_status_index,
            format_func=lambda x: STATUS_DISPLAY_MAPPING.get(x, x)
        )

        # Buttons in the same row
        col_save, col_cancel = st.columns(2)
        with col_save:
            save_button = st.form_submit_button("更新", use_container_width=True) # Changed text to "更新"
        with col_cancel:
            cancel_button = st.form_submit_button("取消", type="secondary", use_container_width=True)

        if save_button: # Check if save button was pressed
            updated_data = {}
            if new_interview_date and new_interview_time:
                updated_data["scheduled_at"] = datetime.combine(new_interview_date, new_interview_time).isoformat()
            elif new_interview_date and not new_interview_time: # Only date provided
                 st.warning("请同时提供日期和时间以更新面试时间，或清除日期以移除时间。当前未做更改。", icon="⚠️")
                 # Or, decide to clear scheduled_at if only date is given and time is None
                 # updated_data["scheduled_at"] = None # To clear if desired
            elif not new_interview_date and not new_interview_time: # Both cleared
                updated_data["scheduled_at"] = None


            if new_status != current_status:
                updated_data["status"] = new_status
            
            if not updated_data:
                st.info("没有检测到更改。")
                st.session_state.editing_interview_id = None # Close dialog
                st.rerun()
                return

            try:
                logger.info(f"Attempting to update interview ID {interview.get('id')} with data: {updated_data}")
                update_interview_api(interview.get('id'), updated_data)
                st.success(f"面试 ID {interview.get('id')} 更新成功！")
                st.session_state.editing_interview_id = None # Close dialog
                st.rerun()
            except APIError as e:
                logger.error(f"APIError updating interview {interview.get('id')}: {e.message}", exc_info=True)
                st.error(f"更新面试失败：{e.message}")
            except Exception as ex:
                logger.error(f"Unexpected error updating interview {interview.get('id')}: {ex}", exc_info=True)
                st.error(f"更新面试时发生意外错误: {str(ex)}")
        
        if cancel_button: # Check if cancel button was pressed
            st.session_state.editing_interview_id = None
            st.rerun()


def show_interview_management_page():
    st.header("🎙️ 面试管理")
    st.markdown("""
    管理和安排候选人的面试流程。您可以创建新的面试，为面试生成定制化问题，并跟踪面试状态。
    """)

    # --- Section: Arrange New Interview ---
    st.subheader("🗓️ 安排新面试")
    
    try:
        jobs_data = get_jobs()
        candidates_data = get_candidates()
    except APIError as e:
        st.error(f"加载职位或候选人列表失败：{e.message}")
        logger.error(f"Failed to load jobs or candidates for interview form: {e}", exc_info=True)
        # Prevent rendering the form if essential data is missing
        return 

    if not jobs_data:
        st.warning("系统中没有职位信息，请先创建职位后再安排面试。", icon="⚠️")
        return
    if not candidates_data:
        st.warning("系统中没有候选人信息，请先添加候选人后再安排面试。", icon="⚠️")
        return

    # Prepare options for select boxes
    # Store as list of dicts to preserve ID and name for submission and display
    job_options = [{ "id": job['id'], "name": job['title']} for job in jobs_data]
    candidate_options = [{ "id": cand['id'], "name": cand['name']} for cand in candidates_data]

    with st.form("new_interview_form", clear_on_submit=True):
        st.write("请选择职位和候选人来安排一场新的面试：")
        
        # Use format_func to display the name, the selectbox will return the whole dict
        selected_job_dict = st.selectbox(
            "选择职位", 
            options=job_options, 
            format_func=lambda x: x['name'] if isinstance(x, dict) else "请选择职位",
            index=None,
            placeholder="请选择一个职位..."
        )
        
        selected_candidate_dict = st.selectbox(
            "选择候选人", 
            options=candidate_options, 
            format_func=lambda x: x['name'] if isinstance(x, dict) else "请选择候选人",
            index=None,
            placeholder="请选择一位候选人..."
        )
        
        # Interview Date and Time input
        col1, col2 = st.columns(2)
        with col1:
            interview_date = st.date_input("面试日期", value=None, min_value=date.today())
        with col2:
            interview_time_val = st.time_input("面试时间", value=None) # step=timedelta(minutes=30) can be added

        # Optional: Add fields for interview date, time, status later
        # interview_status = st.selectbox("面试状态", ["PENDING_QUESTIONS", "SCHEDULED", "COMPLETED"]) 

        submit_button = st.form_submit_button("确认安排面试")

        if submit_button:
            if not selected_job_dict or not selected_candidate_dict:
                st.warning("请务必选择一个职位和一位候选人。")
            else:
                job_id = selected_job_dict['id']
                candidate_id = selected_candidate_dict['id']
                job_name = selected_job_dict['name']
                candidate_name = selected_candidate_dict['name']
                
                # Combine date and time for scheduled_at
                scheduled_at_dt: Optional[datetime] = None
                if interview_date and interview_time_val:
                    scheduled_at_dt = datetime.combine(interview_date, interview_time_val)
                elif interview_date: # If only date is provided, maybe default time or handle as error/incomplete
                    # For now, we will only pass scheduled_at if both date and time are provided
                    # Or you might decide to default to a specific time, e.g., datetime.combine(interview_date, time(9,0))
                    st.warning("请同时提供面试日期和时间，否则将不会设置面试时间。")
                    # Alternatively, make time mandatory if date is provided.
                
                logger.info(f"Attempting to create interview for Job ID: {job_id} ('{job_name}') and Candidate ID: {candidate_id} ('{candidate_name}') with scheduled_at: {scheduled_at_dt}")
                try:
                    # Pass scheduled_at to create_interview. API client needs to be updated.
                    created_interview = create_interview(
                        job_id=job_id, 
                        candidate_id=candidate_id,
                        scheduled_at=scheduled_at_dt.isoformat() if scheduled_at_dt else None
                        # status="PENDING_QUESTIONS" # Default status is handled by schema/model or backend
                    )
                    success_msg = f"🎉 面试安排成功！职位: '{job_name}', 候选人: '{candidate_name}'. 面试ID: {created_interview.get('id')}"
                    if scheduled_at_dt:
                        success_msg += f", 时间: {scheduled_at_dt.strftime('%Y-%m-%d %H:%M')}"
                    st.success(success_msg)
                    logger.info(f"Successfully created interview: {created_interview}")
                    # TODO: Potentially clear selectbox or navigate to interview details
                    st.rerun()
                except APIError as e:
                    logger.error(f"APIError while creating interview for job {job_name}, cand {candidate_name}: {e.message}", exc_info=True)
                    st.error(f"安排面试失败：{e.message}")
                    if e.details: st.error(f"详细信息：{e.details}")
                except Exception as e:
                    logger.error(f"Unexpected error while creating interview: {e}", exc_info=True)
                    st.error(f"安排面试时发生意外错误：{str(e)}")

    st.divider()

    # --- Section: Display Existing Interviews ---
    st.subheader("📋 现有面试列表")
    
    try:
        interviews = get_interviews()
        # We already have jobs_data and candidates_data from the "Arrange New Interview" section loading
        # If that section failed, we would have returned.
        # However, to be safe, or if the sections are more independent later, fetch them again or pass them.
        # For now, assuming jobs_data and candidates_data are available if this point is reached.
        
        if not jobs_data: # Re-check in case logic changes, or fetch again if needed
             logger.warning("jobs_data is not available for listing interviews.")
             st.warning("无法加载职位数据，面试列表可能不完整。")
             jobs_data = [] # Avoid error later
        if not candidates_data: # Re-check
             logger.warning("candidates_data is not available for listing interviews.")
             st.warning("无法加载候选人数据，面试列表可能不完整。")
             candidates_data = [] # Avoid error later


        job_map = {job['id']: job['title'] for job in jobs_data}
        candidate_map = {cand['id']: cand['name'] for cand in candidates_data}

        if not interviews:
            st.info("目前没有已安排的面试。")
        else:
            # Custom headers for the interview list - ID first, Job & Candidate before Scheduled Time
            # Column ratios: ID(1), Job(3), Candidate(3), Scheduled(2.5), Status(2), Actions(3.5)
            cols_header = st.columns([1, 3, 3, 2.5, 2, 3.5]) 
            headers = ["ID", "职位名称", "候选人", "面试时间", "面试状态", "操作"]
            for col, header_text in zip(cols_header, headers):
                col.markdown(f"**{header_text}**")
            
            st.markdown("---") # Visual separator

            for interview in interviews:
                # Adjusted column ratios and order to match headers
                cols_data = st.columns([1, 3, 3, 2.5, 2, 3.5]) 
                interview_id = interview.get('id')
                
                job_title = job_map.get(interview.get('job_id'), f"未知职位 (ID: {interview.get('job_id')})")
                candidate_name = candidate_map.get(interview.get('candidate_id'), f"未知候选人 (ID: {interview.get('candidate_id')})")
                
                scheduled_at_str = interview.get('scheduled_at')
                display_scheduled_time = "未安排"
                if scheduled_at_str:
                    try:
                        dt_obj = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
                        display_scheduled_time = dt_obj.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        display_scheduled_time = scheduled_at_str

                interview_status_key = interview.get('status', 'N/A')
                display_status = STATUS_DISPLAY_MAPPING.get(interview_status_key, interview_status_key)
                
                cols_data[0].caption(f"{interview_id}") 
                cols_data[1].write(job_title) # Moved Job Title to 2nd column
                cols_data[2].write(candidate_name) # Moved Candidate Name to 3rd column
                cols_data[3].write(display_scheduled_time) # Moved Scheduled Time to 4th column
                cols_data[4].write(display_status) 
                # cols_data[5] is Actions

                # Actions column (now cols_data[5])
                with cols_data[5]:
                    action_cols = st.columns([1,1,1,1]) # Four buttons: Generate, View, Edit, Delete
                    with action_cols[0]:
                        if st.button("✍️", key=f"generate_q_{interview_id}", help="生成或重新生成面试问题"):
                            st.session_state.selected_interview_for_questions = interview_id
                            logger.info(f"User clicked 'Generate Questions' for interview ID: {interview_id}")
                            
                            with st.spinner(f"正在为面试 ID: {interview_id} 生成问题..."):
                                try:
                                    response = generate_interview_questions_for_interview(interview_id)
                                    num_questions = len(response.get('questions', []))
                                    st.success(f"🎉 成功为面试 ID: {interview_id} 生成了 {num_questions} 个问题。状态已更新！")
                                    logger.info(f"Successfully generated {num_questions} questions for interview {interview_id}. API Response: {response}")
                                    # Clear selection and loaded questions for this interview if any, then rerun
                                    if 'selected_interview_for_questions' in st.session_state:
                                        del st.session_state.selected_interview_for_questions
                                    if interview_id in st.session_state.loaded_questions:
                                        del st.session_state.loaded_questions[interview_id]
                                    if st.session_state.expanded_interview_questions == interview_id: # Collapse if it was open
                                        st.session_state.expanded_interview_questions = None
                                    st.rerun()
                                except APIError as e:
                                    logger.error(f"APIError generating questions for interview {interview_id}: {e.message}", exc_info=True)
                                    st.error(f"为面试 ID {interview_id} 生成问题失败：{e.message}")
                                    if e.details: st.error(f"详细信息：{e.details}")
                                except Exception as e:
                                    logger.error(f"Unexpected error generating questions for interview {interview_id}: {e}", exc_info=True)
                                    st.error(f"为面试 ID {interview_id} 生成问题时发生意外错误。")
                    
                    with action_cols[1]:
                        if st.button("🧐", key=f"view_q_{interview_id}", help="查看/刷新面试问题"):
                            if st.session_state.expanded_interview_questions == interview_id:
                                st.session_state.expanded_interview_questions = None 
                            else:
                                st.session_state.expanded_interview_questions = interview_id
                                # Fetch questions if not already loaded or to refresh
                                try:
                                    with st.spinner(f"正在加载面试 ID: {interview_id} 的问题..."):
                                        questions_data = get_questions_for_interview(interview_id)
                                        st.session_state.loaded_questions[interview_id] = questions_data
                                        logger.info(f"Loaded {len(questions_data)} questions for interview {interview_id}")
                                except APIError as e:
                                    st.error(f"加载面试 {interview_id} 的问题失败: {e.message}")
                                    st.session_state.loaded_questions[interview_id] = [] # Store empty list on error
                                    logger.error(f"APIError loading questions for interview {interview_id}: {e.message}", exc_info=True)
                                except Exception as e:
                                    st.error(f"加载面试 {interview_id} 的问题时发生未知错误。")
                                    st.session_state.loaded_questions[interview_id] = []
                                    logger.error(f"Unexpected error loading questions for interview {interview_id}: {e}", exc_info=True)
                            st.rerun() # Rerun to update UI based on new session state
                    
                    with action_cols[2]:
                        if st.button("✏️", key=f"edit_interview_{interview_id}", help="编辑面试信息"):
                            st.session_state.editing_interview_id = interview_id
                            st.session_state.interview_to_delete = None # Ensure delete state is cleared
                            # The dialog will be triggered by the main page logic based on this state
                            st.rerun() # Rerun to show dialog

                    with action_cols[3]:
                        if st.button("🗑️", key=f"delete_interview_confirm_{interview_id}", help="删除此面试"):
                            st.session_state.interview_to_delete = interview_id
                            st.session_state.editing_interview_id = None # Ensure edit state is cleared
                            st.rerun() # Rerun to show confirmation

                # Handle displaying the edit dialog outside the loop, triggered by session state
                if st.session_state.editing_interview_id == interview_id:
                    # Find the full interview object to pass to the dialog
                    # This is inefficient if list is very long, better to pass 'interview' directly
                    # but requires dialog to be callable directly or find a way to pass it.
                    # For now, let's refetch or find it (assuming 'interview' is the correct one)
                    edit_interview_dialog(interview) # Pass the current interview dict

                # Handle delete confirmation
                if st.session_state.interview_to_delete == interview_id:
                    st.warning(f"您确定要删除面试 ID: {interview_id} (职位: {job_title}, 候选人: {candidate_name}) 吗？此操作无法撤销。", icon="⚠️")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("确认删除", key=f"delete_interview_do_{interview_id}", type="primary"):
                            try:
                                delete_interview_api(interview_id)
                                st.success(f"面试 ID {interview_id} 已成功删除。")
                                st.session_state.interview_to_delete = None
                                # If questions were expanded for this, collapse
                                if st.session_state.expanded_interview_questions == interview_id:
                                    st.session_state.expanded_interview_questions = None
                                if interview_id in st.session_state.loaded_questions:
                                    del st.session_state.loaded_questions[interview_id]
                                st.rerun()
                            except APIError as e:
                                st.error(f"删除面试 ID {interview_id} 失败: {e.message}")
                                logger.error(f"APIError deleting interview {interview_id}: {e.message}", exc_info=True)
                            except Exception as e_del:
                                st.error(f"删除面试时发生意外错误: {str(e_del)}")
                                logger.error(f"Unexpected error deleting interview {interview_id}: {e_del}", exc_info=True)
                    with confirm_col2:
                        if st.button("取消删除", key=f"delete_interview_cancel_{interview_id}"):
                            st.session_state.interview_to_delete = None
                            st.rerun()
                
                # Display questions if this interview is expanded and questions are loaded
                if st.session_state.expanded_interview_questions == interview_id:
                    questions_to_display = st.session_state.loaded_questions.get(interview_id)
                    if questions_to_display is None: # Still loading or error
                        st.write("问题加载中或加载失败...")
                    elif not questions_to_display:
                        st.info("该面试目前没有问题。请尝试生成问题。")
                    else:
                        with st.expander(f"面试 ID: {interview_id} 的问题列表", expanded=True):
                            for q_idx, q_data in enumerate(questions_to_display):
                                st.markdown(f"{q_data.get('order_num', q_idx + 1)}. {q_data.get('question_text')}")
                            if not questions_to_display: # Should be caught by elif above, but as a fallback
                                st.caption("没有找到问题。")
                st.markdown("---") # Separator between interview entries

    except APIError as e:
        st.error(f"加载面试列表失败：{e.message}")
        logger.error(f"Failed to load interviews: {e}", exc_info=True)
    except Exception as e:
        st.error(f"加载面试列表时发生未知错误: {str(e)}")
        logger.error(f"Unexpected error loading interviews: {e}", exc_info=True)


def main():
    # st.set_page_config(page_title="面试管理 - AI助手", layout="wide") # Moved to top
    
    # Initialize session state for dialogs if not already present
    # Moved these to global scope for better organization
    
    # Trigger dialog if editing_interview_id is set (this part might need refinement or removal if dialog is directly called)
    # if st.session_state.get('editing_interview_id') is not None:
    #     # This logic needs to be careful, as edit_interview_dialog is defined and called inside show_interview_management_page
    #     # For now, the call to edit_interview_dialog(interview) is within the loop.
    #     pass

    show_interview_management_page()

if __name__ == "__main__":
    # Configure logging (optional, if not done elsewhere or for specific page behavior)
    # from streamlit_app.utils.logger_config import setup_global_logger
    # setup_global_logger()
    main()

logger.info("03_Interview_Management.py script execution completed.") 