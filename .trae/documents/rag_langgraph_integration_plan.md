# 选课系统后端第二阶段业务功能计划 (Plan)

## 总结
本阶段将为选课系统引入非结构化知识库（RAG）功能，并将其与 LangGraph 工作流深度整合。主要任务包括：识别并处理 `数据文件` 目录下的官方文档与学生评价，构建 ChromaDB 向量索引（附加丰富的元数据），实现专门的 RAG 检索工具，以及在 LangGraph 中增加相应的路由逻辑（官方文档、学生评价、混合检索）。同时，将调整 SSE 接口以展示更友好的执行状态，屏蔽模型内部的深度思考过程。

## 当前状态分析
- **数据库**：第一阶段已成功搭建结构化数据库与查询工具，并且可以成功查询课程信息。
- **工作流**：目前 `workflow.py` 的路由仅区分 `mysql` 和 `rag`，且 `rag` 节点仅为 Mock 返回，未实现真实检索。
- **接口**：`chat.py` 返回完整的思考过程和最终回复，但未针对工具调用过程发送友好的进度状态。
- **数据**：`数据文件` 目录下已存在相关的 Markdown 文件，尚未进行切分与向量化。

## 拟议变更与实施步骤

### 1. 文档处理与向量库建设 (`app/rag/`)
- **`document_loader.py`**: 实现读取 Markdown 文件，通过正则表达式或简单的文件解析提取内容，并基于文件名识别 `source_type` (`official_programme_plan`, `official_selection_guide`, `student_review`)。
- **`text_splitter.py`**: 使用 LangChain 的 `RecursiveCharacterTextSplitter` 对文档进行切分，每个 chunk 控制在 500-800 字符，保留 100 字符的 overlap。
- **`vector_store.py`**: 封装基于 ChromaDB 的向量存储，使用 `langchain-openai` 的 `OpenAIEmbeddings`（调用阿里云兼容接口）或默认的本地 Embedding。
- **元数据处理**: 在切分时附加要求的 metadata，包括 `doc_id`, `file_name`, `source_type`, `source_tier`, `is_official`, `course_name` (若能提取), `teacher_name` (若能提取), `course_code` (若能提取), `created_at`, `chunk_index`。

### 2. 知识库构建脚本 (`app/scripts/build_rag_index.py`)
- 提供命令行参数 `--rebuild` 以清空并重建索引。
- 依次读取并切分 Markdown 文件，注入对应的 metadata。
- 将生成的 chunks 写入 ChromaDB，并在终端打印统计信息。

### 3. RAG 检索工具封装 (`app/tools/rag_tools.py`)
- 封装三个主要的检索工具：
  - `retrieve_official_docs(query, top_k=5)`：通过 ChromaDB 的 filter 按 `is_official=True` 或 `source_tier=tier_2_official_document` 过滤。
  - `retrieve_student_reviews(query, top_k=5)`：按 `source_tier=tier_3_student_review` 过滤。
  - `retrieve_all_knowledge(query, top_k=8)`：不加过滤条件。
  - `format_rag_evidence(docs)`：将文档格式化为可读的 evidence 字符串。

### 4. 完善 LangGraph 工作流 (`app/agent/workflow.py`)
- **扩展 Router**: 根据意图将问题路由至 `mysql_query`, `official_doc_rag`, `student_review_rag`, `hybrid_sql_rag` 或 `fallback`。
- **实现 RAG 节点**: `official_doc_rag_node` 和 `student_review_rag_node` 将调用对应的 RAG 工具检索上下文。
- **实现 Hybrid 节点**: 针对混合问题，同时调用 MySQL 工具和 RAG 工具，拼接上下文。
- **防幻觉策略**: 若任何节点检索不到足够数据，在上下文明确提示“未找到相关信息”。

### 5. 更新 Prompt 与回答生成策略 (`app/agent/policies.py`)
- 修改 `SYSTEM_PROMPT_TEMPLATE`，引入 Source-Tier-Aware 的指导原则。
- 规定回答的结构必须分为：官方信息、学生评价/经验反馈、建议、依据来源，并明确规定不得将学生评价作为官方结论。

### 6. 更新 SSE 接口输出 (`app/api/chat.py`)
- 修改 `stream_agent_response`。
- 拦截模型的 `reasoning_content`，不直接返回给前端。
- 在 LangGraph 执行到不同节点时（如 `router`, `mysql_query`），向前端 yield 对应的状态提示（如“正在查询课程结构化数据库”）。
- 在最终输出中确保包含 `answer`, `route`, `source_type`, `evidence`, `confidence`, `used_tools` 等字段。

### 7. 测试与文档更新
- **`app/scripts/test_rag_workflow.py`**: 增加针对 RAG 和路由逻辑的验证脚本。
- **`README.md`**: 补充构建 RAG 知识库、测试工作流及数据分类的说明。

## 假设与决策
- 假设用户的阿里云 API Key 支持调用 Embedding 模型（默认可用 `text-embedding-v3` 兼容模型，或我们将显式配置一个免费好用的阿里云 embedding 模型，如 `text-embedding-v1`）。
- 从评价文件中提取课程名称和教师名称时，将尽量使用正则匹配或在 metadata 中先设定默认值，保证系统的稳定性。

## 验证步骤
1. 运行 `build_rag_index.py` 查看统计信息与本地数据库文件生成。
2. 运行 `test_rag_workflow.py`，检查针对不同意图的提问是否能够路由至正确的节点，并返回带有合理证据的回答。
3. 检查控制台及输出，确保回答中未暴露模型内部的深度思考内容。
