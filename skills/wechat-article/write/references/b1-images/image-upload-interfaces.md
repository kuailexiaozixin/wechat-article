---
name: image-upload-interfaces
summary: B1 配图上传的接口口径、图片规格限制、批量上传与退避、URL 失效处理。
---

# B1 配图上传：接口与规格

本流程负责一件事：把要出现在文章里的图，变成微信端能显示的地址。官方文档见
`https://developers.weixin.qq.com/doc/offiaccount/`（素材管理、上传图文消息内的图片）。
本文自带执行所需的全部口径；接口细节的原始出处是仓库根 `references/api-docs.md`
「官方限额」，供溯源与核对，不读它也能执行本阶段。

## 两个接口不是一回事

| 用途 | 官方接口 | 命令 | 拿到什么 | 写到哪里 |
|---|---|---|---|---|
| 封面（永久素材） | `POST /cgi-bin/material/add_material?type=image` | `python scripts/wx_api.py cover ".\cover.png"` | `media_id` | 草稿参数 `--cover`（`draft-add` 内部会自己调这个上传） |
| 正文图 | `POST /cgi-bin/media/uploadimg` | `python scripts/wx_api.py uploadimg ".\img.png"` | `url`（`mmbiz.qpic.cn`） | 直接写进正文 HTML 的 `<img src>` |

封面换的是 `media_id`，正文图换的是 URL，两者不能互换：把 mmbiz URL 当 `thumb_media_id`
传会报 `40007`，把 `media_id` 当 `<img src>` 写进正文图片不显示。凭据走环境变量，见根 `SKILL.md`。

## 规格限制（超限是最常见的失败原因）

- **正文图**：仅支持 jpg / png，且必须 **< 1MB**。格式不符报 `40005`，尺寸超限报 `40009`。
  大图是正文图的头号失败点——先压缩再上传，不要指望接口宽容。压缩用 `compress_img.py`：
  `python Write/references/b1-images/scripts/compress_img.py <img>`（默认压到 950KB、另存
  `<stem>_min.png`；`--in-place` 就地覆盖原图）。
- **封面**：**10MB**，支持 bmp/png/jpg/jpeg/gif。比例 **2.35:1**（900×383）在大卡上展示最佳；
  建议宽构图（如 2048×880），裁剪损失小。
- **数量额度**：`uploadimg` 上传的图片**不占用**素材库图片数量的 100000 上限（官方口径）。
  永久素材（`add_material`）受素材库总数上限约束（图文消息素材与图片各 100000、其他类型 1000），
  长期高频使用要留意清理。

`scripts/wx_api.py` 已封装 multipart/form-data，不需要自己拼请求体。

## 一步到位原则

生成微信内联版 HTML 之前，先把全部配图批量 `uploadimg` 换成 mmbiz URL，HTML 中**直接引用
mmbiz URL**。禁止先写本地路径再事后替换：本地路径一旦误推，图片全部不显示，且必须整篇重推。
这条纪律由 B3 静态闸的「无本地图片路径」判据兜底，但兜底不等于可以依赖它——重推一次的代价
比按顺序做一遍高。

## 回填后本地可见（单文件铁律）

`upload_imgs.py` 把微信 API 返回的 `http://` 统一升成 `https://mmbiz.qpic.cn/...`（安全预览页
按混合内容拦 http 图片）。但**公网可达不等于本地可见**：WorkBuddy 编辑器、Edge 打开的
`127.0.0.1` 静态服务可能因内容安全策略、防盗链或断网拦掉外链，此时只有破图图标。

因此排版时每张 `<img>` 只写 `src`（mmbiz URL）与内联样式即可，不加任何 base64 兜底。
注意：本地用 `file://` 打开时，微信图床防盗链会返回占位图（HTTP 200），`onerror` 兜底不会触发，
本地看不到真图属预期，真图以公众号后台/编辑器预览为准。
禁止再生成「本地预览版」或「待推送版」等第二份 HTML 交付物。

若尚未回填（仍是 `__MMP__` 占位）又需要本地核图：
`python Write/references/b3-acceptance/scripts/wrap_preview.py article-wx.html --figures <配图目录>`
把占位临时换成 data URI，**只作用于系统临时目录里的预览副本，绝不写回原文件**，也不算交付物。
B3 静态闸的 `check_single_artifact.py` 会检查稿件目录里是否多出第二份 HTML。

## 批量上传

多图场景用 `Write/references/b1-images/scripts/upload_imgs.py`，不要逐张手敲：

```bash
python Write/references/b1-images/scripts/upload_imgs.py --html "<article-wx.html>" [--map mmbiz_map.json]
python Write/references/b1-images/scripts/upload_imgs.py --img a.png b.png
```

- 自动扫描 HTML 内的本地图片并逐个上传、打印 mmbiz URL；也可用 `--img` 直接给图片列表。
- `--map` 存「图片 basename → URL」映射，供后续引用（按 basename 匹配，路径不同不影响）。
- 实现（3.4.0 起）：**一次取 token 循环上传全部图片**（不再逐张现取）；**遇 45009 自动退避重试**
  （3s / 6s / 9s，最多 3 次）。
- 上传前逐张做尺寸预检（阈值见上节）：超限即逐张打印 FAIL 并退出 1，**不发请求、不取 token**——
  避免把频率额度浪费在注定失败的图上。

## 封面生成器

系列文章每篇换封面用 `Write/references/b1-images/scripts/gen_cover.py`：

```bash
python Write/references/b1-images/scripts/gen_cover.py --out cover-<篇号>.png \
  [--pattern layers|guard|grid|circuit] [--seed N] [--title "主标题"] [--subtitle "副标题"] [--font ttf]
```

- 深蓝 `#1F3864` + 金 `#B08D3E` 几何构图；`--seed` 缺省随机，保证每篇不同；
  `--pattern` 四种意象：layers 装饰器嵌套 / guard 守卫分支 / grid 账本网格 / circuit 订单回路。
- `--title` / `--subtitle` 可选：Pillow 在封面上方 1/3 区**原生绘制**中文字（字体按
  msyh/simhei 等系统常见中文字体依次尝试，可用 `--font` 指定）。这是正当的原生绘制，
  与「禁止在位图上盖字修补」不冲突——后者针对的是渲染失败后的事后补救（见禁令第 1 条）；
  不传文字参数即纯几何无字，与旧版一致。

## URL 失效处理

`uploadimg` 返回的 `mmbiz.qpic.cn` URL，官方页只给 `url` 字段、**未写有效期**，本技能按长期可用
处理并定期抽查。若发现草稿或已发文章图片不显示：重新 `uploadimg` → 替换 HTML 中的旧 URL →
`draft-update` 重推。每次换会话批量处理前，用 `check_urls.py` 跑一轮体检：
`python Write/references/b1-images/scripts/check_urls.py --map mmbiz_map.json [--html article-wx.html]`
（逐条 HTTP GET 报状态码；`--html` 额外核正文引用的 mmbiz URL 是否都在 map 里，防漏传）。

## 排障（本阶段常见错误的结论已内联，溯源见根 `references/gotchas.md`）

- `40164` IP 白名单：把报错里的 IP 加进公众号后台「设置与开发 → 基本配置 → IP白名单」
  再试；出口 IP 会随会话变化——再失败就再读新 IP 再加。
- `43002` require POST：根因是 HTTP 客户端有 body 却强制 GET；用 `wx_api.py`
  （有 body 时不设 method，urllib 自动用 POST）不会撞。
- `45009` 频率限制：退避 3s/6s/9s 最多 3 次；已内置在 `upload_imgs.py`，
  手动单张调用时需要自己退避。
- 排障前先读 `references/gotchas.md`（唯一一份失效模式清单，本节只引结论）。

## 图片清单先行

本流程的输入不是一堆图片文件，而是一张清单：每张图先写清它插在哪个位置、承担什么作用、
画面内容是什么、依据哪份材料。判据与字段见 `figure-manifest-spec.md`。
清单先过 `figure_manifest.py check`，再执行上面的上传，顺序不可颠倒。
