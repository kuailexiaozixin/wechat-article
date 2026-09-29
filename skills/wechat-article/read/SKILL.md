---
name: read
description: 从 mp.weixin.qq.com 链接提取微信公众号文章正文与元信息并转 Markdown 的方法（四层渐进式：Mobile UA 直连 → Desktop UA + Session → 完整浏览器 Headers → CDP 浏览器自动化），含 HTML 解析要点、图片防盗链处理与验证墙判定。当用户要求“读取/提取/解析某篇公众号文章正文”时使用。
---

# 微信公众号文章读取方法

方法论已验证有效（实测可读取验证墙文章与普通文章，CDP 路径与 HTTP 路径均已跑通）。

## 阅读与解析（四层渐进式，以"非空正文"为准）

核心原则：`success` 必须伴随**非空 markdown**；仅拿到标题、正文为空 → 判失败继续降级。

1. **Mobile UA 直连**（Android Chrome UA）——无验证墙文章可直接拿到正文
2. **Desktop UA + Session**（requests Session 携带 Cookie）
3. **完整浏览器 Headers**（Accept / Accept-Language zh-CN / Referer / Sec-Fetch 系列）
4. **CDP 浏览器自动化**（验证墙场景）：完整连接方法见 `references/cdp-edge.md`（自包含，含代码与已验证的坑）——读本机 Edge 调试端口文件 `%LOCALAPPDATA%\Microsoft\Edge\User Data\DevToolsActivePort`（两行：端口 + ws_path）→ 连接 `ws://127.0.0.1:<port><ws_path>`（禁止 Origin 头）→ `Target.createTarget`（url）→ `Target.activateTarget` → `Target.attachToTarget`(flatten:true) → `Runtime.evaluate` 取 `#js_content`
   - **关键坑（已验证）**：CDP 响应必须**循环读取直到 `id` 匹配**——CDP 会夹带页面事件消息，单次 `ws.recv()` 会读到错误响应导致 `attachToTarget` 失败

## 解析要点（HTML）

- 正文：`id="js_content"`（或 `class="rich_media_content"`）
- 元信息：标题 `og:title` → `h1#activity-name`；作者 `og:article:author` → `span#js_author_name`；公众号 `og:account_name` → `strong#js_name`；发布时间 `article:published_time` → `em#js_publish_time`；封面 `og:image`；摘要 `og:description`
- HTML→Markdown：lxml + BeautifulSoup 递归遍历 DOM（h1-6 / strong / em / a / img / li / pre 映射），降级链路 bs4+html.parser → 纯正则
- 图片：保留 `wx_fmt`/`wx_co`/`tp` 参数，去除 `wx_lazy` 懒加载标记；优先 `data-src` 再 `src`；微信图片有 Referer 防盗链，需加 `Referer: https://mp.weixin.qq.com`
- 验证墙判定：正文缺失（js_content 空）→ 判失败并降级 CDP；"验证提示但正文完整" → 标记 warning 继续提取

## 已验证结论

- 已实测能读取**验证墙文章**（CDP 路径）与**无验证墙文章**（HTTP 路径）
- CDP 连接方法已固化在 `references/cdp-edge.md`（自包含，不依赖其他技能）
- 依赖库：`requests` / `lxml` / `websocket-client`（CDP 层）；`beautifulsoup4` 可选（缺失时降级 html.parser / 纯正则路径）
- CDP 前提：本机 Edge 已开启远程调试端口（`DevToolsActivePort` 存在 + 端口监听）
- 单 URL 重试不超过 3 次避免封 IP；内容仅供合规场景使用，遵守版权

## 脆弱性标注（外部路径，使用前即时验证）

- 本方法依赖 `mp.weixin.qq.com` 页面结构与微信反爬策略，**两者都可能随平台改版失效**：若某次提取失败且方法本身没变，先怀疑页面结构/UA 策略变化，用「四层渐进式」逐层降级重试，不要反复重试同一层。
- CDP 路径依赖本机 Edge 调试端口，端口被占用或 Edge 未启动时 `DevToolsActivePort` 不存在——先确认 Edge 运行状态。
- 图片防盗链 Referer 参数（`wx_fmt`/`wx_co`）若失效，图片可能 403；改用 `data-src` 或原图直链。

## 与其他子技能的关系

- 本方法**读取**单篇已知链接的公众号文章。若需先**发现/定位**文章或公众号，见同级 `search/`；搜得的真实 `mp.weixin.qq.com` 链接再用本方法读取。
- CDP 连接本机 Edge 的具体操作见本子技能 `references/cdp-edge.md`（读取 DevToolsActivePort 直连 WebSocket 的完整代码与排障）。
