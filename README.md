# WeOUC 智能选课知识与对话平台

本项目是面向中国海洋大学学生的智能选课知识与决策辅助平台。后端基于 FastAPI、LangGraph、Chroma 和 Qwen3.7-max，将结构化课程事实、培养方案、选课规则与经审核的学生经验组合到统一问答链路；前端提供可运行的高保真交互原型，用于验证学生信息确认、对话咨询、课程方案、来源追溯和经验投稿等完整流程。

平台只提供选课前的信息解释与决策参考，不代替教务系统执行选课、退课或成绩操作，也不会收集或保存教务系统密码。

## 当前交付内容

- **智能问答后端**：课程事实查询、官方文档 RAG、学生评价 RAG、混合检索、SSE 流式回答和信息来源标识。
- **数据与知识库**：课程数据导入、Markdown 文档切分、ChromaDB 索引和增量更新。
- **评测与需求沉淀**：路由、拒答和关键词命中评测，对话日志脱敏与学生需求标签提取。
- **采集与审核**：官方公告和公开学生评价采集、人工审核及审核后增量入库。
- **高保真前端原型**：学生信息确认、培养方案匹配、对话咨询、需求条件确认、课程方案卡、课程详情、依据抽屉、课表授权、结构化反馈和“我的”。

产品介绍文档见 [`docs/WeOUC智能选课知识与对话平台_产品介绍.pdf`](docs/WeOUC智能选课知识与对话平台_产品介绍.pdf)。

## 项目结构

```text
Course-selection-chat-main/
├── app/
│   ├── agent/              # LangGraph 工作流、模型与策略
│   ├── api/                # 对话与管理 API
│   ├── crawler/            # 官方公告和论坛内容采集
│   ├── database/           # SQLAlchemy 与 ChromaDB 连接
│   ├── eval/               # 评测指标、用例与报告
│   ├── memory/             # 对话记录和需求摘要
│   ├── rag/                # 文档加载、切分、索引与向量检索
│   └── tools/              # SQL 与 RAG 工具
├── frontend/               # 无构建步骤的高保真前端原型
│   ├── assets/css/         # 共享视觉系统与响应式样式
│   ├── assets/js/          # 页面交互、演示数据与 API 适配
│   ├── index.html          # 对话咨询入口
│   ├── onboarding.html     # 学生信息与培养方案确认
│   ├── history.html        # 历史课表上传、确认与记录
│   ├── course.html         # 实时课程详情与依据
│   ├── feedback.html       # 第二阶段结构化经验投稿（默认关闭）
│   └── profile.html        # 后端学生档案与历史课表摘要
├── 数据文件/                # 官方资料和学生评价参考
├── eval_outputs/           # 评测输出
└── pyproject.toml
```

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

### Windows 一键演示（推荐）

双击 `start_demo.bat`，或在 PowerShell 中执行：

```powershell
.\start_demo.ps1
```

脚本会同步锁定依赖、初始化独立的 `demo_course_db.sqlite`、导入演示培养方案和活动课程快照，并在 `8000` 端口同时启动 API 与 H5。随后访问 `http://127.0.0.1:8000/prototype/`。再次启动会幂等复用演示数据；若依赖已经同步，可用 `.\start_demo.ps1 -SkipSync` 加快启动。

演示课程和培养方案位于 `demo_data/`，均明确标记为样例数据。可在“历史课表”页面上传 `demo_data/history.csv`，完整体验上传确认、已修排除、自然语言筛选和真实课程详情。

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

复制环境变量模板并按需填写本地配置：

```bash
cp .env.example .env
```

### 2. 数据库配置

项目默认使用 `SQLite` 作为本地测试关系型数据库，运行数据不会纳入版本控制。
如果需要切换至真实的 MySQL 服务器，请修改项目根目录的 `.env`：

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

启动完成后可访问：

- `http://127.0.0.1:8000/`：自动进入前端原型；
- `http://127.0.0.1:8000/prototype/`：对话咨询首页；
- `http://127.0.0.1:8000/prototype/onboarding.html`：首次信息确认与培养方案匹配；
- `http://127.0.0.1:8000/prototype/history.html`：历史课表上传与确认；
- `http://127.0.0.1:8000/docs`：FastAPI 交互式接口文档。

前端由 FastAPI 同源挂载，不需要单独安装 Node.js 依赖或执行构建命令。

## 前端原型与接口状态

### 当前可演示状态

当前版本已经可以作为第一阶段 Demo 使用：一键启动后，学生可以确认后端学生档案、上传历史课表、确认培养方案、输入自然语言选课要求、查看筛选结果，并进入读取真实课程快照的课程详情页。课程反馈和学生评价模块仍由能力开关关闭。

本地演示入口：

```text
双击 start_demo.bat
→ http://127.0.0.1:8000/prototype/
```

演示数据库为项目目录下的 `demo_course_db.sqlite`，由 `app/scripts/seed_demo.py` 幂等初始化；该数据库和运行时缓存不会提交到 Git。

### 标准化选课规划第一阶段

项目已新增可独立启停的第一阶段选课规划模块，覆盖：培养方案版本与规则导入、当前学期课程快照、历史课表上传与确认、自然语言约束解析、已修课程排除和确定性课程筛选。课程反馈、学生评价 RAG 和课表冲突默认关闭。

标准接口与接入约定见 [`docs/第一阶段标准接口契约.md`](docs/第一阶段标准接口契约.md)。H5 可通过 `GET /api/v1/capabilities` 获取当前模块能力，按配置决定展示入口。

### 已连接接口

对话页会先通过 `GET /api/v1/planning/context` 获取当前活动课程快照与培养方案。选课推荐和历史课程状态纠正使用 `POST /api/v1/planning/sessions`，经学生确认后分别调用规划执行或历史状态确认接口；课程事实等普通问答仍调用现有 `POST /api/v1/chat` SSE 接口。

推荐流程：

```text
输入自然语言需求
→ 创建规划会话
→ 展示并确认结构化条件
→ 确定性筛选
→ 展示真实推荐卡片与快照依据
```

普通问答流式事件：

| 当前事件 | 前端行为 |
|---|---|
| `status` | 更新“正在识别问题”“正在检索资料”等状态文案 |
| `answer` | 逐段追加助手回答 |
| `meta` | 完成本轮响应并保留会话标识 |

当前接口请求结构：

```json
{
  "query": "008301100001 是什么课？",
  "session_id": "由前端生成并在本地保存的会话标识"
}
```

### 学生端数据边界

学生资料通过 `GET/PUT /api/v1/student/profile` 持久化到后端，浏览器只保留当前演示身份指针；历史课表通过 `/api/v1/academic-history` 上传、确认和查询；推荐结果中的 `offering_id` 通过 `GET /api/v1/catalog/offerings/{offering_id}` 读取真实课程详情。课程评价、经验投稿和学生评价 RAG 属于第二阶段，能力开关默认关闭，H5 不展示反馈入口。

尚未实现的是正式公众号登录 Ticket 换取后端身份、长期偏好管理、课表时间冲突和第二阶段反馈审核，而不是第一阶段 Demo 的主链路。

### 部署说明

`start_demo.ps1` 面向本地开发和演示，依赖本机安装 `uv`。正式接入微信小程序时，建议使用 HTTPS 域名和云端部署：FastAPI 以 Docker 或云平台服务运行，数据库使用托管 MySQL，课表文件使用对象存储，并通过服务端登录 Ticket 管理 `tenant_id/user_id`。个人电脑不作为正式生产服务器。

### 前端页面

| 页面 | 文件 | 主要能力 |
|---|---|---|
| 对话咨询 | `frontend/index.html` | 快捷问题、需求确认、流式回答、课程卡和来源详情 |
| 信息确认 | `frontend/onboarding.html` | 年级/学院/专业与后端培养方案确认 |
| 历史课表 | `frontend/history.html` | 文件上传、解析预览、确认和已修记录 |
| 课程详情 | `frontend/course.html` | 活动课程快照、培养方案关系和已修状态 |
| 经验投稿 | `frontend/feedback.html` | 第二阶段模块，默认由能力开关隐藏 |
| 我的 | `frontend/profile.html` | 后端学生档案、培养方案和历史课表摘要 |

原型支持桌面端和小程序常见窄屏宽度；来源等级、风险与审核状态同时使用文字和颜色表达。

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

前端原型已完成以下浏览器验证：

- 桌面端及 `375px` 窄屏页面检查；
- 首次信息确认与培养方案匹配；
- 复杂推荐的约束/偏好确认和课程卡展示；
- 课程详情、依据来源和课程数据切换；
- 反馈填写、预览确认、真实性声明和审核中结果；
- 页面无横向溢出，浏览器控制台无 JavaScript 错误。

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
