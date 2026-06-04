# 云端每日新闻邮件

这个项目把新闻简报任务放到 GitHub Actions 云端执行。电脑和 Codex 不需要开着，只要 GitHub Actions 可用、仓库 Secrets 配置正确，就会在工作日北京时间 08:00 自动发送邮件。

## 功能

- 工作日自动运行：周一到周五，北京时间 08:00。
- 新闻范围：中国政治、国际政治、中国财经、国际财经。
- 新闻来源：Google News RSS 查询结果，邮件中保留来源链接。
- 邮件发送：通过 SMTP 发送到指定邮箱。

## 需要配置的 GitHub Secrets

在 GitHub 仓库中打开 `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`，添加：

| Secret | 示例 | 说明 |
| --- | --- | --- |
| `SMTP_HOST` | `smtp.qq.com` | SMTP 服务器 |
| `SMTP_PORT` | `465` | SMTP SSL 端口 |
| `SMTP_USERNAME` | `your-email@qq.com` | 发件邮箱账号 |
| `SMTP_PASSWORD` | QQ 邮箱授权码 | 不是 QQ 登录密码 |
| `MAIL_TO` | `your-email@qq.com` | 收件人 |
| `MAIL_FROM` | `your-email@qq.com` | 发件人，可与账号相同 |

QQ 邮箱通常需要先开启 SMTP 服务，并使用“授权码”作为 `SMTP_PASSWORD`。

## 手动测试

在 GitHub Actions 页面选择 `Daily News Email`，点击 `Run workflow` 可以手动触发一次。

本地测试可以设置环境变量后运行：

```powershell
python -m pip install -r requirements.txt
python scripts\daily_news_email.py
```

## 调整内容

新闻分类和查询词在 [scripts/daily_news_email.py](scripts/daily_news_email.py) 的 `TOPICS` 中。默认每类最多取 5 条，优先保留最近 24 小时内的新闻。
