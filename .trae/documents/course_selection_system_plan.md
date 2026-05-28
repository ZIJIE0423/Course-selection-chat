# 选课系统后端开发框架计划 (Plan)

## 总结
为选课系统构建一个模块化的后端开发框架，基于 FastAPI 提供 API 服务，使用 LangGraph 编排多智能体工作流（智能路由至 MySQL 结构化查询或 RAG 检索）。结合 Playwright 爬虫与 Chroma 向量数据库进行非结构化数据的抓取与检索，并集成阿里云百炼（Qwen3.7-max）大模型。项目将使用 Conda 管理 Python 运行环境，使用 `uv` 快速管理依赖包。

## 当前状态分析
当前项目目录（`c:\Users\24847\Desktop\实习\RAG系统`）基本为空（仅存在一个 `数据文件` 目录），需要从零搭建项目脚手架、配置文件、环境管理以及核心代码目录结构。系统已具备 `conda` 和 `uv` 工具支持。

## 架构与技术栈决策
基于与用户的沟通和系统要求，做出以下架构决策：
1. **Web框架**: FastAPI。高性能且原生支持异步，非常适合对接 Playwright 和 LangGraph，同时支持自动生成 API 文档供前端 ChatUI 对接。
2. **环境管理**: Conda 用于隔离 Python 版本环境，`uv` 用于项目级依赖的极速管理。
3. **关系型数据库**: MySQL 存储结构化数据（课程、教师等），通过 SQLAlchemy 进行 ORM 映射。
4. **向量数据库**: ChromaDB。采用本地化存储模式，无需额外部署容器或服务，便于快速开发验证。
5. **RAG与工作流编排**: 纯 LangChain / LangGraph 方案。构建 Agent 工作流，将用户问题路由至“课程库(MySQL)”或“知识库(RAG)”。
6. **大模型集成**: 阿里云 DashScope 平台提供的 `qwen3.7-max`（深度思考模型），结合提供的 API 样例代码进行封装。
7. **数据爬取**: Playwright（异步），用于定时抓取校园论坛、官网公告等动态信息并交由 RAGFlow 处理。

## 拟议变更与实施步骤

**第一步：环境与依赖初始化**
- 使用 `conda` 创建环境 `rag_course_system`（Python 3.10+）。
- 初始化 `pyproject.toml`，并使用 `uv` 安装项目核心依赖：
  `fastapi`, `uvicorn`, `langchain`, `langgraph`, `langchain-openai`, `chromadb`, `sqlalchemy`, `pymysql`, `playwright`, `python-dotenv`。
- 安装 Playwright 浏览器内核。

**第二步：目录结构与脚手架搭建**
在项目根目录构建如下标准后端结构：
```text
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/                    # API 路由定义 (例如 chat 接口)
│   ├── core/                   # 核心配置 (config.py 读取环境变量)
│   ├── database/               # 数据库连接 (mysql.py, chroma_db.py)
│   ├── models/                 # SQLAlchemy 实体模型定义 (课程、教师)
│   ├── agent/                  # Agent 层核心逻辑
│   │   ├── workflow.py         # LangGraph 状态图与路由编排
│   │   ├── llm.py              # Qwen3.7-max 实例化与思考过程处理
│   │   └── policies.py         # 提示词和系统策略管理
│   ├── rag/                    # 知识库处理 (切分、向量化、检索引擎)
│   └── crawler/                # Playwright 数据抓取模块
├── .env                        # 环境变量文件 (包含 API Key 和 DB 配置)
├── .gitignore
└── pyproject.toml              # uv 依赖清单
```

**第三步：核心模块骨架编写**
- **配置与LLM模块**：在 `.env` 中写入 `DASHSCOPE_API_KEY`，并在 `app/agent/llm.py` 中参考提供的样例代码，封装可对接 LangChain/LangGraph 的 Qwen 调用类。
- **LangGraph工作流**：在 `workflow.py` 中定义包含“用户提问”、“意图识别/路由”、“MySQL查询节点”、“RAG检索节点”和“综合生成节点”的状态图 (StateGraph)。
- **Web接口**：在 `app/api/chat.py` 暴露 `/chat` 接口，支持基于 SSE (Server-Sent Events) 的流式输出，以便前端实时展示深度思考模型的“思考过程”与“最终回复”。
- **爬虫模块**：在 `app/crawler` 提供基于 Playwright 的爬虫入口模板，预留入库向量数据库的接口。

**第四步：验证步骤**
- 验证 Conda 环境和所有依赖是否被正确安装。
- 启动 FastAPI 本地服务器 (`uvicorn app.main:app --reload`)，验证是否能正常访问 `/docs` 文档。
- 确保项目架构清晰，各层级（用户层、Agent层、数据层、接口层）代码职责明确。