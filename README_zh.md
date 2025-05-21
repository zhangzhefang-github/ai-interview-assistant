[English](README.md)

# AI 面试助手

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)\n[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- 可根据需要添加更多徽章：构建状态、覆盖率等 -->

AI 面试助手是一个旨在利用 AI 技术简化面试流程的平台，其功能包括职位描述分析、简历解析、面试问题生成、多轮面试记录以及生成包含结构化能力评估的综合面试报告。

## 目录

- [特性](#特性)
- [技术栈](#技术栈)
- [先决条件](#先决条件)
- [安装](#安装)
- [环境配置](#环境配置)
- [运行应用程序](#运行应用程序)
  - [FastAPI 后端](#fastapi-后端)
  - [Streamlit 前端](#streamlit-前端)
- [运行测试](#运行测试)
- [数据库迁移](#数据库迁移)
- [关键开发亮点与工作流](#关键开发亮点与工作流)
- [项目结构](#项目结构)
- [未来可能的增强功能](#未来可能的增强功能)
- [贡献](#贡献)
- [许可证](#许可证)

## 特性

-   **职位管理**: 创建、读取、更新和删除职位信息。
-   **候选人管理**: 创建、读取、更新和删除候选人资料，包括利用 AI 解析简历以提取结构化数据。
-   **面试安排与管理**: 安排和管理面试生命周期（例如，从等待生成问题到报告已生成的状态更新）。
-   **AI 驱动的问题生成**: 基于 AI 分析的职位描述和候选人简历自动生成面试问题。
-   **交互式面试记录**: 类聊天界面，用于记录多轮面试对话，将对话与预生成问题或即席提问相关联。
-   **AI 驱动的面试报告**: 基于面试对话、JD 和简历生成全面的面试评估报告。包括：
    -   整体评估。
    -   能力维度分析（1-5分评分）。
    -   优点与待发展领域。
    -   自动提取结构化能力评分（例如，用于雷达图）。
-   **报告查看与可视化**: 显示生成的报告及相关的能力评估雷达图。
-   **动态UI元素**: 例如通过 `st.popover` 动态加载"常见追问问题"，以增强用户体验。

## 技术栈

-   **后端**: FastAPI, Python 3.13+
-   **前端**: Streamlit
-   **数据库**: MySQL
-   **ORM**: SQLAlchemy
-   **数据库迁移**: Alembic
-   **依赖管理**: uv
-   **Python 版本管理**: pyenv (可选, 推荐用于保持一致性)
-   **测试**: Pytest, `pytest-dotenv`
-   **AI 集成**: Langchain, OpenAI (或兼容的 API)
-   **环境变量管理**: `python-dotenv`

## 先决条件

-   Python 3.13+ (推荐使用 `pyenv` 管理以保持一致性)
-   已安装 `pyenv` (如果使用, 参见 [pyenv 安装指南](https://github.com/pyenv/pyenv#installation))
-   已安装 `uv` (参见 [uv 安装指南](https://github.com/astral-sh/uv#installation))
-   MySQL 服务器正在运行且可访问。
-   一个 OpenAI API 密钥，如果使用代理或自定义端点，则可能还需要一个基本 URL。

## 安装

1.  **克隆仓库:**
    ```bash
    git clone <YOUR_REPOSITORY_URL> # 替换为你的实际仓库 URL
    cd ai-interview-assistant
    ```

2.  **使用 pyenv 设置 Python 版本 (推荐):**
    ```bash
    # 确保 .python-version 文件存在且包含目标 Python 版本 (例如, 3.13.0)
    pyenv install $(cat .python-version)
    pyenv local $(cat .python-version)
    ```

3.  **使用 uv 安装依赖:**
    ```bash
    uv pip install -e ".[test]" # 从 pyproject.toml 安装主要和测试依赖
    ```
    *依赖项通过 `pyproject.toml` 和 `uv.lock` 管理。*

## 环境配置

本项目使用 `.env` 文件进行环境变量配置。

1.  **`.env` 文件:**
    此文件存储敏感凭据和特定于环境的配置。它 **不** 应提交到版本控制 (`.gitignore` 应包含 `.env`)。
    在项目根目录创建一个 `.env` 文件:
    ```bash
    cp env.example .env # 如果你提供了 env.example，否则请手动创建
    ```
    用必要的变量填充 `.env` 文件。关键变量包括:
    ```ini
    OPENAI_API_KEY="sk-your_openai_api_key_here"
    OPENAI_API_BASE="https://api.openai.com/v1" # 或者你的自定义基础 URL (如果适用)

    # 主应用程序 (FastAPI) 的数据库 URL
    DATABASE_URL="mysql+pymysql://user:password@host:port/dbname"

    # 测试用的数据库 URL (pytest 通过 pytest-dotenv 使用)
    TEST_MYSQL_DATABASE_URL="mysql+pymysql://testuser:testpass@localhost:3306/testdb"

    # 示例: API_LOG_LEVEL="INFO"
    ```
    **重要提示**：
    - 将占位符替换为你的实际凭据和数据库连接字符串。
    - 确保指定的数据库 (例如, `dbname`, `testdb`) 已存在，并且用户具有必要的权限。
    - 后端应用程序 (`app/main.py`) 使用 `python-dotenv` 加载这些变量。
    - Pytest 使用 `pytest-dotenv` 在测试期间加载这些变量，特别是 `TEST_MYSQL_DATABASE_URL`。

## 运行应用程序

### FastAPI 后端

1.  **确保你的虚拟环境（如果明确管理）已激活，并且 `.env` 文件已填充。**
2.  **运行数据库迁移 (如果是首次运行或有新的迁移):**
    ```bash
    alembic upgrade head
    ```
3.  **使用 Uvicorn 启动 FastAPI 开发服务器:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    - API 通常可在 `http://localhost:8000` 访问。
    - 自动生成的 API 文档 (Swagger UI) 将位于 `http://localhost:8000/docs`。
    - 备选文档 (ReDoc) 位于 `http://localhost:8000/redoc`。

### Streamlit 前端

1.  **确保你的虚拟环境（如果明确管理）已激活，并且 `.env` 文件已填充。** (如果 Streamlit 端有任何直接的客户端调用，它也会从 `OPENAI_API_KEY` 中受益，尽管通常它通过 FastAPI 后端进行交互)。
2.  **运行 Streamlit 应用程序:**
    ```bash
    python -m streamlit run streamlit_app/app_navigator.py --server.port 8501
    ```
    - Streamlit 应用通常可在 `http://localhost:8501` 访问。

## 运行测试

1.  **确保 `.env` 文件中的 `TEST_MYSQL_DATABASE_URL` 已为你的测试数据库正确配置。** `pytest-dotenv` 插件将自动从 `.env` 加载变量。
2.  **使用 Pytest 运行测试:**
    ```bash
    pytest
    ```
    - 你可以通过指定路径或标记来运行特定的测试:
      ```bash
      pytest tests/api/v1/test_interviews.py
      pytest -m "marker_name" # 如果你使用 pytest 标记
      ```

## 数据库迁移

本项目使用 Alembic 进行数据库模式迁移。

-   **在更改 SQLAlchemy 模型 (`app/db/models.py`) 后生成新的迁移脚本:**
    使用 `--autogenerate` 让 Alembic 检测模型更改至关重要。
    ```bash
    alembic revision --autogenerate -m "描述你的更改，例如：add_conversation_log_to_interviews"
    ```
    然后，审查 `alembic/versions/` 目录中生成的脚本。通常，自动生成的脚本已足够，但复杂的更改可能需要手动调整。

-   **将迁移应用到你的数据库:**
    ```bash
    alembic upgrade head
    ```

-   **降级到特定版本 (谨慎使用):**
    ```bash
    alembic downgrade <version_identifier_or_relative_step_like_-1>
    ```

-   **查看当前的数据库修订版本:**
    ```bash
    alembic current
    ```

## 关键开发亮点与工作流

此项目经历了几个关键阶段和问题解决步骤，包括最近的架构升级和错误修复：

*   **增强的环境与测试设置**：
    *   集成了 `pytest-dotenv`，以便在 `pytest` 执行期间自动从 `.env` 文件加载环境变量（如 `TEST_MYSQL_DATABASE_URL`）。这解决了最初的测试设置失败问题，并简化了测试环境管理。
*   **改进的数据库与模型完整性**：
    *   通过确保在更新过程中仅使用有效的 `InterviewStatus` 枚举成员（例如，纠正像 "SCHEDULED" 这样的无效值），解决了 `Interview.status` 字段的 `sqlalchemy.exc.DataError` 问题。
    *   通过向 `app.api.v1.schemas.InterviewInDBBase`（并因此影响 `InterviewOutputSchema`）添加 `updated_at` 字段，修正了 Pydantic schema 定义，使 API 响应与测试断言保持一致，并防止了因字段缺失导致的 `AssertionError`。
*   **提升的测试套件健壮性**：
    *   修正了 API 测试中（例如 `tests/api/v1/test_interviews.py`）的 `unittest.mock.patch` 目标。针对 AI 服务（如 `analyze_jd`）的 mock 已更新，以使其指向函数被查找的路径（例如 `'app.api.v1.endpoints.interviews.analyze_jd'`），而不是其定义位置，从而确保了测试期间服务的有效隔离。
    *   改进了时间戳断言，例如在 `test_update_interview_success` 中，通过将 API 响应中的日期时间字符串解析为带时区的 `datetime` 对象进行比较。这使得测试对微小的格式差异更具弹性，并确保了准确的检查（例如，`updated_at > created_at`）。
*   **LangChain v0.3.x 适配**: 更新了 LangChain 的使用方式以符合 v0.3.x 版本标准，主要涉及采用 `Runnable` 接口及 `ainvoke()` 等方法进行异步链式执行。这增强了与最新 LangChain 功能的兼容性，并通常能提高 I/O 密集型 AI 调用的性能。(此条目补充了现有的"异步操作"点)。
*   **Pydantic V2 迁移**: 将项目升级至使用 Pydantic V2。这包括利用其改进的性能、更严格的验证规则以及更新的 API（例如，模型配置和字段定义的变化）。这确保项目能够从最新的数据验证和序列化能力中受益。

1.  **初始设置与测试**: 确保基本的 LLM 调用和 `pytest` 设置。通过集成 `pytest-dotenv` 遇到并解决了测试数据库 URL 的问题。
2.  **核心面试逻辑**: 通过将测试负载与数据库模式（例如 `InterviewStatus` 枚举）和 Pydantic 模式对齐，修复了API测试中的数据截断错误（状态的 `DataError`）和断言错误。
3.  **AI 服务 Mocking**: 修正了单元测试中 AI 服务调用的 mock 路径，以确保正确的隔离。
4.  **时间戳处理**: 通过将字符串解析为带时区的 datetime 对象，解决了测试中时间戳比较的问题。
5.  **后端环境变量**: 通过确保在 `app/main.py` 中调用 `load_dotenv()`，使得 `.env` 中的变量可用于后端，解决了 OpenAI 认证错误。
6.  **结构化面试记录**:
    -   从单个 `conversation_log` 文本字段演变为用于多轮对话的结构化 `InterviewLog` 表。
    -   这涉及 Pydantic schema 更新、用于日志创建/检索的新 API 端点以及 Alembic 迁移（`--autogenerate` 是关键）。
7.  **AI 报告生成与数据提取**:
    -   增强了 `app/core/prompts.py` 中的提示，以指示 AI 输出中文并为能力评分输出结构化 JSON。
    -   在后端实现了从 AI 的文本响应中提取此 JSON 并将其分开存储的逻辑（例如，`Interview` 模型中的 `radar_data`）。
    -   优化了提示以限制 AI 评分（1-5分制）并最小化 JSON 块周围的无关文本。
8.  **前端用户体验增强 (`streamlit_app/`)**:
    -   **面试管理**: 改进了加载指示器和反馈消息（使用候选人姓名，避免重复图标）。
    -   **面试记录**:
        -   使用 `st.chat_message` 和 `st.chat_input` 将记录页面从单个 `st.text_area` 转换为交互式聊天界面。
        -   从 `app/core/prompts.py` 动态加载"常见追问问题"，并使用 `st.popover` 显示它们，以避免 UI 混乱。
        -   改进了面试选择的显示（显示候选人/职位名称，中文状态）。
    -   **报告查看**: 确保正确显示 AI 生成的报告文本和相关的雷达图数据。
9.  **数据库模式演进**: 在模式更改和问题重新生成期间处理了外键约束（例如，`InterviewLog.question_id` 的 `ondelete="SET NULL"`）。
10. **异步操作**: 将 AI 服务调用（例如报告生成）迁移到使用 `async` 和 `await chain.ainvoke()`，以获得更好的性能和响应能力，尤其是在 FastAPI 后端。

## 项目结构

    .
    ├── alembic/                  # Alembic 迁移脚本和环境配置
    ├── app/                      # 主应用程序源代码 (FastAPI)
    │   ├── api/                  # API 特定模块
    │   │   └── v1/               # API 版本 1
    │   │       ├── endpoints/    # API 路由定义
    │   │       └── schemas.py    # Pydantic schemas
    │   ├── core/                 # 核心应用程序逻辑、配置和提示
    │   │   ├── config.py         # 应用程序设置
    │   │   └── prompts.py        # AI 服务的提示
    │   ├── db/                   # 数据库交互层
    │   │   ├── models.py         # SQLAlchemy ORM 模型
    │   │   ├── session.py        # 数据库会话管理
    │   │   └── crud/             # CRUD 操作
    │   ├── services/             # 业务逻辑层, AI 服务集成
    │   │   ├── ai_services.py    # 与 LLM 交互的客户端
    │   │   └── ai_report_generator.py # AI 报告生成逻辑
    │   ├── utils/                # 实用功能
    │   └── main.py               # FastAPI 应用程序入口点 (app.main:app)
    ├── streamlit_app/            # Streamlit 前端应用程序
    │   ├── pages/                # Streamlit 应用的各个页面
    │   ├── utils/                # 前端特定实用程序
    │   └── app_navigator.py      # 主 Streamlit 应用程序导航器/入口点
    ├── tests/                    # 测试套件 (Pytest)
    │   ├── api/                  # API 测试
    │   └── conftest.py           # Pytest fixtures 和配置
    ├── static/                   # 静态文件 (例如 CSS, JS, 图像)
    ├── .conda-env                # Conda 环境文件 (如果使用 Conda)
    ├── .envrc                    # direnv 环境配置文件 (如果使用 direnv)
    ├── .gitignore                # Git 忽略的文件和目录
    ├── .python-version           # 项目的 pyenv Python 版本
    ├── .test_migration_env       # 测试数据库迁移环境配置文件
    ├── alembic.ini               # Alembic 配置文件
    ├── ai_interview_assistant.egg-info/ # Python 包构建信息 (egg)
    ├── build/                    # 构建输出目录
    ├── env.example               # 环境变量示例文件
    ├── LICENSE                   # 项目许可证文件
    ├── LICENSE.md                # 项目许可证文件 (Markdown)
    ├── main.py                   # 项目根目录下的主要脚本 (用途需根据实际情况说明)
    ├── migration_sanity_check.py # 数据库迁移健全性检查脚本
    ├── pyproject.toml            # 项目元数据和依赖项 (PEP 517/518)
    ├── pytest.ini                # Pytest 配置文件
    ├── README.md                 # 英文版 README
    ├── README_zh.md              # 本文件 (中文版 README)
    ├── requirements.txt          # 依赖项文件 (通常由 uv.lock 或 pyproject.toml 管理)
    └── uv.lock                   # uv lock 文件，用于可复现的依赖

## 未来可能的增强功能

-   **集中化 `STATUS_DISPLAY_MAPPING`**: 将其移至共享的实用程序模块以避免重复。
-   **实时协作/更新**: 用于涉及多个用户的实时面试记录等功能。
-   **高级 AI 功能**: 微调模型、更复杂的分析、用于领域特定知识的 RAG。
-   **用户认证与授权**: 保护应用程序的访问安全。
-   **全面的国际化与本地化**: 支持更多语言。
-   **CI/CD 流水线**: 自动化测试和部署。
-   **全面的日志记录与监控**: 用于生产环境。
-   **更稳健的错误处理**: 提供详细的面向用户的错误消息。

## 贡献

欢迎贡献！请遵循以下步骤：

1.  Fork 本仓库。
2.  创建一个新分支 (`git checkout -b feature/your-feature-name`)。
3.  进行更改。
4.  确保测试通过 (`pytest`)。
5.  提交您的更改 (`git commit -m 'Add some feature'`)。
6.  将分支推送到远程仓库 (`git push origin feature/your-feature-name`)。
7.  创建一个 Pull Request。

请确保您的代码符合项目中使用的任何 linting 和格式化标准 (例如，Ruff, Black 是不错的选择，如果尚未集成)。

## 许可证

本项目采用 MIT 许可证。详情请参阅 `LICENSE` 文件。 