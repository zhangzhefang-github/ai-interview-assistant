import streamlit as st
from streamlit_app.utils.logger_config import get_logger

# --- Logger Setup ---
logger = get_logger(__name__)

logger.info("00_Home.py script execution started.")

# st.set_page_config(
#     page_title="首页 - AI面试助手",
#     page_icon="🤖",
#     layout="wide"
# )

st.title("欢迎使用 AI 面试助手")
st.sidebar.success("请从上方选择一个功能页面。")

st.markdown("""
欢迎探索 **AI 面试助手**，您的战略招聘赋能平台。我们致力于通过尖端智能技术，革新您的招聘作业模式，赋予您对职位规划、人才吸引及面试评估全链路的卓越掌控力，驱动企业人才战略升级。

本平台深度集成前沿AI算法，为您提供：
*   **简历智能筛选与解析：** 自动化处理海量简历，精准提取关键信息，大幅提升筛选效率。
*   **职位需求深度洞察：** AI辅助分析职位核心能力与潜在候选人画像，优化招聘启事吸引力。
*   **定制化面试方案生成：** 基于职位与候选人特性，智能推荐结构化面试流程与高度相关的提问。
*   **一键式专业评估报告：** 综合各项考察维度，快速生成客观、全面的面试评估报告，支持数据化人才决策。

**核心功能模块：**

*   **战略职位管理:**
    高效创建与发布职位，多维度精准编辑与追溯，通过实时数据看板全面掌控职位动态与招聘进展，确保每一个招聘需求都得到最优化的高效管理。

*   **智能候选人中心:** (敬请期待)
    构建企业动态人才资源库，AI驱动实现候选人与职位需求的多维度智能匹配。自动化初步筛选与标签化管理，显著提升人才甄选的效率与精准度。

*   **AI赋能面试流程:** (敬请期待)
    从智能面试排期、协同面试官操作，到结构化面试反馈的便捷记录。更可体验AI生成的深度定制化面试问题与多维度评估报告，确保每一场面试都富有洞见，助力企业实现科学、高效的人才选拔。

请通过左侧导航栏，深度体验各核心模块，即刻开启您的高效智能招聘新纪元。
""")

logger.info("Rendering Home page UI elements.")

# TODO: 可以将原 main_ui.py 中的全局配置（如 logger, BACKEND_URL）移到此处或一个通用的 config/utils 文件中。
# logger = ... (全局logger已在此文件顶部配置)
# BACKEND_URL = ... (如果需要全局访问，可以定义在这里或config文件中)

logger.info("Home.py script execution completed and UI rendered.") 