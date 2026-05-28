# GitHub 个人访问令牌 (PAT) 配置指南

## 问题说明

当前系统无法推送代码到 GitHub 仓库，错误信息表明：
```
Permission Denied: Resource not accessible by personal access token
```
这通常是因为 GitHub 个人访问令牌 (PAT) 缺少必要的权限。

## 解决方案：创建具有正确权限的 GitHub PAT

### 1. 生成新的 Personal Access Token

1. **访问 GitHub 令牌生成页面**
   - 登录 GitHub 后，访问: [https://github.com/settings/tokens/new](https://github.com/settings/tokens/new)

2. **填写令牌信息**
   - **Note**: 输入 `RAG-System-Deploy` (便于识别)
   - **Expiration**: 选择 **No expiration** (或至少 30 天)
   - **Select scopes**:
     - ✅ **repo** (包括 `public_repo`)
     - ✅ **workflow**
     - ✅ **admin:org** (如果需要管理组织仓库)
     
   ![GitHub PAT Scopes](https://docs.github.com/assets/images/help/settings/token-scopes.png)

3. **生成令牌**
   - 点击 **Generate token** 按钮
   - **重要！** 立即将生成的令牌复制保存（GitHub 不会再次显示）
   - 示例令牌格式: `ghp_abcdef1234567890...`

### 2. 配置环境变量

#### Windows 系统配置

1. 打开命令提示符 (CMD) 或 PowerShell
2. 设置环境变量:
   ```powershell
   # 临时生效（当前终端）
   $env:GITHUB_TOKEN="ghp_abcdef1234567890..."

   # 永久生效
   [System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_abcdef1234567890...", "Machine")
   ```

3. **重启终端** 使环境变量生效

#### 项目配置 (推荐)

1. 在项目根目录创建 `.env` 文件:
   ```env
   GITHUB_TOKEN=ghp_abcdef1234567890...
   ```
2. 确保 `.env` 已添加到 `.gitignore` (避免提交到仓库)

### 3. 验证令牌权限

1. 在终端运行以下命令测试权限:
   ```powershell
   curl -H "Authorization: token $env:GITHUB_TOKEN" https://api.github.com/user
   ```
2. 如果返回用户信息，说明令牌有效

## 注意事项

- 🔐 **绝对不要提交令牌到代码仓库**，确保 `.env` 和 `GITHUB_TOKEN` 不会被推送到 GitHub
- 📌 建议为不同用途创建不同令牌，避免权限过大
- 🔁 如果令牌泄露，立即在 GitHub 重新生成新令牌

## 后续操作

完成配置后，请重新尝试推送操作。如果仍遇到问题，可通过以下命令检查当前令牌权限:

```powershell
$token = $env:GITHUB_TOKEN
$headers = @{"Authorization" = "token $token"}
Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers
```