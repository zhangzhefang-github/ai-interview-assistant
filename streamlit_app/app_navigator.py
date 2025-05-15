import sys
import os

# 获取 app_navigator.py 文件的绝对路径
_current_file_path = os.path.abspath(__file__)
# 获取 streamlit_app 目录的路径 (app_navigator.py 的父目录)
_streamlit_app_dir = os.path.dirname(_current_file_path)
# 获取项目根目录的路径 (streamlit_app 目录的父目录)
_project_root_dir = os.path.dirname(_streamlit_app_dir)

# 将项目根目录添加到 sys.path，如果它还不在里面的话
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

import streamlit as st
from streamlit.navigation.page import Page

# 定义应用中的所有页面及其在侧边栏的显示方式
# st.Page 的第一个参数是实际的文件路径
# title 参数是将在侧边栏显示的中文名称
# icon 参数是侧边栏图标

# 设置整个应用的页面配置，这会影响浏览器标签等
st.set_page_config(
    page_title="AI 面试助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main_app_navigator():
    st.sidebar.title("导航")

    # 获取 app_navigator.py 所在目录的绝对路径 (即 streamlit_app/)
    navigator_dir = os.path.dirname(os.path.abspath(__file__))
    # print(f"[DEBUG] Navigator directory: {navigator_dir}") 

    # 首页路径直接在 streamlit_app/ 目录下
    home_page_path = os.path.join(navigator_dir, "00_Home.py")
    # print(f"[DEBUG] Path for 00_Home.py: {home_page_path}") 
    # print(f"[DEBUG] Does 00_Home.py exist at that path? {os.path.exists(home_page_path)}")

    # 其他页面在 pages 子目录下
    pages_dir = os.path.join(navigator_dir, "pages")

    pages = [
        Page(home_page_path, title="首页", icon="🏠"),
        Page(os.path.join(pages_dir, "01_Job_Management.py"), title="职位管理", icon="🛠️"),
        Page(os.path.join(pages_dir, "02_Candidate_Management.py"), title="候选人管理", icon="👥"),
        Page(os.path.join(pages_dir, "03_Interview_Management.py"), title="面试管理", icon="🗓️"),
        Page(os.path.join(pages_dir, "04_Interview_Logging.py"), title="面试过程记录", icon="🎤"),
        Page(os.path.join(pages_dir, "05_Report_Generation_and_Viewing.py"), title="面试评估报告", icon="📊"),
    ]

    # Create the navigation
    pg = st.navigation(pages)
    
    # Run the selected page
    pg.run()

if __name__ == "__main__":
    main_app_navigator() 