[English Version](README.md)

# AI 面试助手

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- 根据需要添加更多徽章：构建状态、代码覆盖率等 -->

AI 面试助手是一个旨在通过利用人工智能完成诸如职位描述分析、简历解析、面试问题生成、多轮面试过程记录和全面的面试评估报告（包括结构化能力评估）等任务，从而帮助简化面试流程的平台。

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
- [未来潜在增强功能](#未来潜在增强功能)
- [贡献](#贡献)
- [许可证](#许可证)

## 特性

-   **职位管理**：创建、读取、更新和删除职位信息。
-   **候选人管理**：创建、读取、更新和删除候选人资料，包括基于AI的简历解析以提取结构化数据。
-   **面试安排与管理**：安排和管理面试生命周期（例如，从待生成问题到报告已生成的状态更新）。
-   **AI驱动的问题生成**：基于AI分析的职位描述和候选人简历自动生成面试问题。
-   **交互式面试过程记录**：一个聊天风格的界面，用于记录多轮面试对话，将对话与预生成问题或即席输入相关联。
-   **AI驱动的面试报告**：基于面试对话、职位描述和简历生成全面的面试评估报告。包括：
    -   整体评估。
    -   1-5分制的能力维度分析。
    -   优点与待发展点。
    -   自动提取结构化能力评分（例如，用于雷达图）。
-   **报告查看与可视化**：显示生成的报告及相关的能力评估雷达图。
-   **动态UI元素**：通过 `st.popover` 动态加载"常用追问角度"等功能以增强用户体验。

## 技术栈

-   **后端**：FastAPI, Python 3.13+
-   **前端**：Streamlit
-   **数据库**：MySQL
-   **ORM**：SQLAlchemy
-   **数据库迁移**：Alembic
-   **依赖管理**：uv
-   **Python 版本管理**：pyenv (可选，为保持一致性)
-   **测试**：Pytest, `pytest-dotenv`
-   **AI 集成**：Langchain, OpenAI (或兼容的 API)
-   **环境变量管理**：`python-dotenv`

## 先决条件

-   Python 3.13+ (建议通过 `pyenv` 管理以保持一致性)
-   已安装 `pyenv` (如果使用，请参见 [pyenv 安装指南](https://github.com/pyenv/pyenv#installation))
-   已安装 `uv` (参见 [uv 安装指南](https://github.com/astral-sh/uv#installation))
-   MySQL 服务器正在运行且可访问。
-   一个 OpenAI API 密钥，如果使用代理或自定义端点，则可能还需要一个基础 URL。

## 安装

1.  **克隆仓库：**
    ```bash
    git clone <YOUR_REPOSITORY_URL> # 替换为您的实际仓库 URL
    cd ai-interview-assistant
    ```

2.  **使用 pyenv 设置 Python 版本 (推荐)：**
    ```bash
    # 确保 .python-version 文件存在且包含目标 Python 版本 (例如, 3.13.0)
    pyenv install $(cat .python-version)
    pyenv local $(cat .python-version)
    ```

3.  **使用 uv 安装依赖：**
    ```bash
    uv pip install -e ".[test]" # 从 pyproject.toml 安装主要和测试依赖
    ```
    *依赖主要通过 `pyproject.toml` 和 `uv.lock` 管理。*

## 环境配置

本项目使用 `.env` 文件进行环境变量配置。

1.  **`.env` 文件：**
    此文件用于存储敏感凭据和特定于环境的配置。它 **不会** 被提交到版本控制 (`.gitignore` 应包含 `.env`)。
    在项目根目录下创建一个 `.env` 文件：
    ```bash
    cp env.example .env # 如果您提供了 env.example，否则请手动创建
    ```
    使用必要的变量填充 `.env` 文件。关键变量包括：
    ```ini
    OPENAI_API_KEY="sk-your_openai_api_key_here"
    OPENAI_API_BASE="https://api.openai.com/v1" # 或者您自定义的基础 URL (如果适用)

    # 主应用程序 (FastAPI) 的数据库 URL
    DATABASE_URL="mysql+pymysql://user:password@host:port/dbname"

    # 测试用的数据库 URL (pytest 通过 pytest-dotenv 使用此变量)
    TEST_MYSQL_DATABASE_URL="mysql+pymysql://testuser:testpass@localhost:3306/testdb"

    # 示例: API_LOG_LEVEL="INFO"
    ```
    **重要提示**：
    - 请将占位符替换为您的实际凭据和数据库连接字符串。
    - 确保指定的数据库 (例如 `dbname`, `testdb`) 存在，并且用户具有必要的权限。
    - 后端应用程序 (`app/main.py`) 使用 `python-dotenv` 加载这些变量。
    - Pytest 使用 `pytest-dotenv` 在测试期间加载这些变量，特别是 `TEST_MYSQL_DATABASE_URL`。

## 运行应用程序

### FastAPI 后端

1.  **确保您的虚拟环境 (如果显式管理) 已激活并且 `.env` 文件已正确填充。**
2.  **运行数据库迁移 (如果是首次运行或有新的迁移)：**
    ```bash
    alembic upgrade head
    ```
3.  **使用 Uvicorn 启动 FastAPI 开发服务器：**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    - API 通常可在 `http://localhost:8000` 访问。
    - 自动生成的 API 文档 (Swagger UI) 位于 `http://localhost:8000/docs`。
    - 备选文档 (ReDoc) 位于 `http://localhost:8000/redoc`。

### Streamlit 前端

1.  **确保您的虚拟环境 (如果显式管理) 已激活并且 `.env` 文件已正确填充。** (如果 Streamlit 应用有任何直接的客户端API调用，它也会从 `OPENAI_API_KEY` 受益，尽管通常它通过 FastAPI 后端进行交互)。
2.  **运行 Streamlit 应用程序：**
    ```bash
    python -m streamlit run streamlit_app/app_navigator.py --server.port 8501
    ```
    - Streamlit 应用通常可在 `http://localhost:8501` 访问。

## 运行测试

1.  **确保 `.env` 文件中的 `TEST_MYSQL_DATABASE_URL` 已为您的测试数据库正确配置。** `pytest-dotenv` 插件会自动从 `.env` 文件加载变量。
2.  **使用 Pytest 运行测试：**
    ```bash
    pytest
    ```
    - 您可以通过指定路径或标记来运行特定的测试：
      ```bash
      pytest tests/api/v1/test_interviews.py
      pytest -m "marker_name" # 如果您使用 pytest 标记
      ```

## 数据库迁移

本项目使用 Alembic 进行数据库模式迁移。

-   **在更改 SQLAlchemy 模型 (`app/db/models.py`) 后生成新的迁移脚本：**
    使用 `--autogenerate` 让 Alembic 检测模型更改至关重要。
    ```bash
    alembic revision --autogenerate -m "在此描述您的更改，例如：add_conversation_log_to_interviews"
    ```
    然后，审查 `alembic/versions/` 目录中生成的脚本。通常，自动生成的脚本已足够，但复杂的更改可能需要手动调整。

-   **将迁移应用到您的数据库：**
    ```bash
    alembic upgrade head
    ```

-   **降级到特定版本 (请谨慎使用)：**
    ```bash
    alembic downgrade <版本标识符_或_相对步数_如_-1>
    ```

-   **查看当前的数据库修订版本：**
    ```bash
    alembic current
    ```

## 关键开发亮点与工作流

本项目通过几个关键阶段和问题解决步骤演进而来：

1.  **初始设置与测试**：确保了基本的 LLM 调用和 `pytest` 设置。通过集成 `pytest-dotenv` 遇到并解决了测试数据库 URL 的问题。
2.  **核心面试逻辑**：通过将测试负载与数据库模式（例如 `InterviewStatus` 枚举）和 Pydantic 模式对齐，修复了 API 测试中的数据截断错误（状态的 `DataError`）和断言错误。
3.  **AI 服务模拟**：修正了单元测试中 AI 服务调用的模拟路径，以确保适当的隔离。
4.  **时间戳处理**：通过将字符串解析为具有时区意识的 datetime 对象，解决了测试中的时间戳比较问题。
5.  **后端环境变量**：通过确保在 `app/main.py` 中调用 `load_dotenv()`，使得 `.env` 变量对后端可用，从而解决了 OpenAI 身份验证错误。
6.  **结构化面试日志记录**：
    -   从单个 `conversation_log` 文本字段演进为用于多轮对话的结构化 `InterviewLog` 表。
    -   这涉及 Pydantic 模式更新、用于日志创建/检索的新 API 端点以及 Alembic 迁移（`--autogenerate` 是关键）。
7.  **AI 报告生成与数据提取**：
    -   增强了 `app/core/prompts.py` 中的提示，以指示 AI 输出中文内容和用于能力评分的结构化 JSON。
    -   在后端实现了从 AI 的文本响应中提取此 JSON 并将其分开存储的逻辑（例如，存储在 `Interview` 模型的 `radar_data` 字段中）。
    -   优化了提示以约束 AI 评分（1-5分制）并最小化 JSON 块周围的无关文本。
8.  **前端用户体验增强 (`streamlit_app/`)**：
    -   **面试管理**：改进了加载指示器和反馈消息（使用候选人姓名，避免重复图标）。
    -   **面试过程记录**：
        -   使用 `st.chat_message` 和 `st.chat_input` 将日志记录页面从单个 `st.text_area` 转换为交互式聊天界面。
        -   从 `app/core/prompts.py` 动态加载"常用追问角度"，并使用 `st.popover` 显示它们，以避免UI混乱。
        -   改进了面试选择的显示（显示候选人/职位名称，中文状态）。
    -   **报告查看**：确保正确显示 AI 生成的报告文本和相关的雷达图数据。
9.  **数据库模式演进**：在模式更改和问题重新生成期间处理了外键约束（例如，为 `InterviewLog.question_id` 设置 `ondelete="SET NULL"`）。
10. **异步操作**：将 AI 服务调用（例如报告生成）迁移为使用 `async` 和 `await chain.ainvoke()`，以获得更好的性能和响应能力，尤其是在 FastAPI 后端。

## 项目结构

    .
    ├── alembic/                  # Alembic 迁移脚本和环境配置
    ├── app/                      # 主应用程序源代码 (FastAPI)
    │   ├── api/                  # API 特定模块
    │   │   └── v1/               # API 版本 1
    │   │       ├── endpoints/    # API 路由定义 (例如 interviews.py, jobs.py)
    │   │       └── schemas.py    # 用于请求/响应验证和序列化的 Pydantic 模式
    │   ├── core/                 #核心应用逻辑、配置和提示
    │   │   ├── config.py         # 应用设置 (可能来自 .env)
    │   │   └── prompts.py        # AI 服务的提示
    │   ├── db/                   # 数据库交互层
    │   │   ├── models.py         # SQLAlchemy ORM 模型
    │   │   ├── session.py        # 数据库会话管理 (get_db 依赖)
    │   │   └── crud/             # CRUD 操作 (可选, 可位于 services 或 endpoints 中)
    │   ├── services/             # 业务逻辑层, AI 服务集成
    │   │   ├── ai_services.py    # 用于与 LLM 交互以执行各种任务的客户端
    │   │   └── ai_report_generator.py # 生成 AI 报告的特定逻辑
    │   ├── utils/                # 实用功能 (例如 JSON 解析器)
    │   └── main.py               # FastAPI 应用程序入口点, 中间件, 路由包含
    ├── streamlit_app/            # Streamlit 前端应用程序
    │   ├── pages/                # Streamlit 应用的各个页面
    │   ├── utils/                # 前端特定实用程序 (例如 api_client.py)
    │   └── app_navigator.py      # Streamlit 主应用程序导航器/入口点
    ├── tests/                    # 测试套件 (Pytest)
    │   ├── api/                  # API 测试
    │   └── conftest.py           # Pytest fixtures 和配置
    ├── .env                      # 本地环境变量 (GIT 忽略)
    ├── env.example               # 环境变量示例文件
    ├── .gitignore                # Git 忽略的文件和目录
    ├── .python-version           # 项目的 pyenv Python 版本
    ├── alembic.ini               # Alembic 配置文件
    ├── pyproject.toml            # 项目元数据和依赖 (用于 uv/PEP 517 工具)
    ├── pytest.ini                # Pytest 配置
    ├── README.md                 # 本文件 (英文版)
    ├── README.zh-CN.md           # 本文件 (中文版)
    └── uv.lock                   # uv 锁文件，用于可复现的依赖

## 未来潜在增强功能

-   **集中化 `STATUS_DISPLAY_MAPPING`**：移至共享的实用程序模块以避免重复。
-   **实时协作/更新**：例如，如果涉及多个用户，可用于实时面试记录等功能。
-   **高级 AI 功能**：微调模型，更复杂的分析，针对特定领域知识的 RAG。
-   **用户身份验证与授权**：安全访问应用程序。
-   **CI/CD 流水线**：自动化测试和部署。
-   **全面的日志记录与监控**：用于生产环境。
-   **更稳健的错误处理**：提供详细的面向用户的错误消息。

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

本项目采用 MIT 许可证授权。(您应创建一个包含完整 MIT 许可证文本的 `LICENSE.md` 文件)。 