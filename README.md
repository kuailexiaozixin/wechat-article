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

`tests/` 覆盖 16 条 validate ERROR 规则（各配命中 fixture）、theme-default 九组件与 `build_blocks.py` 的逐字一致性（改主题表不改脚本即红）、`qa_mobile.py` 的伪表格反证（`div + display:table` 样张必须先报红）、P0 三道闸、读取质量门、搜索解析与还原、`evals/evals.json` 路由用例的引用核对、以及全树文本里的顶层目录引用与磁盘目录名逐字符比对。全部离线，不联网、不消耗任何接口额度。文中 `write/`、`read/`、`search/`、`scripts/`、`tests/` 等相对路径均以 `skills/wechat-article/` 为根。

汇总行形如「判据文件 8 个：通过 8 · 跳过 0 · 失败 0 项」。**跳过单列、不计入通过**：`qa_mobile` 那一支需要本机有 Playwright 与浏览器，缺依赖时打印 SKIP 并说明原因，不会伪装成通过。GitHub Actions（`.github/workflows/verify.yml`）在 Ubuntu 上跑的正是这同一批判据，Linux 的文件系统大小写敏感，所以那一跑同时也在验本仓库的下述目录名口径。

`read` 的 Markdown 结构断言分两条引擎路径：装了 `beautifulsoup4` 才逐节点映射标题/列表/加粗/引用/代码块/图片，没装则走 `regex-degraded`（只出段落文本，不产结构，详见 `skills/wechat-article/read/SKILL.md` 四、五两节）。CI 用 `bs4: [none, installed]` 矩阵把两条都跑一遍——只在装有 bs4 的机器上验结构，等于从没测过降级分支。

## 目录名与行尾口径

- **子技能目录一律小写**（`write`、`read`、`search`、`draft`、`materials`）。宿主本地安装目录的三个子技能用的是首字母大写目录名（`Write`、`Read`、`Search`），发布树按小写生成，文本里的同名引用一起改写；这条改写由 `tests/test_evals_routes.py` 守着——它在小写树和大写树里都能跑，引用与磁盘名大小写不符即报红。本 README 也在同一判据的核对范围内：它写的都是 `skills/wechat-article/read/SKILL.md` 这种完整式路径，判据剥掉 `skills/wechat-article/` 前缀后按同一口径比对（此前实测就在这里写出过与实际磁盘名不符的引用）。Linux/macOS 克隆后文件系统大小写敏感，靠约定不成立，所以做成判据。
- **行尾只有 LF**，由仓库根 `.gitattributes` 钉住检出行为。
- 映射与同步由仓库外的一个脚本完成（把本地树按上述两条改写后写入 `skills/wechat-article/`）。它不进本仓库：技能内容必须能独立分发，而那个脚本认识的是发布者的本机目录。仓库内留下的是上面这两条口径本身和守它们的判据，两者合起来足够重建发布树。

## 安装

```bash
# GitHub CLI（需带 skill 子命令；本机 gh 2.101.0 实测可用）
gh skill install kuailexiaozixin/wechat-article
# 锁版本
gh skill install kuailexiaozixin/wechat-article wechat-article --pin v4.5.2

# 手动：下载 tag 归档（每个 tag 都有，无需 release 资产）
#   https://github.com/kuailexiaozixin/wechat-article/archive/refs/tags/v4.5.2.zip
# 解压后把其中的 skills/wechat-article 整个目录放进助手的技能目录
```

两条路径落地出来的文件不完全一样，做比对前先按这个口径：

- `gh skill install` 会重写落地件里每个 `SKILL.md` 的 frontmatter：键按字母序重排、`description` 的引号风格改写、`---` 后的空行去掉，并注入四项安装来源标记（`metadata.github-repo` / `github-ref` / `github-path` / `github-tree-sha`）。v4.5.1 实测：52 个文件里 46 个与仓库逐字节相同，6 个 `SKILL.md` 因上述改写而不同；注入的 `github-tree-sha` 与 `git rev-parse v4.5.1:skills/wechat-article` 逐字符相同，说明改写只发生在 frontmatter，正文与脚本没动。
- 下载 tag 归档解压出来的目录与仓库件逐字节相同（仓库根 `.gitattributes` 规定了检出行尾，文本一律 LF）。

所以要拿这个目录做二次分发、打补丁或者与仓库做 diff，走归档路径；只是装进助手使用，两条都一样。

## 凭据（环境变量）

```
WECHAT_APPID   # 公众号 AppID
WECHAT_SECRET  # 公众号 AppSecret
WECHAT_AUTHOR  # 作者名（可选，缺省省略 author 字段）
```

## 发布说明（重要）

个人主体/未认证公众号的**发布接口族（freepublish/*）实测整体返回 48001 无权限**（含只读查询）。本技能因此不封装发布命令，只提供 `check-perm` 权限探测；发布请在公众号后台「内容管理 → 草稿箱」手动完成，并在发布页手动设置：开赞赏、声明原创、选择合集、创作来源「内容由AI生成」。清单与固定话术在 `skills/wechat-article/draft/SKILL.md`「制作→预览工作流」第 4 步，错误码实测范围在 `skills/wechat-article/references/gotchas.md` A3。

## 使用示例

```
写一篇公众号文章：主题 xxx，参考素材 xxx
推送到公众号草稿箱
回读核验刚才推送的草稿
```

## License

MIT © 2026 kuailexiaozixin
