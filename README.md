# 选课系统智能问答后端框架

本项目是一个基于 FastAPI、LangGraph、Chroma 和 Qwen3.7-max 构建的选课系统智能问答后端。支持将结构化课程事实与非结构化知识文档结合，实现混合式的检索与问答生成。

## 第一阶段功能特性

1. **多格式数据导入**：支持从 `.md` 表格等格式的官方数据文件解析并规范化课程事实数据。
2. **关系型数据库结构**：利用 SQLAlchemy 管理课程实体(`Course`)与相关约束(`CourseRequirement`)，持久化至关系型数据库。
3. **Agent 工作流**：基于 LangGraph 构建。支持智能意图识别与路由，针对明确包含“课程代码”、“学分”、“课程名称”等强事实性提问，强制路由至 SQL 查询工具；针对模糊问题则路由至知识库检索（RAG）。
4. **实时流式响应**：基于 SSE 提供流式回复接口，展示深度思考大模型（Qwen3.7-max）的推理过程和回答。
5. **精准信息溯源**：在 API 响应中明确标识 `route`（路由节点）、`source_type`（数据源）以及 `evidence`（佐证数据），保障无幻觉回答。

## 第二阶段功能特性

本阶段引入了非结构化知识库（RAG）功能，并与 LangGraph 工作流深度整合，实现：

1. **多数据源混合检索**：系统可同时连接 MySQL 结构化数据库与 ChromaDB 向量知识库。
2. **文档分类与切分**：自动扫描 `数据文件` 下的 Markdown 文档，根据文件名智能分类为“官方培养方案”、“官方选课指导”、“学生课程评价”，并注入对应元数据（Metadata）。
3. **智能路由扩展**：在原有强事实问题（走 MySQL）基础上，支持将“选课规则/流程”类问题路由至官方文档 RAG，将“老师怎么样/给分如何”等主观问题路由至学生评价 RAG。同时支持 MySQL + RAG 的**混合检索 (Hybrid)**。
4. **防幻觉与来源隔离 (Source-Tier-Aware)**：在 Prompt 中明确规定官方信息与学生评价的区别，系统回答被强制要求分为：官方信息、学生经验反馈、建议、依据来源四个板块。

## 第三阶段功能特性

本阶段构建了**评测闭环与对话需求沉淀**功能，具体包括：

1. **多维指标评测体系**：新增 `app/eval/` 模块，包含覆盖 6 大查询场景的测试数据集。通过计算路由准确率、拒答逻辑准确率、关键词命中率等指标，量化评估 RAG + LangGraph 的整体性能。
2. **对话日志与需求提取**：基于大模型实现针对学生选课偏好的自动识别（在后台从对话文本中提取难度偏好、考核偏好等标签），并完成 PII 脱敏后沉淀入库（`ConversationLog` 与 `StudentNeedSummary`）。
3. **管理后台统计接口**：预留 `app/api/admin.py`，提供针对最新需求、全量标签分布的后台数据接口，为校方提供可视化的数据支撑。

## 第四阶段功能特性

本阶段实现了**Playwright 数据采集与知识库增量更新**，具体包括：

1. **多源数据采集**：支持从官网公告、公开选课指导页面、校园论坛/课程评价页面定期采集信息，包括官方通知（`official_notice`）和学生评价（`student_review`）。
2. **审核工作流**：采集数据经清洗后进入待审核区（`pending`状态），审核通过（`approved`）后再更新到 RAG 知识库，确保信息质量。
3. **智能路由优化**：当用户询问“最新选课通知”等关键词时，优先检索已审核并入库的官方公告；普通问答不触发实时浏览器采集，避免影响响应速度。
4. **定时任务**：使用 APScheduler 实现每周定时采集，同时提供手动执行命令方便测试。

## 快速开始

### 1. 环境准备

本项目采用 `conda` 隔离 Python 版本，使用 `uv` 极速管理依赖。

```bash
# 创建虚拟环境
conda create -y -n rag_course_system python=3.12
conda activate rag_course_system

# 安装依赖项与 Playwright 内核
uv sync
uv run playwright install
```

### 2. 数据库配置

项目默认使用 `SQLite` 作为本地测试关系型数据库，配置存储于 `.env`。
如果您需要切换至真实的 MySQL 服务器，请修改项目根目录的 `.env`：

```env
DASHSCOPE_API_KEY=sk-xxxxxxx
MYSQL_URL=mysql+pymysql://user:password@localhost:3306/course_db
CHROMA_DB_PATH=./chroma_data
```

### 3. 采集 URL 配置

在项目根目录的 `.env` 文件中配置要采集的 URL：

```env
# 官方公告/选课通知 URL（多个用逗号分隔）
CRAWL_NOTICE_URLS=https://jwgl.ouc.edu.cn/,https://example.com/notice

# 校园论坛/课程评价 URL（多个用逗号分隔）
CRAWL_FORUM_URLS=https://example.edu/forum,https://example.com/forums
```

> **注意**：多个 URL 之间必须用逗号分隔，不要添加空格

### 4. 数据导入与初始化

运行以下脚本，系统会自动在数据库中建表，并从 `数据文件` 目录解析导入结构化的课程数据：

```bash
uv run python app/scripts/import_courses.py
```
> **提示**：导入脚本具有幂等性，支持增量更新。

### 5. 构建 RAG 知识库索引

执行以下命令自动读取 `数据文件` 中的 `.md` 文件，切分文本并构建向量索引：

```bash
uv run python app/scripts/build_rag_index.py --rebuild
```
*执行成功后，项目根目录会生成 `./chroma_data` 文件夹。*

### 6. 手动运行爬虫

要立即执行数据采集，运行以下命令：

```bash
uv run python app/tasks/weekly_crawl.py
```

执行后，您将看到类似这样的输出：
```
=== 开始每周定时采集 ===

  官方公告采集: 3 条
  论坛评价采集: 5 条

=== 采集统计 ===
  采集总数: 8
  新增入库: 7
  跳过(重复): 1
  失败: 0
================
```

### 7. 查看待审核内容

启动服务后，使用以下命令查看待审核的采集内容：

```bash
curl http://localhost:8000/api/v1/admin/crawled/pending
```

响应示例：
```json
{
  "total": 8,
  "data": [
    {
      "id": 1,
      "title": "2024年春季学期选课通知",
      "content_preview": "各位同学：2024年春季学期选课将于下周一开启...",
      "source_url": "https://jwgl.ouc.edu.cn/notice/202402",
      "source_type": "official_notice",
      "source_tier": "tier_2_official_document",
      "hash_id": "a1b2c3...",
      "status": "pending",
      "crawled_at": "2024-02-15T10:30:00",
      "reviewed_at": null
    }
  ]
}
```

### 8. 审核流程

#### 审核通过

```bash
curl -X POST http://localhost:8000/api/v1/admin/crawled/1/approve
```

#### 驳回内容

```bash
curl -X POST http://localhost:8000/api/v1/admin/crawled/1/reject
```

#### 触发索引更新

```bash
curl -X POST http://localhost:8000/api/v1/admin/crawled/1/index
```

### 9. 启动服务

启动 FastAPI 服务：

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
访问 http://127.0.0.1:8000/docs 可以查看交互式 API 接口文档。

## 管理后台与评测

### 1. 运行评测框架

本项目内置了自动化评测脚本，用于量化系统性能：
```bash
uv run python app/eval/run_eval.py
```
运行完成后，可在 `eval_outputs/eval_summary.md` 查看详细的评测报告。

### 2. 管理后台接口

在服务启动后，可以通过以下预留的 Admin API 查看用户需求分布：
- `GET /api/v1/admin/needs/recent`：获取最新的学生需求沉淀列表。
- `GET /api/v1/admin/needs/tags`：获取全量需求标签的统计分布。
- `GET /api/v1/admin/conversations/recent`：获取最新的对话日志列表。
- `GET /api/v1/admin/crawled/pending`：获取待审核的采集内容

*(以上接口可访问 http://127.0.0.1:8000/docs 进行在线调用和调试)*

## 本地测试

我们提供了内置的测试脚本，用于快速验证 Agent 路由逻辑、SQL 工具与 RAG 检索：

```bash
# 测试第一阶段工作流
uv run python app/scripts/test_workflow.py

# 测试第二阶段 RAG 混合工作流
uv run python app/scripts/test_rag_workflow.py
```

**预期行为测试样例**：
1. **测试课程代码查询**  
   - 输入: `"008301100001 是什么课？"`  
   - 预期: 强制路由至 MySQL 节点，并输出《大学英语Ⅲ》的准确信息，附带来源"结构化数据库查询结果"。
2. **测试课程名称模糊查询**  
   - 输入: `"大学英语Ⅳ 的学分是多少？"`  
   - 预期: 提取"大学英语Ⅳ"关键词进行模糊匹配并路由至 MySQL，查询到课程信息并回复（若无学分数据则说明无法提供）。
3. **测试不存在的课程**  
   - 输入: `"NOTEXIST999 有这门课吗？"`  
   - 预期: 强制路由至 MySQL 节点，系统明确告知"未找到该课程信息"，**不会发生编造和幻觉**。
5. **测试 RAG 政策检索**  
   - 输入: `"选课流程是什么？"`  
   - 预期: 自动路由至官方文档 RAG 节点，返回《中国海洋大学选课指导.md》中的流程规范。
6. **测试主观评价与防幻觉隔离**  
   - 输入: `"张圆圆的大学英语怎么样？"`  
   - 预期: 自动路由至学生评价 RAG 节点，返回学生的主观反馈。并在回答排版中明确划分"学生评价/经验反馈"与"官方信息"，告知用户这仅仅是非官方参考。
7. **测试 Hybrid 混合查询**  
   - 输入: `"大学英语Ⅲ的学分是多少？这门课水不水？"`  
   - 预期: 同时调用 MySQL 查询（获取官方教师与课程基础数据）和 RAG 查询（获取学生评价），生成混合的、分层级的回答。
8. **测试最新公告查询**  
   - 输入: `"最近选课通知"`  
   - 预期: 自动路由至官方公告 RAG 节点，返回最近审核通过的选课通知内容。
9. **测试无公告情况**  
   - 输入: `"最新选课通知"`（当知识库中无公告时） 
   - 预期: 返回"当前知识库未检索到最新公告，请以教务系统通知为准。"
10. **测试普通问答**  
    - 输入: `"帮我推荐一门选修课"`  
    - 预期: 不触发爬虫采集，正常进行知识库检索和回答，响应速度符合预期。