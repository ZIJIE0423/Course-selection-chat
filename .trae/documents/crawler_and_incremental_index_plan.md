# 选课系统后端第四阶段：Playwright 数据采集与知识库增量更新实施计划

## 1. 概述

本计划描述第四阶段的最终实施步骤，包括 README 更新和验证测试。第四阶段的大部分核心功能已实现，剩余工作主要是完善文档和验证功能。

## 2. 实施步骤

### 2.1 README 更新

- [ ] 补充采集 URL 配置说明（在快速开始部分添加）
  - 说明在 `.env` 文件中设置 `CRAWL_NOTICE_URLS` 和 `CRAWL_FORUM_URLS`
  - 提供示例：`CRAWL_NOTICE_URLS=https://jwgl.ouc.edu.cn/,https://example.com/notice`
  - 提醒多个 URL 用逗号分隔

- [ ] 添加手动爬虫运行说明
  - 添加命令 `uv run python app/tasks/weekly_crawl.py` 到快速开始部分
  - 说明执行结果的输出内容（采集数、新增数等）

- [ ] 添加待审核内容查看指南
  - 说明访问 `/api/v1/admin/crawled/pending` 接口查看待审核内容
  - 提供 curl 示例和预期响应结构

- [ ] 添加审核流程说明
  - 说明如何使用 `approve`/`reject`/`index` 接口进行审核
  - 提供每个接口的简要说明和使用示例

- [ ] 添加知识库增量更新流程
  - 说明审核通过后如何触发索引更新
  - 提醒只有状态为 `approved` 的文档才会被索引

### 2.2 验证测试

- [ ] 运行 `uv run python app/tasks/weekly_crawl.py` 验证采集流程
  - 确认采集结果进入数据库，状态为 `pending`
  - 检查去重机制是否正常工作

- [ ] 启动服务测试审核接口
  - 确认 `/api/v1/admin/crawled/pending` 返回采集内容
  - 测试 `approve`/`reject` 接口更新状态
  - 测试 `index` 接口触发知识库更新

- [ ] 验证增量索引功能
  - 确认 `indexed` 状态的文档已成功写入 ChromaDB
  - 在向量数据库中验证元数据是否正确

- [ ] 测试"最新公告"路由
  - 使用包含"最新选课通知"的查询测试
  - 验证返回是否包含官方公告信息
  - 测试无结果时的提示语

- [ ] 确认普通问答不触发实时采集
  - 使用普通问题查询，确认无爬虫相关日志
  - 确认响应速度符合要求

## 3. 注意事项

- 项目中缺少 `app/crawler/__init__.py` 和 `app/tasks/__init__.py` 文件
  - 为确保模块导入正常，应创建空的 `__init__.py` 文件
  - 只需创建文件，无需添加任何内容

- 项目依赖已通过 `pyproject.toml` 添加 `apscheduler` 和 `beautifulsoup4`
  - 确认 `uv add apscheduler beautifulsoup4` 已执行

## 4. 验收标准

| 序号 | 验收标准 | 状态 |
|------|----------|------|
| 1 | 能运行 `uv run python app/tasks/weekly_crawl.py` 完成采集 | |
| 2 | 采集内容进入 CrawledDocument 表，状态为 pending | |
| 3 | 管理接口可查看、审核、驳回采集内容 | |
| 4 | 审核通过后可增量写入 ChromaDB | |
| 5 | 用户询问最新选课公告时，系统能从已审核知识库中检索并回答 | |
| 6 | 普通问答不会触发实时 Playwright 采集 | |

## 5. 验证结果记录

在测试完成后，应在此处记录验证结果，包括通过/失败的测试用例和问题说明。