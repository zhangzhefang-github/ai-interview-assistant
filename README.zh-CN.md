[English Version](README.md)

# AI 面试助手

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- 根据需要添加更多徽章：构建状态、代码覆盖率等 -->

<YOUR_PROJECT_DESCRIPTION_HERE> <!-- 请在此处填写您的项目描述 -->

AI 面试助手是一个旨在通过利用人工智能完成诸如问题生成、职位描述分析、简历解析和面试报告生成等任务，从而帮助简化面试流程的平台。

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
- [项目结构](#项目结构)
- [贡献](#贡献)
- [许可证](#许可证)

## 特性

-   **职位管理**：创建、读取、更新和删除职位信息。
-   **候选人管理**：创建、读取、更新和删除候选人资料，包括简历解析。
-   **面试安排与管理**：安排和管理面试。
-   **AI 驱动的问题生成**：根据职位描述和候选人简历自动生成面试问题。
-   **AI 驱动的面试报告**：生成全面的面试评估报告。
-   **交互式前端**：一个基于 Streamlit 的前端，方便交互（如果适用）。

## 技术栈

-   **后端**：FastAPI, Python 3.13+
-   **前端**：Streamlit (如果适用，请描述其作用)
-   **数据库**：MySQL
-   **ORM**：SQLAlchemy
-   **数据库迁移**：Alembic
-   **依赖管理**：uv
-   **Python 版本管理**：pyenv
-   **测试**：Pytest
-   **AI 集成**：Langchain, OpenAI

## 先决条件

-   Python 3.13+ (建议通过 `pyenv` 管理)
-   已安装 `pyenv` (参见 [pyenv 安装指南](https://github.com/pyenv/pyenv#installation))
-   已安装 `uv` (参见 [uv 安装指南](https://github.com/astral-sh/uv#installation))
-   MySQL 服务器正在运行且可访问。
-   一个 OpenAI API 密钥。

## 安装

1.  **克隆仓库：**
    ```bash
    git clone <YOUR_REPOSITORY_URL> <!-- 请在此处填写您的仓库 URL -->
    cd ai-interview-assistant
    ```

2.  **使用 pyenv 设置 Python 版本：**
    ```bash
    pyenv install $(cat .python-version) # 安装 .python-version 文件中指定的版本
    pyenv local $(cat .python-version)   # 为项目设置本地 Python 版本
    ```

3.  **创建并激活虚拟环境 (可选但推荐，uv 可以管理此过程)：**
    `uv` 可以在有或没有显式激活的虚拟环境下工作。如果您倾向于创建一个：
    ```bash
    python -m venv .venv
    source .venv/bin/activate # Windows 系统: .venv\\Scripts\\activate
    ```
    或者，您可以让 `uv` 隐式管理其自身的环境。

4.  **使用 uv 安装依赖：**
    ```bash
    # uv pip install -r requirements.txt # requirements.txt 已被移至 .gitignore
    uv pip install . # 从 pyproject.toml 安装依赖
    uv pip install -e ".[test]" # 安装可选的测试依赖
    ```
    *注意：依赖主要通过 `pyproject.toml` 和 `uv.lock` 管理。*

## 环境配置

本项目使用 `.envrc` (可选，用于 `direnv`) 和 `.env` 文件进行环境变量配置。

1.  **`direnv` (可选)：**
    如果您使用 `direnv`，当您 `cd` 进入项目目录时，它会自动激活 Python 虚拟环境 (如果在 `.envrc` 中配置过)。请确保您的 `.envrc` 设置正确 (例如，用于加载 `.venv/bin/activate` 脚本或管理 `pyenv`)。
    `.envrc` 内容示例 (如果尚未存在或不正确)：
    ```bash
    # .envrc 内容示例
    # layout python # 如果您将 pyenv 与 direnv 结合使用
    # 或者
    # source .venv/bin/activate # 如果使用 .venv
    echo "已激活项目环境。"
    ```
    创建或修改 `.envrc` 后，请记得运行 `direnv allow`。

2.  **`.env` 文件：**
    此文件用于存储敏感凭据和特定于环境的配置。它 **不会** 被提交到版本控制。
    通过复制示例文件 (如果您创建了 `env.example`) 或手动创建，在项目根目录下创建一个 `.env` 文件：
    ```bash
    cp env.example .env # 如果您提供了 env.example
    # 或手动创建 .env
    ```
    使用必要的变量填充 `.env` 文件。至少，您将需要：
    ```ini
    OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>" <!-- 请在此处填写您的 OpenAI API Key -->
    # 主应用程序的数据库 URL
    DATABASE_URL="mysql+pymysql://user:pass@host:port/dbname" <!-- 请确认或提供 -->
    # 测试用的数据库 URL (pytest 通过 pytest-dotenv 使用此变量)
    TEST_MYSQL_DATABASE_URL="mysql+pymysql://testuser:testpass@localhost:3306/testdb" <!-- 请确认或提供 -->
    # 您的应用程序可能需要的其他环境变量
    ```
    **重要提示**：请将占位符替换为您的实际凭据和数据库连接字符串。确保指定的数据库存在，并且用户具有必要的权限。

## 运行应用程序

### FastAPI 后端

1.  **确保您的虚拟环境已激活 (如果您显式创建了一个) 并且 `.env` 文件已正确填充。**
2.  **运行数据库迁移 (如果是首次运行或有新的迁移)：**
    ```bash
    alembic upgrade head
    ```
3.  **使用 Uvicorn 启动 FastAPI 开发服务器：**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    API 通常可在 `http://localhost:8000` 访问。
    自动生成的 API 文档位于 `http://localhost:8000/docs`。

### Streamlit 前端 (如果适用)

1.  **确保您的虚拟环境已激活并且 `.env` 文件已正确填充。**
2.  **导航到 Streamlit 应用目录 (如果它是独立的)：**
    ```bash
    cd streamlit_app # 或您的 Streamlit 应用目录
    ```
3.  **运行 Streamlit 应用程序：**
    ```bash
    streamlit run main_streamlit.py # 请将 main_streamlit.py 替换为您的入口脚本
    ```
    Streamlit 应用通常可在 `http://localhost:8501` 访问。

## 运行测试

1.  **确保您的虚拟环境已激活，并且 `.env` 文件中的 `TEST_MYSQL_DATABASE_URL` 已为您的测试数据库正确配置。**
    `pytest-dotenv` 插件会自动从 `.env` 文件加载变量。
2.  **使用 Pytest 运行测试：**
    ```bash
    pytest
    ```
    您可以通过指定路径或标记来运行特定的测试：
    ```bash
    pytest tests/api/v1/test_interviews.py
    pytest -m "marker_name"
    ```

## 数据库迁移

本项目使用 Alembic 进行数据库模式迁移。

-   **在更改 SQLAlchemy 模型后生成新的迁移脚本：**
    ```bash
    alembic revision -m "更改的简短描述"
    ```
    然后，编辑 `alembic/versions/` 目录中生成的脚本以定义升级和降级操作。

-   **将迁移应用到您的数据库：**
    ```bash
    alembic upgrade head
    ```

-   **降级到特定版本：**
    ```bash
    alembic downgrade <版本标识符>
    ```

-   **查看当前的数据库修订版本：**
    ```bash
    alembic current
    ```

## 项目结构

    .
    ├── alembic/                  # Alembic 迁移脚本
    ├── app/                      # 主应用程序源代码 (FastAPI)
    │   ├── api/                  # API 特定模块 (路由, schemas)
    │   │   └── v1/
    │   ├── core/                 #核心逻辑, 配置
    │   ├── db/                   # 数据库模型, 会话管理
    │   ├── services/             # 业务逻辑, AI 服务集成
    │   └── main.py               # FastAPI 应用程序入口点
    ├── streamlit_app/            # Streamlit 前端应用程序 (如果适用)
    ├── tests/                    # 测试套件
    ├── env.example               # 环境变量示例文件 (可选, 推荐做法)
    ├── .envrc                    # Direnv 配置 (可选)
    ├── .gitignore                # Git 忽略的文件和目录
    ├── .python-version           # 项目的 pyenv Python 版本
    ├── alembic.ini               # Alembic 配置文件
    ├── pyproject.toml            # 项目元数据和依赖 (用于 uv/PEP 517 工具)
    ├── pytest.ini                # Pytest 配置
    ├── README.md                 # 本文件 (英文版)
    ├── README.zh-CN.md           # 本文件 (中文版)
    └── uv.lock                   # uv 锁文件，用于可复现的依赖

## 贡献

欢迎贡献！请遵循以下步骤：

1.  Fork 本仓库。
2.  创建一个新分支 (`git checkout -b feature/your-feature-name`)。
3.  进行更改。
4.  确保测试通过 (`pytest`)。
5.  提交您的更改 (`git commit -m 'Add some feature'`)。
6.  将分支推送到远程仓库 (`git push origin feature/your-feature-name`)。
7.  创建一个 Pull Request。

请确保您的代码符合项目中使用的任何 linting 和格式化标准 (例如，Ruff, Black - 如果尚未使用，请考虑添加它们)。

## 许可证

本项目采用 MIT 许可证授权 - 详情参见 [LICENSE](LICENSE.md) 文件 (如果您选择此许可证，您需要创建一个包含 MIT 许可证文本的 `LICENSE.md` 文件)。 