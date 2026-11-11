---
name: read
description: 从已知的 mp.weixin.qq.com 链接提取公众号文章正文与元信息并转 Markdown：四层降级取页（Mobile UA → Desktop UA+Cookie → 完整浏览器头 → 本机 Edge CDP）、验证墙判定、正文完整性质量门；四层全失败时可选 --yuanbao 用标题去元宝搜索换源兜底。当用户要求"读取/提取/解析某篇公众号文章正文""这篇写了什么"时使用。只有关键词没有链接时先走 Search/。
---

# 微信公众号文章读取（Read）

## 零、元宝换源兜底（--yuanbao，可选，默认关）

四层都取不到合格正文、但页面至少给过标题时，可以拿这个标题去元宝搜索（`so.qq.com` 公众号文章频道）找同款，换成能直接读的链接再试一遍。

```bash
python Read/scripts/read_wechat.py "<原链接>" --yuanbao
```

**触发条件（三个同时满足，缺一不做）**：显式传了 `--yuanbao`；四层全部未过质量门；失败页里解析到了标题（`og:title` 或 `h1#activity-name`）。标题里的 `&amp;` 这类实体会先还原成正常文字再拿去搜。

**为什么这条路走得通**：`Search/scripts/yuanbao_search.py` 从元宝结果页拿到的就是**永久直链** `mp.weixin.qq.com/s?__biz=…&mid=…&idx=…&sn=…&chksm=…#rd`，不像搜狗 `-r` 还原出来的是带 `timestamp`/`signature` 的临时票据（会过期）。所以换源链接能直接喂给本脚本，不需要还原步骤。

**脚本实际做的事**：搜一次，取前 3 条（`FALLBACK_CANDIDATES`），逐个用同一套四层 + 同一套质量门重读；第一个读到合格正文的就返回。命中结果的 `source_url` 是**换源后的真实链接**，`note` 里写明标题、原链接与新链接，`attempts`/`diag` 把前后两轮合并，看得出是从哪里换过来的。

**三道约束（改代码时别拆）**：

1. **不回环**：递归调用固定传 `yuanbao_fallback=False`，元宝只搜一次，候选再失败也不会继续搜下去。
2. **链接白名单**：换源 URL 来自外部结果页，属不可信输入。`safe_article_url()` 只放行 `http(s)://mp.weixin.qq.com`（无端口）；外域、`mp.weixin.qq.com.evil.example` 这种子串伪装、带端口、非法 IPv6 一律丢弃，**不发任何请求**，并在诊断里写明。这道门在 Read 侧独立实现，不依赖 Search 内部函数。
3. **请求量不放大**：原四层最多 6 次 HTTP（`LAYER_TRIES=2` × 3 层）+ 元宝搜索最多 2 次 + 最多 3 个候选各走一遍同样的四层（各最多 6 次 HTTP）。全程串行、不并发、不破解验证码，命中元宝 `antispider` 时就此停手。

**默认关的理由**：会额外访问一个外部站点；而且按标题搜同款**可能命中转载、改写或同题不同文**，不是百分百换回原文。调用方应当知情并核对 `source_url` 与 `note`。因此它只在显式加 `--yuanbao` 时启用，`--fixture` 离线解析路径永不触发（会打 NOTE 说明已忽略，全程不联网）。

**失败时怎么办**：元宝返回空、被拦、解析异常，或 3 个候选都没取到正文 → 干净回到原来的失败结论，退出码 1，诊断里逐条写明原因。**不要对同一个原链接反复重跑**：反复请求会加深风控。此时改走 `Search/` 用标题 + 公众号名人工确认来源，或按 `Read/references/cdp-edge.md` 把 Edge 调试端口配好再读。

判据见 `tests/test_read_yuanbao_fallback.py`（纯离线，注入假元宝模块，覆盖默认关闭、CDP 异常仍兜底、不回环、恶意链接丢弃等方向）。

## 一、命令

```bash
python Read/scripts/read_wechat.py "<mp.weixin.qq.com 链接>"              # Markdown 打印到 stdout
python Read/scripts/read_wechat.py "<链接>" -o article.md                 # 存文件
python Read/scripts/read_wechat.py "<链接>" --json                        # 结构化结果（含正文与逐项诊断）
python Read/scripts/read_wechat.py "<链接>" --no-cdp                      # 只用 HTTP 三层，不起浏览器
python Read/scripts/read_wechat.py "<链接>" --layer 2                     # 最多降到第 2 层
python Read/scripts/read_wechat.py "<链接>" --min-chars 1200              # 收紧正文长度阈值
python Read/scripts/read_wechat.py "<链接>" --yuanbao                     # 四层失败时用标题去元宝换源兜底（见第零节）
python Read/scripts/read_wechat.py x --fixture saved.html                 # 离线解析本地存下的页面
```

输出：YAML frontmatter（`source_url`/`title`/`author`/`account`/`published`/`cover`/`digest`/`extract_layer`/`content_chars`/`note`/`fetched_at`）+ 正文 Markdown。
退出码：0 = 过质量门；1 = 失败，stderr 打印各层尝试与判定原因。

## 二、四层降级取页

`success` 必须伴随非空正文：只拿到标题、正文为空一律判失败并继续降级。

| 层 | 手段 | 什么时候够用 |
|---|---|---|
| 1 | Mobile UA 直连（Android Chrome UA） | 无验证墙的普通文章 |
| 2 | Desktop UA + cookie jar（Session 语义，cookie 随请求带） | 需要先落 cookie 的请求 |
| 3 | Desktop UA + 完整浏览器头（`Accept`/`Accept-Language`/`Accept-Encoding: identity`/`Upgrade-Insecure-Requests`/`Sec-Fetch-*`/`Referer: https://mp.weixin.qq.com/`） | 按 header 完整性风控的页面 |
| 4 | CDP 浏览器自动化（本机 Edge） | 验证墙文章：页面要在真实浏览器里跑过 JS 才有正文 |

第 4 层的连接序列固化在 `Read/references/cdp-edge.md`（自包含，含代码与已验证的坑）：读 Edge 的 `DevToolsActivePort`（两行：端口 + WebSocket 路径，UUID 每次重启都变，不能写死；默认路径按平台给候选，取不到时用环境变量 `WX_EDGE_DEVTOOLS_PORT_FILE` 直接指向该文件，不改脚本）→ 连 `ws://127.0.0.1:<port><path>`（禁止带 Origin）→ `Target.createTarget` → `Target.activateTarget` → `Target.attachToTarget(flatten:true)` → 带 `sessionId` 的 `Runtime.evaluate` 取 `document.documentElement.outerHTML`。**关键坑**：CDP 会在响应流里夹带页面事件消息，必须循环读到 `id` 匹配才算收到应答，单次 `recv()` 会读到别的消息导致 `attachToTarget` 看似失败。

重试纪律（上限在 `read_wechat.py` 的 `LAYER_TRIES` 与 `HTTP_MAX_PER_URL` 里，改这两个常量判据会报红）：第 1–3 层每层最多 2 次网络请求（1 次正常 + 1 次连接类异常补发），内容不合格不在同层重试、直接换层，三层合计最多 **6 次**；第 4 层是浏览器导航，不在这 6 次之内。四层走完仍失败就停手输出诊断。

## 三、质量门（判「取到了全文」而不是「请求成功了」）

依次判，任一不过即 FAIL：

1. **正文节点缺失** → `#js_content` 取不到（验证墙或结构变更）。
2. **命中验证墙标记** → 正文区出现 `wappoc_appmsgcaptcha`、"环境异常"、"完成验证后即可继续访问"、"验证码拦截"。
3. **正文过短** → 去标签后非空白字符数 < `--min-chars`（默认 800，经验阈值不是官方口径）。**短文豁免**：字数不足但标题、发布时间、正文节点三者齐备，判 PASS 并在 `note` 里写明豁免——短推文本来就没 800 字，不能因此判失败。缺标题或缺发布时间时不适用豁免。

## 四、解析要点

- 正文节点：`id="js_content"`（回退 `class="rich_media_content"`）。
- 元信息：标题 `og:title` → `h1#activity-name`；作者 `og:article:author` → `span#js_author_name`；公众号 `og:account_name` → `strong#js_name`；发布时间 `article:published_time` → `em#js_publish_time`；封面 `og:image`；摘要 `og:description`。
- HTML→Markdown：优先 BeautifulSoup（`html.parser`），逐节点映射标题/加粗/斜体/链接/图片/列表/引用/代码块/段落。解析路径记在结果的 `parse_mode`：`bs4` 正常；`bs4-no-node` 表示 bs4 在但正文节点没找到——判失败并降级下一层，不猜正文；`regex-degraded` 表示未安装 bs4、走正则截取正文（该路径不产结构，只有段落文本）。
- 图片 URL：保留 `wx_fmt`/`wx_co`/`tp` 参数，只去掉 `wx_lazy` 懒加载标记；优先 `data-src` 再 `src`。微信图片有 Referer 防盗链，本地另存需带 `Referer: https://mp.weixin.qq.com`。
- 编码：按响应头 charset，再退 UTF-8、GBK。

## 五、依赖

- 第 1–3 层：Python 标准库（`urllib` + `re`），无第三方硬依赖。
- 第 4 层：`websocket-client`（`pip install websocket-client`）+ 本机 Edge 已开远程调试端口。
- 可选：`beautifulsoup4`（`pip install beautifulsoup4`）。缺它仍能取到正文，但 `parse_mode` 落到
  `regex-degraded`：输出的 Markdown 只有段落文本，标题层级、加粗/斜体、列表、引用、代码块围栏、
  图片地址都不产出。要结构化正文就得装 bs4。`tests/test_read_gate.py` 按「有没有 bs4」分两支断言
  （有 bs4 判结构七项，无 bs4 判上面这条降级契约），并在日志里打印走的是哪一支。两支都不许伪装：
  没装 bs4 却报告 `parse_mode="bs4"`、降级路径凭空产出 `## ` 结构、装了 bs4 却丢掉图片映射，都报红；
  降级契约满足时是绿，但日志会写明「本机未装 bs4，结构断言不适用」，引用结果时看得见这一跑测了什么。

## 六、脆弱性（用前即时验证）

- 依赖 `mp.weixin.qq.com` 页面结构与微信风控策略，两者都可能随改版失效。失败且代码没变时：按四层逐层降级看诊断，先怀疑结构/UA 策略变化，不反复重试同一层。
- CDP 路径要求 Edge 在跑且调试端口开着；`DevToolsActivePort` 不存在时脚本会直接说明缺哪个前提，`--no-cdp` 可跳过该层。
- `wx_fmt`/`wx_co` 若失效，图片可能 403；改取 `data-src` 或原图直链。

## 七、与其他子技能的关系

需要先**发现/定位**文章（只有主题、没有链接）时走同级 `Search/`；搜到的跳转链接由 `Search/scripts/search_wechat.py -r` 还原成 `mp.weixin.qq.com` 链接后再交给本脚本。搜到的真实链接带签名时效，拿到就立即读取，不要存档 URL 待用。

`Search/` 有两条通道：搜狗（`search_wechat.py`，跳转链接要 `-r` 还原成临时票据）与元宝（`yuanbao_search.py`，结果即永久直链、无需还原）。本脚本第零节的 `--yuanbao` 兜底走的是后者，运行期动态加载 `Search/scripts/yuanbao_search.py`——**这是一条跨子技能软依赖**：该文件缺失或导入失败时不会崩，只把原因写进诊断并回到原失败结论（不静默假装成功）。搬动或改名那个文件前先查这条边，判据在 `tests/test_read_yuanbao_fallback.py` 的「搜索抛异常」方向。

内容仅供合规阅读与研究，遵守原文版权。
