import streamlit as st
from streamlit_app.utils.api_client import (
    APIError,
    get_interviews,
    get_jobs, # For job_map
    get_candidates, # For candidate_map
    get_interview_details, # Now using this
    generate_report_for_interview_api # Now using this
)
from streamlit_app.utils.logger_config import get_logger
from datetime import datetime
from typing import Optional, Dict, List # Updated typing
import plotly.graph_objects as go # Import go
# Removed pandas import as it's not used in the new simple chart function
# import pandas as pd # For creating DataFrame for Plotly 

# Logger Setup
logger = get_logger(__name__)

logger.info("05_Report_Generation_and_Viewing.py script execution started.")

# st.set_page_config(
#     page_title="面试评估报告 - AI面试助手",
#     page_icon="📊",
#     layout="wide"
# )

STATUS_DISPLAY_MAPPING = {
    "PENDING_QUESTIONS": "等待生成问题",
    "QUESTIONS_GENERATED": "问题已生成",
    "LOGGING_COMPLETED": "记录已完成",
    "REPORT_GENERATED": "报告已生成",
    # Add other statuses if they can appear here
}

# Helper to format datetime string if not None
def format_datetime_display(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "未设置"
    try:
        dt_obj = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt_obj.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return dt_str # Return original if parsing fails

# --- Function to create radar chart (New Simple Version) --- 
def create_radar_chart_simple(assessment_data: Dict[str, float]) -> Optional[go.Figure]:
    """
    Creates a radar chart using plotly.graph_objects directly.
    Assumes assessment_data keys are categories and values are scores (expected 1-5).
    """
    if not assessment_data or not isinstance(assessment_data, dict):
        logger.warning("Radar chart (simple): assessment_data is empty or not a dict.")
        return None

    categories = list(assessment_data.keys())
    raw_values = list(assessment_data.values())

    # Basic validation and conversion for values
    values: List[float] = []
    for v in raw_values:
        try:
            val = float(v)
            # Optional: Clamp values to the 0-5 range if AI might exceed it
            # val = max(0, min(5, val)) 
            values.append(val)
        except (ValueError, TypeError):
            logger.warning(f"Radar chart (simple): Non-numeric score '{v}' found, using 0.")
            values.append(0.0) # Default to 0 if not a valid number

    if not categories or not values or len(categories) != len(values):
        logger.warning("Radar chart (simple): Invalid data (categories/values mismatch or empty after processing).")
        return None

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]] if values else [],  # Close the shape
        theta=categories + [categories[0]] if categories else [], # Close the shape
        fill='toself',
        # Example styling (optional, can be customized)
        # line_color='rgb(31, 119, 180)', # Plotly default blue
        # fillcolor='rgba(31, 119, 180, 0.6)' 
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, 
                range=[0, 5],       # Set range for 1-5 scale
                tickvals=[1, 2, 3, 4, 5], # Explicit ticks
                # angle=90, # Optional: sets the angle of the first axis
                # tickfont_size = 10 # Optional: adjust tick font size
            ),
            # angularaxis=dict(
            #     tickfont_size=12 # Optional: adjust category label font size
            # )
        ),
        showlegend=False,
        # You might want to adjust margins if labels get cut off
        # margin=dict(l=80, r=80, t=50, b=50) # Example: l=left, r=right, t=top, b=bottom
    )
    
    # Remove Streamlit theme-based template for more direct control if preferred
    # Or, if you want to use it:
    # theme_template = "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"
    # fig.update_layout(template=theme_template)

    return fig

def show_report_generation_page():
    st.header("📊 面试评估报告生成与查看")
    st.markdown("选择已完成面试记录的访谈，为其生成AI评估报告，或查看已生成的报告及能力雷达图。")

    interviews_options = []
    job_map = {}
    candidate_map = {}

    try:
        # Fetch all necessary data upfront
        all_interviews = get_interviews()
        jobs_data = get_jobs()
        candidates_data = get_candidates()
        
        job_map = {job['id']: job for job in jobs_data}
        candidate_map = {cand['id']: cand for cand in candidates_data}

        eligible_interviews = [
            i for i in all_interviews 
            if i.get("status") in ["LOGGING_COMPLETED", "REPORT_GENERATED"]
        ]
        
        if not eligible_interviews:
            st.info("当前没有已完成记录或已生成报告的面试。请先完成面试过程记录。")
            return

        for interview in eligible_interviews:
            interview_id = interview.get('id')
            job_id = interview.get('job_id')
            candidate_id = interview.get('candidate_id')
            interview_status = interview.get('status', '未知状态')
            
            job_title = job_map.get(job_id, {}).get('title', f"职位ID {job_id}")
            candidate_name = candidate_map.get(candidate_id, {}).get('name', f"候选人ID {candidate_id}")
            status_display = STATUS_DISPLAY_MAPPING.get(interview_status, interview_status) # Translate status to Chinese
            
            display_name = f"面试ID {interview_id}：{job_title} - {candidate_name} - {status_display}"
            interviews_options.append((display_name, interview_id))

    except APIError as e:
        st.error(f"获取面试列表或关联数据失败：{e.details or e.message}")
        return
    except Exception as e:
        st.error(f"加载面试列表或关联数据时发生意外错误: {str(e)}")
        logger.error("Error loading interviews/jobs/candidates for report page", exc_info=True)
        return

    if not interviews_options:
        st.info("系统中没有符合条件的面试可供选择（状态为 LOGGING_COMPLETED 或 REPORT_GENERATED）。")
        return

    # Sort options by interview ID, newest first (descending)
    interviews_options.sort(key=lambda x: x[1], reverse=True)

    selected_option = st.selectbox(
        "选择一个面试：", 
        options=interviews_options, 
        format_func=lambda x: x[0] # Display name is the first element of the tuple
    )

    if selected_option:
        selected_interview_id = selected_option[1]
        logger.info(f"Report page: Selected interview ID: {selected_interview_id}")
        
        # Initialize session state for this interview's report
        if f"report_text_{selected_interview_id}" not in st.session_state:
            st.session_state[f"report_text_{selected_interview_id}"] = None
        if f"report_error_{selected_interview_id}" not in st.session_state:
            st.session_state[f"report_error_{selected_interview_id}"] = None

        interview_details = None
        try:
            # get_interview_details should return job and candidate info nested within
            interview_details = get_interview_details(selected_interview_id) 
            st.session_state[f"report_text_{selected_interview_id}"] = interview_details.get("report")
            st.session_state[f"report_error_{selected_interview_id}"] = None # Clear previous error
        except APIError as e:
            st.error(f"获取面试详情失败：{e.details or e.message}")
            st.session_state[f"report_error_{selected_interview_id}"] = f"获取面试详情失败：{e.details or e.message}"
            return 
        except Exception as e:
            st.error(f"获取面试详情时发生意外错误: {str(e)}")
            logger.error(f"Error fetching interview details for ID {selected_interview_id}", exc_info=True)
            st.session_state[f"report_error_{selected_interview_id}"] = f"获取面试详情时发生意外错误: {str(e)}"
            return

        if not interview_details:
            st.error("无法加载所选面试的详细信息。")
            return

        st.subheader(f"面试详情 (ID: {selected_interview_id})")
        
        # Use job and candidate names from the maps for consistency if interview_details doesn't have them readily
        # However, interview_details *should* have them if the API is structured correctly.
        display_job_title = interview_details.get("job", {}).get("title", job_map.get(interview_details.get("job_id"), {}).get("title", "未知职位"))
        display_candidate_name = interview_details.get("candidate", {}).get("name", candidate_map.get(interview_details.get("candidate_id"), {}).get("name", "未知候选人"))
        st.caption(f"职位: {display_job_title} | 候选人: {display_candidate_name}")

        # --- Section for JD, Resume, Log ---
        with st.expander("职位描述 (JD)", expanded=False): # Changed title for clarity
            jd_text = interview_details.get("job", {}).get("description", "无JD信息")
            st.text_area("JD_display", value=jd_text, height=150, disabled=True, key=f"jd_{selected_interview_id}", label_visibility="collapsed")
        
        with st.expander("候选人简历摘要", expanded=False):
            resume_text = interview_details.get("candidate", {}).get("resume_text", "无简历信息")
            st.text_area("Resume_display", value=resume_text, height=150, disabled=True, key=f"resume_{selected_interview_id}", label_visibility="collapsed")
        
        with st.expander("面试过程记录", expanded=False):
            log_text = interview_details.get("conversation_log", "无面试记录")
            st.text_area("Log_display", value=log_text, height=200, disabled=True, key=f"log_{selected_interview_id}", label_visibility="collapsed")

        st.divider() # Divider after JD/Resume/Log expanders

        # --- Section for Report and Radar Chart ---
        current_report = st.session_state[f"report_text_{selected_interview_id}"]
        current_status_str = interview_details.get("status") 
        current_status_display = STATUS_DISPLAY_MAPPING.get(current_status_str, current_status_str)

        # Display existing report if available
        if current_report:
            st.subheader("📋 AI评估报告")
            st.markdown(current_report)

            st.divider()
            st.subheader("🎯 候选人能力雷达图")
            capability_data = interview_details.get("radar_data")
            if capability_data:
                radar_fig = create_radar_chart_simple(capability_data)
                if radar_fig:
                    st.plotly_chart(radar_fig, use_container_width=True)
                else:
                    st.info("未能生成雷达图：评估数据格式不正确或不完整。")
            else:
                st.info("AI评估报告中未找到可用于生成雷达图的结构化能力评分数据。请检查AI提示词和报告内容。")
            st.divider() # Divider after report and radar chart, before potential re-generate button

        # Button to generate or re-generate report
        button_text = "🔄 重新生成AI评估报告" if current_report and current_status_str == "REPORT_GENERATED" else "🤖 生成AI评估报告"
        button_key = f"action_report_btn_{selected_interview_id}" # Use a consistent key prefix

        if current_status_str in ["LOGGING_COMPLETED", "REPORT_GENERATED"]:
            if current_report and current_status_str == "REPORT_GENERATED":
                st.info("提示：您可以选择重新生成AI评估报告，这将覆盖当前的报告内容。")
            
            # For LOGGING_COMPLETED without a report yet
            elif current_status_str == "LOGGING_COMPLETED" and not current_report:
                 st.info(f"此面试已记录完毕 (状态: {current_status_display})，点击下方按钮生成评估报告。")

            if st.button(button_text, key=button_key):
                if current_report and current_status_str == "REPORT_GENERATED":
                    logger.info(f"User initiated RE-GENERATION of report for interview ID: {selected_interview_id}")
                else:
                    logger.info(f"User initiated GENERATION of report for interview ID: {selected_interview_id}")
                
                with st.spinner("AI正在分析并生成报告中，请稍候..."):
                    try:
                        logger.info(f"Calling generate_report_for_interview_api for interview ID: {selected_interview_id}")
                        api_response = generate_report_for_interview_api(selected_interview_id)
                        updated_report = api_response.get("report") 
                        st.session_state[f"report_text_{selected_interview_id}"] = updated_report
                        # Update status in session state from API response if it's part of it
                        # For now, assume generate_report_for_interview_api returns the full interview object
                        if api_response.get("status"):
                            st.session_state[f"interview_status_{selected_interview_id}"] = api_response.get("status")

                        st.session_state[f"report_error_{selected_interview_id}"] = None
                        logger.info(f"Successfully generated/re-generated report for interview {selected_interview_id}")
                        st.success("AI评估报告已成功处理！")
                        st.rerun() 
                    except APIError as e:
                        logger.error(f"APIError generating/re-generating report for interview {selected_interview_id}: {e.details or e.message}", exc_info=True)
                        st.session_state[f"report_error_{selected_interview_id}"] = f"处理报告失败：{e.details or e.message}"
                        st.error(st.session_state[f"report_error_{selected_interview_id}"])
                    except Exception as e:
                        logger.error(f"Unexpected error generating/re-generating report for interview {selected_interview_id}: {e}", exc_info=True)
                        st.session_state[f"report_error_{selected_interview_id}"] = f"处理报告时发生意外错误：{str(e)}"
                        st.error(st.session_state[f"report_error_{selected_interview_id}"])
            
        elif st.session_state.get(f"report_error_{selected_interview_id}"): # Check if there's a stored error for this interview
             st.error(st.session_state[f"report_error_{selected_interview_id}"]) 
            
        else: 
            # This case might occur if status is not LOGGING_COMPLETED or REPORT_GENERATED
            # and no report/error is in session state.
            st.warning(f"当前面试状态为 ({current_status_display})，不符合生成或查看报告的条件，或未找到报告内容。")

if __name__ == "__main__":
    show_report_generation_page()

logger.info("05_Report_Generation_and_Viewing.py script execution completed and UI rendered.") 