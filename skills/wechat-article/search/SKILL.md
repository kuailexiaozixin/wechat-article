---
name: search
description: 按关键词搜索微信公众号文章，返回标题、公众号名、发布时间与真实 mp.weixin.qq.com 链接，可按发布日期用 --after/--before 过滤、按公众号名做后置筛选 --account：走搜狗 weixin.sogou.com 的 type=2 结果页，纯标准库实现，跳转链接三形态还原（302 Location / meta refresh / url 片段拼接），命中反爬立即停手不重试。当用户要求"搜索/查找/定位某篇公众号文章""找写过 xx 的公众号文章""找某段时间的公众号文章""找某公众号发的文章"时使用。按公众号名检索（type=1）实测返回空结果容器，本技能未封装，改用 --account 后置筛；拿到链接后取正文走 read/。
---

# 微信公众号文章搜索（搜狗通道）

微信官方没有开放「搜索公众号文章」的接口，本技能走搜狗微信搜索（`weixin.sogou.com`）这一公开网页入口。

这一份只给命令、字段、判定与处置；**每个参数口径出自哪个样本、每一格「未判定」缺什么证据**记在 `search/references/sogou-probe.md`，补测时按那一份的清单走，不要在正文里加样本细节。

## 一、命令

```bash
python search/scripts/search_wechat.py "<关键词>"                      # 列表（默认前 10 条）
python search/scripts/search_wechat.py "<关键词>" -n 20 --pages 2       # 取 20 条，翻 2 页
python search/scripts/search_wechat.py "<关键词>" -r                    # 同时把跳转链接还原成真实文章链接
python search/scripts/search_wechat.py "<关键词>" --after 2026-09-01    # 只要该日（含）之后发布的
python search/scripts/search_wechat.py "<关键词>" --after 2026-09-01 --before 2026-09-30 -n 30
python search/scripts/search_wechat.py "<关键词>" --format json -o res.json
python search/scripts/search_wechat.py "<关键词>" --format md           # Markdown 输出
python search/scripts/search_wechat.py "<关键词>" --account <公众号名>   # 后置筛：只要该号发的条目
python search/scripts/search_wechat.py "<关键词>" --dump pages/         # 每次抓到的结果页（含被拦页）落盘
python search/scripts/search_wechat.py "<关键词>" --fixture page.html   # 离线解析本地存下的页面（不联网）
```

输出字段：`title`、`account`（公众号名）、`summary`、`timestamp`（unix 秒）、`published`（`YYYY-MM-DD`）、`link`（搜狗跳转链接）、`resolved`（`-r` 时的真实链接）、`resolve_via`（`302`/`meta-refresh`/`url-concat`）、`resolved_at`（本机完成还原的时刻，unix 秒）、`resolve_error`、`resolve_skipped`（还原期熔断后未发起请求的条目）、`link_error`。`--format json` 的顶层除 `keyword`/`count`/`items` 外还带 `notes` 数组，内容与 stderr 上的 NOTE 逐条一致。

`link` 只可能是 `https://weixin.sogou.com`（无端口）——结果页的 `href` 是不可信输入，`href="//evil.example/x"` 这类协议相对写法会被拼成合法外域链接。`safe_link` 把这种链接置空并在条目上落 `link_error`，标题、日期、摘要照常交付，`-r` 不为它发任何请求。**这一条是给调用方的硬约束**：带 `link_error` 的条目不要转手交给 `read/` 或浏览器，它已经没有可信去处了。

`resolved` 同理，但走的是另一道门：`safe_mp_link` 只放行 `https://mp.weixin.qq.com`（无端口），三种还原形态（302 Location / meta refresh / `url += '…'` 片段拼接）的产物一律过它。以前判的是「字符串里含不含 `mp.weixin.qq.com`」，那是子串判定，`https://mp.weixin.qq.com.evil.example/s?x=1` 也算含；页内 meta refresh 与 JS 拼出来的目标更是由页面对象说了算。现在这类结果不落 `resolved`，原因写进 `resolve_error`，条目继续交付搜狗跳转链接兜底（`-r` 的失败不该让整条结果作废）。两条门都要求 URL 合法：主机位置出现不配对的 `[` 时 `urlsplit` 会抛 `ValueError('Invalid IPv6 URL')`，这类页面内容按不可信处理、只丢那一条链接，不能让它把整次搜索弄崩。打印出来的原因里控制字符会被剥掉——那串文本来自页面，原样打到终端等于给了一次伪造输出的机会。

退出码：0 = 拿到至少一条结果；1 = 失败；2 = 日期参数不合法、区间为空或 `--account` 给了空白名。退 1 的三种形态靠 NOTE 文案区分，且互斥：**「被拦截」**（命中反爬标记、被 302 回首页，或 HTTP 状态码 403/429/503——那三个码是服务端明确说「现在不给」，处置和限流一样要停手冷却）、**「传输层异常」**（超时/DNS/连接重置，以及 500 这类服务端未表态的失败，立即停止翻页，既不说成拦截也不说成没结果）、**「本页 0 条」**（搜狗确实没有更多结果）。分家的理由：限流之后继续请求只会延长风控，网络抖动才是马上重试有意义的那一种，两者混在一句文案里调用方就没法选。两类拦截 NOTE（搜索页被拦、还原期熔断）都带本机时刻，处置建议说的「隔时再跑」要有起点；冷却时长本身未实测，所以只记时刻不承诺几点恢复。三种文案都不改变 stdout 的内容形状：NOTE 照旧打到 stderr，`--format json` 时同一批文本也进 json 顶层的 `notes` 数组——只用 `-o res.json` 落盘的调用方同样能看到判定，不会拿到「结果 + 无说明」。

响应体读满 4MB（`MAX_BODY_BYTES`）即停并打截断 NOTE。实测正常结果页在 3.1 万字符量级（本机两张 page=1 切片逐字节相同，均 31243 字符），到上限说明拿到的根本不是结果页；25 秒超时管不住「慢但不断」的响应，所以按字节收口。截断后仍照常解析已读到的部分，因为哨兵会比对节点数量、半页数据骗不过去。

`--after/--before` 是**取回之后**按结果页自带的 `timeConvert('<unix>')` 时间戳筛，闭区间，`--before` 含当天全天；没有时间戳的条目一律丢弃并计数（无法证明它在窗内）。带时间过滤而未显式给 `--pages` 时默认翻满 10 页——同页日期不是严格倒序（见第二节），只翻一页就报「窗口内没结果」等于把覆盖不足当成搜狗没收录。

## 二、参数口径（本机实测，2026-10-17）

| 项 | 实测结论 |
|---|---|
| 搜文章 | `https://weixin.sogou.com/weixin?type=2&query=<关键词>&page=<N>`，`type=2` 无登录即可用；`s_from`/`_sug_` 可省（缺这两个参数实测同样返回 10 条） |
| 每页条数 | 固定 10 条。`num=20`/`n=20` 是否放大每页条数**未判定**（该轮请求撞反爬，见下方判定纪律） |
| 翻页上限 | `page=10` 仍返回结果，`page=11`/`12` 返回无结果容器且两次页面长度逐字节相同（10488）——即单关键词最多约 100 条；`--pages` 大于 10 无意义，脚本直接不发该请求 |
| 服务端时间筛选 | 不可用：`tsn=1`/`2`/`3`/`4` 四次请求全部 302 回首页；`ft`/`et` 与 `ss_st`/`ss_et` **未判定**。脚本不发任何时间参数 |
| 客户端时间筛选 | `--after/--before` 按结果页自带时间戳筛，口径见第一节 |
| 结果顺序 | 同一页内 `timeConvert` 时间戳**不是严格倒序**（两组样本与由此定下的「不做本页变旧就停」的早停规则，论证在 `search/references/sogou-probe.md` 第 2、3 节）。所以带时间过滤而未显式给 `--pages` 时默认翻满 10 页，不按页内最小时间戳提前收手 |
| 跨页重复 | **未判定**：没有多页样本，重复率没量过（缺样本的经过与复采方法见 `search/references/sogou-probe.md` 第 3 节）。脚本因此不做到页去重：`raw.extend(got)` 原样拼接，`-n` 数的是交付条数 |
| 搜公众号 | `type=1` 两轮实测均返回空的结果容器（本轮页面长度 10196），拿不到账号列表；需要某公众号的文章时用「公众号名 + 主题词」走 `type=2`，再加 `--account <公众号名>` 后置筛（不区分大小写的子串匹配，账号名常带「工作室/小站」这类后缀，筛出 0 条时先看 NOTE 列出的「本次读到过的公众号」）。它是后置过滤，少翻页会漏：翻页的停止条件按筛后条数判，凑不够 `-n` 就继续翻 |
| 检索语法 | `OR`、`-排除词`、`intitle:` 都能返回结果页；`"精确短语"`、`site:` **未判定**。「返回结果页」不等于「语法生效」——判生效要比对带与不带该语法两次请求的标题集合，这组对照没做完（缺什么证据见 `search/references/sogou-probe.md` 第 7 节） |
| 编码 | 搜索页为 UTF-8；`/link` 跳转壳页为 GBK——两处解码口径不同，脚本按响应头优先、再退 UTF-8/GBK |
| 结果节点 | 标题在 `h3 > a`（内含 `<em>` 高亮标记，取值后去标签）；公众号名在 `span.all-time-y2`；时间由页内 `document.write(timeConvert('<unix>'))` 给出，直接抽该数字。**每条结果四类节点各一个**：真实切片 box / `h3>a` / `timeConvert` / `span.all-time-y2` 均为 10，而 `/link?url=` 链接有 20 条（标题之外还有第二跳），所以链接数不参与结构判定 |
| 链接形态 | `/link?url=...&type=2&query=...&token=...`，`token` 与查询绑定，不能自造 |

**判定纪律（这张表每一格都得按它读）**：单发请求拿到一次 BLOCK 不能判成「该参数不可用」，只能判「未判定」。要补上任何一格，需要同一 URL 三试内稳定复现同一形态，且与不带该参数的对照请求能区分开。表内标 **未判定** 的行是按这条纪律留空的——宁可缺一格，不把抽样抖动写成结论。那一轮 26 个用例里 10 个落到 `antispider` 的经过、七项未判定各自缺什么证据，写在 `search/references/sogou-probe.md` 第 1、7 节。

## 三、跳转还原的三种形态

`/link` 返回的是一个 HTML 壳，真实链接可能出现在三处，脚本按顺序尝试：

1. **302 Location**——直接跟随即可。
2. **`<meta http-equiv="refresh" content="0;URL='...'">`**。
3. **JS 片段拼接**：壳页里是 `url += '...'` 分段字符串，逐段拼接后 `window.location.replace(url)`。这是最常见的一种，纯跟随重定向会拿到空页。

还原得到的真实链接形如 `mp.weixin.qq.com/s?src=11&timestamp=...&ver=...&signature=...&new=1`，**其中 `timestamp`/`signature` 是当次会话的跳转票据**：隔一段时间或换 IP 后即失效，失效的票据不能刷新也不能重放，技能没有重放能力。脚本在还原成功时写下 `resolved_at`（本机时刻，unix 秒；text 输出里是「还原时刻」一行），用法只有两条：`resolved_at` 距今不久，立刻把 `resolved` 交给 `read/` 取正文；已隔了一段时间或换了网络，作废这条 URL、重新 `-r` 取一张新票据。要长期留存，记「标题 + 公众号名 + 发布时间」，不存这条 URL。票据的确切存活时长**未实测**（须跨会话长时间复采同一张票据才能量出），上面两条处置不依赖具体时长。

## 四、反爬与限流

| 现象 | 判定 | 脚本动作 |
|---|---|---|
| 页面/落地 URL 命中 `antispider`、`wappoc_appmsgcaptcha`、"环境异常"、"验证码拦截"、`anti.min.css` | 拦截 | 立即停止，不重试；`resolve` 阶段命中即中断还原并保留已拿到的列表结果 |
| HTTP 状态码 403/429/503（`fetch` 把码带在 `http_status` 里） | 服务端明确拒绝/限流，按拦截处理 | NOTE 写「被拦截：服务端按状态码拒绝（HTTP 429）」并停止翻页；`-r` 期间命中同一批处置，**立即熔断后续还原**，不逐条撞 `/link` |
| `fetch` 三次退避后仍拿不到响应（超时/DNS/连接重置），或 500 这类服务端未表态的状态码 | 传输层异常，**不是**搜狗的判定 | NOTE 写「传输层异常」并立即停止翻页；不把这种情况写成「被拦」或「本页 0 条」 |
| 最终 URL 回到 `weixin.sogou.com/` 首页 | 参数不被接受或被引导 | 记为失败，提示检查参数（如误用 `tsn`） |
| 结果容器存在但 0 条 | 无收录或关键词过窄 | 明确输出「本页 0 条」，不当作崩溃 |
| 找不到 `ul.news-list` 容器 | 页面结构变更 | 报「结构已变或被拦截」；带 `--dump DIR` 时该页已落盘（被拦页文件名带 `blocked_page`），拿它用 `--fixture <.html>` 离线复现解析器行为 |
| 结果容器在、条目也在，但四类节点数量与条目数不等 | 页面改版（第一步通常是加层或换标签） | 打印「结构漂移（box=… 标题=… 时间戳=… 公众号=… 已解析=…）」NOTE，结果照常交付；见到它就停下来复验解析器，不要把缺字段当成数据缺失 |
| 连续请求 `/link` | 实测会 302 到 `antispider` 页 | 还原只在 `-r` 时做、且只还原真正交付的 `-n` 条；每条之间 `--sleep`（默认 1.5s） |
| 条目 `href` 指向 `weixin.sogou.com` 之外 | 结果页被注入，或该条不是文章链接 | `link` 置空 + `link_error`，标题/日期/摘要照常交付，`-r` 不为它发请求；条目数不变，所以不会误报结构漂移 |
| `/link` 还原目标指向 `mp.weixin.qq.com` 之外（含 `mp.weixin.qq.com.evil.example` 这种子串伪装） | 壳页被改写，或还原形态变更 | 不落 `resolved`，原因写进 `resolve_error`，条目继续交付搜狗跳转链接兜底；这不算拦截，后续条目照常尝试 |
| 页面给的 URL 非法（主机位置 `[` 不配对，`urlsplit` 抛 `ValueError`） | 结果页内容不可信 | 该条链接按「域外」处理，只丢这一条，不让它把整次搜索弄崩；打印原因时剥控制字符 |
| 还原期熔断（`is_block_why` 命中 `BLOCK_WHY_KEYS`）后剩下的条目 | 没发过请求，既不是成功也不是失败 | 落 `resolve_skipped`，`resolved`/`resolve_error` 都不写；text/md 各多一行「还原未尝试」，json 里该字段可查。处置与熔断 NOTE 同一条：隔时再 `-r`，或人工过一次验证 |
| 单次响应读满 `MAX_BODY_BYTES`（4MB） | 拿到的不是预期页面（正常结果页 3.1 万字符量级） | 停止读取、照常解析并打「截断」NOTE；25 秒超时管不住慢而不断的响应，按字节收口 |
| 搜索页被拦 / 还原期熔断 | 服务端在限流或要验证 | NOTE 末尾带本机时刻（`_stamp()`），作为「隔时再跑」的起点；冷却时长未实测，不承诺几点恢复 |
| 需要留存现场 | 改版或风控过后必须拿回同一份页面比对 | `--dump DIR`：每次抓到的结果页写 `DIR/page<N>_<epoch>.html`，被拦页文件名带 `blocked_page`；`--fixture` 只能读，没有 `--dump` 就得重跑请求，而重跑拿到的已是另一个页面 |

标记集为什么含 `anti.min.css` 而不会把好页面误判成拦截，依据（仓库样本与本机真实页各命中几次）在 `search/references/sogou-probe.md` 第 5 节，判据在 `tests/test_search_parser.py` 第 12 节两个方向都断言。

限流纪律：**同一 URL 最多 3 次请求**（`RETRIES=3`，UA 轮换 + 退避 1.5s/3s/4.5s），超过即放弃并报告，不换 IP、不并发、不绕过验证码。搜索前置一次 `weixin.sogou.com` 首页请求只为拿 `ABTEST`/`SUID` 等种子 cookie，**这条不是已证的抗拦截手段**（A/B 五个样本判不出预热有没有用，保留它的理由与「预热入口不换」的依据在 `search/references/sogou-probe.md` 第 4 节）。

**命中拦截的处置**：脚本层没有可自动完成的填写动作，所以唯一正确动作是**停手**——把已拿到的列表结果照常交付，需要继续时由用户在浏览器里人工完成一次验证再跑。拦截页的实际形态（`antispider.min.js` 驱动、按顺序点选汉字而非文本验证码框）记在 `search/references/sogou-probe.md` 第 5 节。本技能第二、四节每一条参数与判定都注明它来自对本机返回页的实际观察，改版后须重新实测。

## 五、与读取的配合

搜索给的是「哪篇文章」，正文交给 `read/`：`python read/scripts/read_wechat.py "<resolved_url>"`。搜狗收录有时效延迟，刚发布的文章搜不到属正常，用户给已知链接时直接走 `read/`，不要绕搜索。带 `link_error` 的条目没有可信链接可交给 `read/`，只能按标题+公众号+日期口头向用户确认来源。交给 `read/` 的只能是 `resolved` 字段：`read/` 要的是真实文章链接，搜狗跳转链接在它那一侧没有文档保证；条目带 `resolve_error`（包括还原目标主机不符被丢弃的情况）时保留的只是跳转链接，处置是隔时再跑一次 `-r`，或按第四节先人工过一次验证，不要拿跳转链接硬喂 `read/`；带 `resolve_skipped` 的条目是还原期熔断后没发过请求的那几条，处置相同，但不必为它重新解释失败原因——它没有原因，只有熔断时刻（在同一批 NOTE 里）。

## 六、脆弱性（用前即时验证）

本能力完全依赖搜狗微信搜索这一公开网页：它随时可能改版、加验证码、改参数语义或下线。排障顺序：第一步先看脚本自己打出的哨兵——每次解析都会核对 box/`h3>a`/`timeConvert`/`span.all-time-y2` 四类节点数量（第二节「结果节点」行），一旦输出里出现「结构漂移」或「字段命中率下降」NOTE，就是选择器与页面对不上了，先带 `--dump DIR` 重跑一次把当页落盘、用 `--fixture` 离线复现（哨兵在离线路径同样触发，不需要联网），再确认参数口径是否变化（第二节表格逐条可复验），最后才怀疑关键词。**同一请求最多三试，不复跑、不并发、不破解**。

`tests/test_search_parser.py` 用本仓库 `tests/fixtures/sogou_*.html`（真实页面切片）离线验解析与还原三形态；改选择器或参数时先跑它。

内容仅供合规阅读与研究，遵守原文版权与搜狗服务条款。
