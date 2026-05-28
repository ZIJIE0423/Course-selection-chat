# 选课系统后端第三阶段业务功能计划 (Plan)

## 总结
本阶段的目标是为选课系统构建评测闭环与对话需求沉淀功能。首先，开发基于结构化测试集与多种核心指标的评测模块，量化验证当前路由与 RAG/SQL 的融合效果。其次，增加会话日志及学生需求分析沉淀模块，利用大模型从交互文本中提取选课关注点（如时间偏好、给分要求等）进行脱敏存储。最后，提供供管理后台调用的 API 接口，以及更新项目文档。

## 拟议变更与实施步骤

### 1. 数据库模型扩展
- 在 `app/models/` 目录下新增 `log.py`，定义以下 SQLAlchemy 模型：
  - `ConversationLog`: 记录每次对话的用户提问、系统回答、命中路由、数据源类型、使用工具、证据摘要和创建时间等。
  - `StudentNeedSummary`: 记录每次会话分析出的学生需求，包括关注课程/教师、偏好标签、关注点、提取摘要以及脱敏标识等。
- 修改 `app/main.py` 导入这些新模型，以便 `Base.metadata.create_all()` 能够自动建表。

### 2. 对话记录与需求沉淀模块 (`app/memory/`)
- **`conversation_logger.py`**: 提供保存 `ConversationLog` 的函数，将完整对话记录持久化至数据库。
- **`preference_extractor.py`**: 利用 `app.agent.llm.get_llm()` 调用大模型，将用户提问和回答作为输入，要求以 JSON 格式输出标准化需求标签（含脱敏策略，剔除 PII 信息）。
- **`need_summary.py`**: 提供入口函数，整合前两步操作。接收一次完整会话的信息，先保存对话日志，再异步或同步调用大模型进行需求提取，最终存入 `StudentNeedSummary`，并返回是否成功入库。

### 3. API 接口更新
- **改造 `/api/v1/chat` (`app/api/chat.py`)**:
  - 在 SSE 流式输出中积累完整的回答字符串 (`full_answer`)。
  - 在生成结束后，调用 `need_summary.py` 的处理逻辑。
  - 最终向前端 yield 一条附加消息：`{"type": "meta", "need_summary_saved": true/false}`。
- **管理后台接口 (`app/api/admin.py`)**:
  - 新增 API 路由文件 `admin.py`，包含：
    - `GET /api/v1/admin/needs/recent`: 获取最新需求列表。
    - `GET /api/v1/admin/needs/tags`: 获取全量标签分布统计。
    - `GET /api/v1/admin/conversations/recent`: 获取最新对话日志。
  - 在 `app/main.py` 中挂载该路由（`/api/v1/admin`）。

### 4. 评测模块开发 (`app/eval/`)
- **`test_cases.jsonl`**: 编写包含 40 条涵盖 6 种场景（事实、政策、评价、混合、无效、反事实）的测试用例。
- **`metrics.py`**: 编写核心指标计算函数（route_accuracy, source_type_accuracy, abstain_accuracy, citation_coverage, hallucination_flag, keyword_hit_rate, tool_usage_accuracy），并预留 RAGAS 评分字段。
- **`run_eval.py`**: 评测执行脚本，读取 jsonl，调用现有 Agent 工作流或通过模块调用获取回答，进行指标计算。
- **`eval_report.py`**: 将评测结果写入 `eval_outputs/eval_results.json`，并汇总生成 `eval_outputs/eval_summary.md` 报告。

### 5. 文档更新 (`README.md`)
- 补充第三阶段的运行指引，包括评测执行命令 `uv run python app/eval/run_eval.py`、报告生成路径及管理后台接口说明。

## 验证步骤
1. 启动服务，发送几次 Chat 请求，观察返回流的末尾是否带有 `"need_summary_saved": true`。
2. 访问 Swagger UI (`/docs`)，调用 `/api/v1/admin/needs/recent` 等接口，检查是否能获取到刚刚保存的对话与需求提取数据。
3. 在命令行执行 `uv run python app/eval/run_eval.py`，检查控制台是否正常输出评测进度。
4. 检查 `eval_outputs/eval_summary.md` 是否成功生成并包含所有的指标数据。
