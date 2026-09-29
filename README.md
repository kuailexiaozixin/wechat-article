# wechat-article

微信公众号文章全链路 **Agent Skill**（遵循 [Agent Skills 开放标准](https://agentskills.io)）：写作纪律、微信兼容 HTML 排版、素材上传、草稿箱管理、文章读取与搜索。安装后，AI 助手按 `SKILL.md` 的工作流与铁律，完成从写作到推送草稿箱的全链路。

## 子技能（5 个）

| 子技能 | 能力 |
|---|---|
| `write` | 写作纪律（去 AI 味/不虚构）+ 微信兼容 HTML 硬规范（内联样式、禁 `<pre>`/`<table>`、代码块 section+逐行 p、mmbiz 正文图、纯 section 片段）+ `validate_wx_html.py` 确定性校验 + 通用排版主题 + 本地预览 + mermaid 渲染 + 跨篇查重 |
| `draft` | 草稿箱全接口（add/update/get/list/count/delete）+ 参数约束 + `check_draft.py` 回读核验 + 发布前后台手动设置清单 |
| `materials` | 封面永久素材上传、正文图批量 `uploadimg`（token 复用 + 45009 退避）、封面生成器 |
| `read` | 公众号文章正文四层渐进式提取（含验证墙处理） |
| `search` | 搜狗公众号文章/账号搜索 + 302 跳转还原 |

## 安装

```bash
# GitHub CLI（gh >= 2.90）
gh skill install kuailexiaozixin/wechat-article

# 或 Claude Code
/plugin marketplace add kuailexiaozixin/wechat-article

# 或手动：下载 Release 归档，把 skills/wechat-article 放入助手技能目录
```

## 凭据（环境变量）

```
WECHAT_APPID   # 公众号 AppID
WECHAT_SECRET  # 公众号 AppSecret
WECHAT_AUTHOR  # 作者名（可选，缺省省略 author 字段）
```

## 发布说明（重要）

个人主体/未认证公众号的**发布接口族（freepublish/*）实测整体返回 48001 无权限**（含只读查询）。本技能因此不封装发布命令，只提供 `check-perm` 权限探测；发布请在公众号后台「内容管理 → 草稿箱」手动完成，并在发布页手动设置：开赞赏、声明原创、选择合集、创作来源「内容由AI生成」。详见 `skills/wechat-article/SKILL.md`「发布」节。

## 使用示例

```
写一篇公众号文章：主题 xxx，参考素材 xxx
推送到公众号草稿箱
回读核验刚才推送的草稿
```

## License

MIT © 2026 kuailexiaozixin
