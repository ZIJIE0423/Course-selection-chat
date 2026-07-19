# WeOUC 高保真前端原型

## 启动

在项目根目录运行：

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 `http://127.0.0.1:8000/prototype/`。项目根路径也会自动跳转到该入口。

## 页面

- `onboarding.html`：学生信息与培养方案确认
- `index.html`：对话咨询、需求确认、课程方案卡和课表授权提示
- `course.html`：课程详情与来源依据
- `feedback.html`：结构化课程体验、预览确认和提交结果
- `profile.html`：学生信息、长期偏好、课表授权和投稿状态

## 接口状态

- 对话页已连接现有 `POST /api/v1/chat` SSE 接口，并兼容当前的 `status`、`answer`、`meta` 事件。
- 学生信息、培养方案、课表授权、课程详情、投稿和偏好管理目前没有对应学生端 API，原型使用代表性数据与 `localStorage` 演示交互。
- 后端按 PRD 扩展 `requirement_confirmation`、`course_card`、`source_card`、`warning`、`done` 和 `error` 事件后，可在 `assets/js/chat.js` 的事件分发处接入。

原型不会收集教务系统账号、密码或真实个人课表。
