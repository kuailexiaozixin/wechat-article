---
name: search
description: 按关键词搜索微信公众号文章，返回标题、公众号名、发布时间与真实 mp.weixin.qq.com 链接：走搜狗 weixin.sogou.com 的 type=2 结果页，纯标准库实现，跳转链接三形态还原（302 Location / meta refresh / url 片段拼接），命中反爬立即停手不重试。当用户要求"搜索/查找/定位某篇公众号文章""找写过 xx 的公众号文章"时使用。按公众号名检索（type=1）实测返回空结果容器，本技能未封装；拿到链接后取正文走 read/。
---

# 微信公众号文章搜索（搜狗通道）

微信官方没有开放「搜索公众号文章」的接口，本技能走搜狗微信搜索（`weixin.sogou.com`）这一公开网页入口。

## 一、命令

```bash
python search/scripts/search_wechat.py "<关键词>"                      # 列表（默认前 10 条）
python search/scripts/search_wechat.py "<关键词>" -n 20 --pages 2       # 取 20 条，翻 2 页
python search/scripts/search_wechat.py "<关键词>" -r                    # 同时把跳转链接还原成真实文章链接
python search/scripts/search_wechat.py "<关键词>" --format json -o res.json
python search/scripts/search_wechat.py "<关键词>" --format md           # Markdown 输出
python search/scripts/search_wechat.py "<关键词>" --fixture page.html   # 离线解析本地存下的页面（不联网）
```

输出字段：`title`、`account`（公众号名）、`summary`、`timestamp`（unix 秒）、`published`（`YYYY-MM-DD`）、`link`（搜狗跳转链接）、`resolved`（`-r` 时的真实链接）、`resolve_via`（`302`/`meta-refresh`/`url-concat`）、`resolve_error`。

退出码：0 = 拿到至少一条结果；1 = 无结果或被拦截（stderr 的 NOTE 给出当页 URL 与判定依据，`--format json` 时同样打印）。

## 二、参数口径（本机实测，2026-10）

| 项 | 实测结论 |
|---|---|
| 搜文章 | `https://weixin.sogou.com/weixin?type=2&query=<关键词>&page=<N>`，`type=2` 无登录即可用 |
| 每页条数 | 固定 10 条 |
| 翻页上限 | `page=11` 起返回空结果容器，即单关键词最多约 100 条；`--pages` 大于 10 无意义，脚本直接不发该请求 |
| 时间筛选 | `tsn`/`ft`/`et` 三个时间参数实测 302 回首页，不可用；按时间过滤只能取回后按 `timestamp` 自行筛 |
| 搜公众号 | `type=1` 实测返回空的结果容器，拿不到账号列表；需要某公众号的文章时用「公众号名 + 主题词」走 `type=2` |
| 编码 | 搜索页为 UTF-8；`/link` 跳转壳页为 GBK——两处解码口径不同，脚本按响应头优先、再退 UTF-8/GBK |
| 结果节点 | 标题在 `h3 > a`（内含 `<em>` 高亮标记，取值后去标签）；公众号名在 `span.all-time-y2`；时间由页内 `document.write(timeConvert('<unix>'))` 给出，直接抽该数字 |
| 链接形态 | `/link?url=...&type=2&query=...&token=...`，`token` 与查询绑定，不能自造 |

## 三、跳转还原的三种形态

`/link` 返回的是一个 HTML 壳，真实链接可能出现在三处，脚本按顺序尝试：

1. **302 Location**——直接跟随即可。
2. **`<meta http-equiv="refresh" content="0;URL='...'">`**。
3. **JS 片段拼接**：壳页里是 `url += '...'` 分段字符串，逐段拼接后 `window.location.replace(url)`。这是最常见的一种，纯跟随重定向会拿到空页。

还原得到的真实链接形如 `mp.weixin.qq.com/s?src=11&timestamp=...&ver=...&signature=...&new=1`，**其中 `timestamp`/`signature` 带时效**：这是当次会话的跳转票据，隔一段时间或换 IP 后可能失效。要长期留存，用还原后的链接立刻走 `read/` 取正文，或记录文章标题+公众号名+发布时间，而不是保存这条 URL。

## 四、反爬与限流

| 现象 | 判定 | 脚本动作 |
|---|---|---|
| 页面/落地 URL 命中 `antispider`、`wappoc_appmsgcaptcha`、"环境异常"、"验证码拦截" | 拦截 | 立即停止，不重试；`resolve` 阶段命中即中断还原并保留已拿到的列表结果 |
| 最终 URL 回到 `weixin.sogou.com/` 首页 | 参数不被接受或被引导 | 记为失败，提示检查参数（如误用 `tsn`） |
| 结果容器存在但 0 条 | 无收录或关键词过窄 | 明确输出「本页 0 条」，不当作崩溃 |
| 找不到 `ul.news-list` 容器 | 页面结构变更 | 报「结构已变或被拦截」；把当页存成文件后用 `--fixture <.html>` 离线复现解析器行为 |
| 连续请求 `/link` | 实测会 302 到 `antispider` 页 | 还原只在 `-r` 时做、且只还原真正交付的 `-n` 条；每条之间 `--sleep`（默认 1.5s） |

限流纪律：**同一 URL 最多 3 次请求**（`RETRIES=3`，UA 轮换 + 退避 1.5s/3s/4.5s），超过即放弃并报告，不换 IP、不并发、不绕过验证码。搜索前置一次首页请求用于拿 cookie（`SNUID` 等），空 cookie 直查更容易被判机器。

**拦截页的形态（外部公开页面观察，非本技能实测）**：`weixin.sogou.com/antispider/` 给出的是「按顺序点击若干汉字」这类点选式验证，不是文本验证码输入框——脚本层没有可自动化的填写动作。命中它时唯一正确处置是**停手**：把已拿到的列表结果交付，需要继续时由用户在浏览器里人工完成一次验证（验证通过后同一 cookie 通常可恢复正常请求）。搜狗帮助中心没有公开过微信搜索的参数口径与反爬阈值，本技能第二、四节的每一条参数与判定都来自对本机返回页的实际观察，改版后须重新实测。

## 五、与读取的配合

搜索给的是「哪篇文章」，正文交给 `read/`：`python read/scripts/read_wechat.py "<resolved_url>"`。搜狗收录有时效延迟，刚发布的文章搜不到属正常，用户给已知链接时直接走 `read/`，不要绕搜索。

## 六、脆弱性（用前即时验证）

本能力完全依赖搜狗微信搜索这一公开网页：它随时可能改版、加验证码、改参数语义或下线。判定异常时按此顺序处理：先 `--fixture` 用存下的页面确认解析器没坏，再确认参数口径是否变化（第二节表格逐条可复验），最后才怀疑关键词。**同一请求最多三试，不复跑、不并发、不破解**。

`tests/test_search_parser.py` 用本仓库 `tests/fixtures/sogou_*.html`（真实页面切片）离线验解析与还原三形态；改选择器或参数时先跑它。

内容仅供合规阅读与研究，遵守原文版权与搜狗服务条款。
