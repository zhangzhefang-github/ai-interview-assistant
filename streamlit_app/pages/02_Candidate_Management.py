import streamlit as st
from streamlit_app.utils.api_client import (
    get_candidates, 
    create_candidate_with_resume, 
    update_candidate_api,
    delete_candidate_api,
    APIError
)
from streamlit_app.utils.logger_config import get_logger
from io import BytesIO
import pandas as pd

# Initialize logger
logger = get_logger(__name__)

logger.info("02_Candidate_Management.py page loading...")

# --- Session State Initialization for Delete (Edit dialog state no longer needed here to trigger it) ---
# if 'editing_candidate_id' not in st.session_state: # REMOVED
#     st.session_state.editing_candidate_id = None   # REMOVED
if 'confirming_delete_candidate_id' not in st.session_state:
    st.session_state.confirming_delete_candidate_id = None
if 'candidate_to_delete_name' not in st.session_state:
    st.session_state.candidate_to_delete_name = ""
# Add session state for action messages
if 'last_action_status' not in st.session_state:
    st.session_state.last_action_status = None


# --- Dialog for Editing Candidate ---
@st.dialog("📝 编辑候选人信息")
def edit_candidate_dialog(candidate: dict):
    candidate_id = candidate.get("id")
    logger.info(f"Edit Candidate dialog opened for candidate ID: {candidate_id}, Name: {candidate.get('name')}")
    
    with st.form(key=f"edit_candidate_form_{candidate_id}"):
        current_name = candidate.get("name", "")
        current_email = candidate.get("email", "")

        edited_name = st.text_input("姓名", value=current_name, key=f"dialog_edit_cand_name_{candidate_id}")
        edited_email = st.text_input("邮箱", value=current_email, key=f"dialog_edit_cand_email_{candidate_id}")

        submitted = st.form_submit_button("保存更改")
        if submitted:
            if not edited_name or not edited_email:
                st.warning("候选人姓名和邮箱均不能为空。")
            elif edited_name == current_name and edited_email == current_email: 
                st.info("未检测到任何更改。")
            else:
                try:
                    update_candidate_api(candidate_id, edited_name, edited_email) 
                    st.success(f"候选人 '{edited_name}' (ID: {candidate_id}) 信息更新成功！")
                    logger.info(f"Candidate ID '{candidate_id}' updated successfully via dialog. Rerunning.")
                    # st.session_state.editing_candidate_id = None # No longer needed to close by state
                    st.rerun() # Rerun to refresh list & close dialog by not being called again
                except APIError as e:
                    logger.error(f"APIError during candidate update via dialog (ID: {candidate_id}): {e.message}", exc_info=True)
                    st.error(f"更新失败：{e.message}")
                    if e.details: st.error(f"详细信息：{e.details}")
                except Exception as e:
                    logger.error(f"Unexpected error during candidate update via dialog (ID: {candidate_id}): {e}", exc_info=True)
                    st.error(f"发生意外错误：{str(e)}")

def show_candidate_management_page():
    st.header("👥 候选人管理")
    st.markdown("管理系统中的候选人信息。您可以在这里添加新的候选人、上传他们的简历，并查看、编辑或删除现有候选人的列表。AI系统将尝试从上传的简历中提取关键信息。")

    # --- Section: Create New Candidate ---
    st.subheader("➕ 添加新候选人")
    with st.form("new_candidate_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            candidate_name = st.text_input("姓名", placeholder="例如：张三")
        with col2:
            candidate_email = st.text_input("邮箱", placeholder="例如：zhangsan@example.com")
        
        uploaded_resume = st.file_uploader(
            "上传简历", 
            type=["txt", "pdf", "doc", "docx"],
            help="支持 .txt, .pdf, .doc, .docx 格式的简历文件。"
        )
        
        submit_button = st.form_submit_button("提交候选人信息")

        if submit_button:
            if not candidate_name:
                st.warning("请输入候选人姓名。")
            elif not candidate_email: 
                st.warning("请输入候选人邮箱。")
            elif uploaded_resume is None:
                st.warning("请上传候选人的简历文件。")
            else:
                try:
                    resume_bytes_io = BytesIO(uploaded_resume.getvalue())
                    if hasattr(uploaded_resume, 'type'):
                        resume_bytes_io.type = uploaded_resume.type
                    
                    logger.info(f"Form submitted for new candidate: {candidate_name}, {candidate_email}, resume: {uploaded_resume.name}")
                    
                    created_candidate = create_candidate_with_resume(
                        name=candidate_name,
                        email=candidate_email,
                        resume_file=resume_bytes_io,
                        filename=uploaded_resume.name
                    )
                    
                    st.success(f"🎉 候选人 '{created_candidate.get('name')}' 添加成功！简历已上传并开始处理。")
                    logger.info(f"Successfully created candidate: {created_candidate}")
                    st.rerun()
                except APIError as e:
                    logger.error(f"APIError while creating candidate: {e.message} (Status: {e.status_code}, Details: {e.details})", exc_info=True)
                    st.error(f"创建候选人失败：{e.message}")
                    if e.details:
                        st.error(f"详细信息：{e.details}")
                except Exception as e:
                    logger.error(f"Unexpected error while creating candidate: {e}", exc_info=True)
                    st.error(f"创建候选人时发生意外错误：{str(e)}")

    st.divider()

    st.subheader("📋 现有候选人列表")
    display_candidates_list_with_actions()


def display_candidates_list_with_actions():
    try:
        candidates = get_candidates()
        if not candidates:
            st.info("系统中暂无候选人信息。请通过上面的表单添加。")
            return

        cols_config = {
            "ID": 0.3,
            "姓名": 0.7,
            "邮箱": 1.5,
            "查看简历": 4.5,
            "编辑": 0.5,
            "删除": 0.5
        }
        header_cols = st.columns(list(cols_config.values()))
        for col, field_name in zip(header_cols, cols_config.keys()):
            col.markdown(f"**{field_name}**")

        for candidate_data in candidates: # Renamed to avoid conflict with edit_candidate_dialog parameter
            cand_id = candidate_data.get('id')
            cand_name = candidate_data.get('name', 'N/A')
            cand_email = candidate_data.get('email', 'N/A')
            cand_resume_text = candidate_data.get('resume_text', '无简历文本或解析失败。')
            if not cand_resume_text: cand_resume_text = "无简历文本或解析失败。"

            data_cols = st.columns(list(cols_config.values()))
            data_cols[0].write(str(cand_id))
            data_cols[1].write(cand_name)
            data_cols[2].write(cand_email)

            with data_cols[3]: 
                with st.expander("查看解析文本", expanded=False):
                    st.text_area(label="简历内容:", value=cand_resume_text, height=200, disabled=True, key=f"resume_view_{cand_id}")
            
            with data_cols[4]: 
                if st.button("✏️", key=f"edit_cand_{cand_id}", help="编辑候选人信息", use_container_width=True):
                    # Directly call the dialog if the button is clicked.
                    # The dialog will appear in the part of the script execution where this button is True.
                    edit_candidate_dialog(candidate_data) # Pass the full candidate data dict
            
            with data_cols[5]: 
                if st.button("🗑️", key=f"delete_init_cand_{cand_id}", help="删除候选人", use_container_width=True):
                    st.session_state.confirming_delete_candidate_id = cand_id
                    st.session_state.candidate_to_delete_name = cand_name
                    # st.session_state.editing_candidate_id = None # Already cleared by previous fix if this was an issue
                    st.rerun() 

            # Confirmation UI and action buttons
            if st.session_state.confirming_delete_candidate_id == cand_id:
                st.warning(f"您确定要删除候选人 '{st.session_state.candidate_to_delete_name}' (ID: {cand_id}) 吗？此操作无法撤销。", icon="⚠️")
                # Align buttons to the right or under specific columns if desired, but message display will be separate
                button_row_cols = st.columns((sum(list(cols_config.values())[:-2]), list(cols_config.values())[-2] + list(cols_config.values())[-1] ))
                with button_row_cols[1]: 
                    inner_button_cols = st.columns(2)
                    with inner_button_cols[0]:
                        if st.button("确认", key=f"confirm_delete_cand_action_{cand_id}", use_container_width=True, type="secondary"):
                            try:
                                delete_candidate_api(cand_id)
                                st.session_state.last_action_status = {
                                    "type": "success",
                                    "message": f"候选人 '{st.session_state.candidate_to_delete_name}' (ID: {cand_id}) 已成功删除。",
                                    "candidate_id": cand_id
                                }
                                logger.info(f"Candidate {cand_id} successfully deleted.")
                            except APIError as e:
                                st.session_state.last_action_status = {
                                    "type": "error",
                                    "message": f"操作失败：{e.details or e.message}",
                                    "candidate_id": cand_id
                                }
                                logger.error(f"APIError deleting candidate {cand_id}: {e.details or e.message}")
                            except Exception as e:
                                st.session_state.last_action_status = {
                                    "type": "error",
                                    "message": f"发生意外错误：{str(e)}",
                                    "candidate_id": cand_id
                                }
                                logger.error(f"Unexpected error deleting candidate {cand_id}: {str(e)}", exc_info=True)
                            finally:
                                # Always clear confirmation state and rerun to show message or refresh list
                                st.session_state.confirming_delete_candidate_id = None
                                st.session_state.candidate_to_delete_name = ""
                                st.rerun()
                    with inner_button_cols[1]:
                        if st.button("取消", key=f"cancel_delete_cand_action_{cand_id}", use_container_width=True):
                            st.session_state.confirming_delete_candidate_id = None
                            st.session_state.candidate_to_delete_name = ""
                            st.rerun()
            
            # Display action status message (success or error) for the current candidate
            # This is placed outside the button column structure, so it will be wider.
            if st.session_state.last_action_status and \
               st.session_state.last_action_status.get("candidate_id") == cand_id:
                status_info = st.session_state.last_action_status
                if status_info["type"] == "success":
                    st.success(status_info["message"])
                elif status_info["type"] == "error":
                    st.error(status_info["message"])
                st.session_state.last_action_status = None # Clear the message after displaying

            st.markdown("---") 

        # REMOVED THE BLOCK THAT OPENS DIALOG BASED ON SESSION STATE
        # # Handle dialog opening for editing
        # if st.session_state.editing_candidate_id is not None:
        #     candidate_to_edit_data = next((c for c in candidates if c['id'] == st.session_state.editing_candidate_id), None)
        #     if candidate_to_edit_data:
        #         edit_candidate_dialog(candidate_to_edit_data)
        #     else:
        #         logger.error(f"Attempted to edit candidate ID {st.session_state.editing_candidate_id} but no data found.")
        #         st.error("无法加载候选人数据进行编辑。")
        #         st.session_state.editing_candidate_id = None 

    except APIError as e:
        logger.error(f"APIError while fetching/displaying candidates: {e.message} (Status: {e.status_code}, Details: {e.details})", exc_info=True)
        if e.details:
            st.error(f"获取候选人列表失败：{e.details}")
        else:
            st.error(f"获取候选人列表失败：{e.message}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching/displaying candidates: {e}", exc_info=True)
        st.error(f"获取候选人列表时发生意外错误：{str(e)}")

if __name__ == "__main__":
    show_candidate_management_page()

logger.info("02_Candidate_Management.py script execution completed.")
