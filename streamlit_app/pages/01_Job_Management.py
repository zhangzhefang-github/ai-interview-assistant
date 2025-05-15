import streamlit as st
import pandas as pd
from streamlit_app.utils.logger_config import get_logger
from streamlit_app.core_ui_config import BACKEND_API_URL
from streamlit_app.utils.api_client import get_jobs, create_job, delete_job_api, update_job_api, APIError

# --- Logger Setup ---
logger = get_logger(__name__)

logger.info("01_Job_Management.py script execution started.")

# st.set_page_config( # REMOVED or COMMENTED OUT
#     page_title="职位管理 - AI面试助手",
#     page_icon="💼",
#     layout="wide"
# )

# --- Configuration ---
logger.debug(f"Backend URL (from core_ui_config): {BACKEND_API_URL}")

# --- Session State Initialization ---
# 确保 session_state 属性存在，避免 AttributeError
if 'editing_job' not in st.session_state:
    st.session_state.editing_job = False
if 'current_job_id' not in st.session_state:
    st.session_state.current_job_id = None
if 'current_job_title' not in st.session_state:
    st.session_state.current_job_title = ""
if 'current_job_description' not in st.session_state:
    st.session_state.current_job_description = ""
if 'confirming_delete_job_id' not in st.session_state:
    st.session_state.confirming_delete_job_id = None
if 'job_to_delete_title' not in st.session_state: # To store title for confirmation message
    st.session_state.job_to_delete_title = ""

# # --- Page Title and Header ---
# st.title("职位管理")
# st.markdown("管理您的招聘职位，包括创建、编辑、查看和删除职位信息。")
# logger.info("Job Management page UI main elements rendered.")

# --- UI Sections (大部分从原 main_ui.py 迁移) ---

@st.dialog("➕ 添加新职位")
def add_job_dialog():
    logger.info("Add New Job dialog opened.")
    with st.form("new_job_form_dialog"):
        new_job_title = st.text_input("职位名称", key="dialog_add_job_title")
        new_job_description = st.text_area("职位描述", key="dialog_add_job_desc", height=150)
        
        submitted = st.form_submit_button("保存职位")
        if submitted:
            if not new_job_title or not new_job_description:
                st.warning("职位名称和描述均不能为空。")
            else:
                try:
                    create_job(new_job_title, new_job_description)
                    st.success(f"职位 '{new_job_title}' 添加成功！")
                    logger.info(f"New job '{new_job_title}' created successfully via dialog. Rerunning.")
                    st.rerun() # Rerun to close dialog and refresh list
                except APIError as e:
                    logger.error(f"APIError during job creation via dialog: {e.message}", exc_info=True)
                    st.error(f"添加失败：{e.message}")
                    if e.details: st.error(f"详细信息：{e.details}")
                except Exception as e:
                    logger.error(f"Unexpected error during job creation via dialog: {e}", exc_info=True)
                    st.error(f"发生意外错误：{str(e)}")

@st.dialog("📝 编辑职位")
def edit_job_dialog(job_to_edit: dict):
    job_id = job_to_edit['id']
    logger.info(f"Edit Job dialog opened for job ID: {job_id}")
    with st.form(key=f"edit_job_form_dialog_{job_id}"):
        current_title = job_to_edit.get("title", "")
        current_description = job_to_edit.get("description", "")

        edited_title = st.text_input("职位名称", value=current_title, key=f"dialog_edit_title_{job_id}")
        edited_description = st.text_area("职位描述", value=current_description, key=f"dialog_edit_desc_{job_id}", height=150)
        
        submitted = st.form_submit_button("保存更改")
        if submitted:
            if not edited_title or not edited_description:
                st.warning("职位名称和描述均不能为空。")
            elif edited_title == current_title and edited_description == current_description:
                st.info("未检测到任何更改。")
            else:
                try:
                    update_job_api(job_id, edited_title, edited_description)
                    st.success(f"职位 '{edited_title}' 更新成功！")
                    logger.info(f"Job ID '{job_id}' updated successfully via dialog. Rerunning.")
                    st.rerun() # Rerun to close dialog and refresh list
                except APIError as e:
                    logger.error(f"APIError during job update via dialog (ID: {job_id}): {e.message}", exc_info=True)
                    st.error(f"更新失败：{e.message}")
                    if e.details: st.error(f"详细信息：{e.details}")
                except Exception as e:
                    logger.error(f"Unexpected error during job update via dialog (ID: {job_id}): {e}", exc_info=True)
                    st.error(f"发生意外错误：{str(e)}")

# --- Main Page Content for Job Management ---
logger.info("Rendering main content of Job Management page.")

def reset_form_state():
    st.session_state.editing_job = False
    st.session_state.current_job_id = None
    st.session_state.current_job_title = ""
    st.session_state.current_job_description = ""
    # Force rerun to reflect state change in UI, especially after form submission for create/update
    # This will also help in clearing input fields if they are bound to these session state vars.
    st.rerun()

def show_job_management_page():
    st.header("💼 职位管理")
    st.markdown("管理您的招聘职位，包括创建、编辑、查看和删除职位信息。")

    if st.button("➕ 添加新职位", type="primary"):
        add_job_dialog()
    
    st.divider()

    # --- Display Existing Jobs ---
    st.subheader("现有职位列表")
    logger.info("Fetching jobs list for display...")
    try:
        jobs_data = get_jobs()
        if jobs_data:
            # Define column configurations: (name, width)
            # Column names for header and data mapping key
            cols_config = {
                "ID": 0.7,
                "职位名称": 2.5,
                "职位描述": 3.5,
                "编辑": 1.0, # Placeholder for edit button
                "删除": 1.0  # Placeholder for delete button
            }
            header_cols = st.columns(cols_config.values())
            for col, field_name in zip(header_cols, cols_config.keys()):
                col.markdown(f"**{field_name}**")
            
            for job in jobs_data:
                job_id = job.get('id')
                job_title = job.get('title', 'N/A')
                job_description_full = job.get('description', 'N/A')
                # Truncate description for display in expander label
                max_desc_len = 50 
                expander_label = (job_description_full[:max_desc_len] + '...') if len(job_description_full) > max_desc_len else job_description_full

                data_cols = st.columns(list(cols_config.values()))
                data_cols[0].write(str(job_id))
                data_cols[1].write(job_title)
                # data_cols[2].write(truncated_desc) # Display truncated is now replaced by the expander below
                with data_cols[2]: # Description column
                    with st.expander(label=expander_label, expanded=False):
                        st.write(job_description_full)
                
                with data_cols[3]: # Edit button column
                    if st.button("✏️ 编辑", key=f"edit_{job_id}", use_container_width=True):
                        # Fetch the full job data again to ensure we pass complete description to dialog
                        full_job_data = next((j for j in jobs_data if j['id'] == job_id), None)
                        if full_job_data:
                            edit_job_dialog(full_job_data)
                        else:
                            st.error(f"无法找到ID为 {job_id} 的职位数据进行编辑。")
                            logger.error(f"Edit button clicked, but full job data for ID {job_id} not found.")
                
                with data_cols[4]: # Delete button column
                    if st.button("🗑️ 删除", key=f"delete_initiate_{job_id}", type="primary", use_container_width=True):
                        st.session_state.confirming_delete_job_id = job_id
                        st.session_state.job_to_delete_title = job_title 
                        st.rerun()
                
                # Confirmation UI displayed below the job item if it's the one being confirmed for deletion
                if st.session_state.confirming_delete_job_id == job_id:
                    # Indent confirmation slightly or place in a container if needed for clarity
                    st.warning(f"您确定要删除职位 '{st.session_state.job_to_delete_title}' (ID: {job_id}) 吗？此操作无法撤销。", icon="⚠️")
                    # confirm_action_cols = st.columns([st.session_state.cols_config_sum - 1, 1]) # Make confirm/cancel span part of the row # This line had an error and has been removed
                    
                    button_cols_config = list(cols_config.values())
                    # empty_space_width = sum(button_cols_config[:3]) # Width of ID, Title, Desc
                    # action_buttons_width_ratio = sum(button_cols_config[3:])

                    # Create placeholder columns for alignment, then the action buttons
                    # This is a bit tricky to align perfectly under the specific action buttons of the row above.
                    # A simpler way is to just show it full width below the item row.
                    # For now, let's do a simpler full-width confirmation display.
                    
                    # Adjusted to use a simpler layout for confirm/cancel buttons to avoid complexity with precise column alignment
                    confirm_ui_cols_buttons = st.columns([3, 1, 1]) # Adjust ratios as needed: spacer, yes, cancel
                    
                    with confirm_ui_cols_buttons[1]: # "Yes" button column
                        if st.button("是的", key=f"confirm_delete_action_{job_id}", use_container_width=True, type="secondary"): # Changed type to secondary
                            try:
                                delete_job_api(job_id)
                                st.success(f"职位 '{st.session_state.job_to_delete_title}' (ID: {job_id}) 已删除。")
                                st.session_state.confirming_delete_job_id = None 
                                st.session_state.job_to_delete_title = ""
                                st.rerun()
                            except APIError as e:
                                st.error(f"删除失败：{e.message}")
                                if e.details: st.error(f"详细信息：{e.details}")
                            except Exception as e:
                                st.error(f"发生意外错误：{str(e)}")
                    with confirm_ui_cols_buttons[2]: # "Cancel" button column
                        if st.button("取消", key=f"cancel_delete_action_{job_id}", use_container_width=True):
                            st.info("删除操作已取消。")
                            st.session_state.confirming_delete_job_id = None
                            st.session_state.job_to_delete_title = ""
                            st.rerun()
                
        elif jobs_data is None:
             st.info("无法加载职位数据，请稍后再试或检查后端服务。")
        else: 
            st.info("系统中暂无职位信息。请点击上方按钮添加新职位。")
            
    except APIError as e:
        logger.error(f"APIError fetching jobs for display: {e.message}", exc_info=True)
        st.error(f"获取职位列表失败：{e.message}")
        if e.details: st.error(f"详细信息：{e.details}")
    except Exception as e:
        logger.error(f"Unexpected error fetching jobs for display: {e}", exc_info=True)
        st.error(f"加载职位列表时发生意外错误：{str(e)}")

# Ensure this is the main function called if this script is run as a page
if __name__ == "__main__":
    show_job_management_page()

logger.info("01_Job_Management.py script execution completed and UI rendered.") 