# wechat-article

微信公众号文章全链路 **Agent Skill**（遵循 [Agent Skills 开放标准](https://agentskills.io)）：写作纪律、微信兼容 HTML 排版、素材上传、草稿箱管理、文章读取与搜索。安装后，AI 助手按 `SKILL.md` 的工作流与铁律，完成从写作到推送草稿箱的全链路。

## 子技能（5 个）

| 子技能 | 能力 |
|---|---|
| `write` | 写作纪律（去 AI 味/不虚构）+ 微信兼容 HTML 硬规范（内联样式、禁 `<pre>`/`<table>`、代码块 section+逐行 p、mmbiz 正文图、纯 section 片段）+ `validate_wx_html.py` 确定性校验 + `qa_mobile.py` 390px 真机渲染验收 + `build_blocks.py` 按组件 JSON 产出与主题表逐字一致的正文 + 本地预览 + mermaid 渲染 + 跨篇查重 |
| `draft` | 草稿箱全接口（add/update/get/list/count/delete）+ 参数约束 + 腾讯 WAF 501 自动绕行（delete+add，明确告知 media_id 变化）+ `check_draft.py --source` 回读正文与源文件逐字比对 |
| `materials` | 封面永久素材上传、正文图批量 `uploadimg`（token 复用 + 45009 退避 + 上传前 1MB 逐张预检）、封面生成器 |
| `read` | 公众号文章正文四层渐进式提取（Mobile UA → Desktop UA+Cookie → 完整浏览器头 → CDP）+ 质量门（正文长度阈值与验证墙标记）+ Markdown/frontmatter 输出，脚本 `read_wechat.py` |
| `search` | 搜狗公众号文章搜索（`type=2`）+ 跳转链接三形态还原（302 Location / `<meta refresh>` / `url +=` 拼接）+ 反爬判定与停手规则，脚本 `search_wechat.py` |

## 三道闸（v4.3.0 起落地为代码）

成稿到入库依次过三关，任一不过就不会有网络请求发出：

1. **写作侧**：`check_prose.py` 清零硬禁令 → `validate_wx_html.py` ERROR=0 → `qa_mobile.py` 390px 无横向溢出、无 `display:table*`/grid 伪表格。
2. **推送侧**：`wx_draft_push.py` 内置同一份 validate 判据，ERROR>0 直接 `ERR PUSH_BLOCKED` 退出，先于取 token。一份含 `<table>` 的 HTML 在这一关就会被拦下。
3. **入库侧**：`check_draft.py <media_id> --source <article.html>` 把回读正文与源文件归一化后逐字比对（统一换行、剥 mmbiz 查询参数、去标签间与连续空白），图片数预期由源文件自动得出。**改了源文件没重推，这一步必 FAIL**。

## 测试与评测

```bash
cd skills/wechat-article
python tests/run_all.py          # 8 个判据文件离线跑完，全绿退出码 0
python tests/run_all.py -k qa    # 只跑文件名含 qa 的判据
```

`tests/` 覆盖 16 条 validate ERROR 规则（各配命中 fixture）、theme-default 九组件与 `build_blocks.py` 的逐字一致性（改主题表不改脚本即红）、`qa_mobile.py` 的伪表格反证（`div + display:table` 样张必须先报红）、P0 三道闸、读取质量门、搜索解析与还原、`evals/evals.json` 路由用例的引用核对。全部离线，不联网、不消耗任何接口额度。文中 `write/`、`read/`、`search/`、`scripts/`、`tests/` 等相对路径均以 `skills/wechat-article/` 为根。

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
