# GitHub 项目推送指南

## 问题诊断

您遇到了 `Repository not found` 错误，原因可能是：

- **仓库名称包含特殊字符**：您的仓库名为 `-DEMO`（以连字符开头），GitHub 虽然支持但部分工具链存在兼容性问题
- **仓库权限问题**：仓库可能不存在或您没有推送权限
- **URL 格式错误**：推送地址格式不正确

## 解决方案

### ✅ 方法一：使用正确仓库地址（推荐）

```powershell
# 1. 重置远程仓库地址
git remote set-url origin https://github.com/ZIJIE0423/-DEMO.git

# 2. 推送至 main 分支
git push -u origin main
```

> **关键说明**：
> - 仓库名称 `-DEMO` 以连字符开头时，URL 必须完整包含连字符：`-DEMO.git`
> - 正确的推送 URL 应为：`https://github.com/ZIJIE0423/-DEMO.git`

### 🔧 方法二：重命名仓库（永久解决）

1. 在 GitHub 网页端操作：
   - 访问 https://github.com/ZIJIE0423/-DEMO/settings
   - 将 **Repository name** 改为 `RAG-System`（移除开头连字符）
   - 保存更改

2. 本地同步新仓库地址：
   ```powershell
   git remote set-url origin https://github.com/ZIJIE0423/RAG-System.git
   git push -u origin main
   ```

## 验证成功

成功推送后，您将看到类似输出：
```
Enumerating objects: 60, done.
Counting objects: 100% (60/60), done.
Delta compression using up to 4 threads
Compressing objects: 100% (59/59), done.
Writing objects: 100% (60/60), 25.50 KiB | 5.10 MiB/s, done.
Total 60 (delta 0), reused 0 (delta 0), pack-reused 0
To https://github.com/ZIJIE0423/RAG-System.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `Permission Denied` | 确认 GitHub Token 有 `repo` 权限 | 
| `Authentication failed` | 检查 `.gitconfig` 是否包含有效 token |
| `Branch 'main' not found` | 使用 `git switch -c main` 创建分支 |

## 注意事项

- 🔐 **敏感信息保护**：`.env` 和 `GITHUB_TOKEN` 已被 `.gitignore` 排除，不会提交到仓库
- 📌 推送前建议运行 `git status` 确认文件状态
- 💡 仓库名以特殊字符开头时，建议在 GitHub 网页端操作更可靠