---
name: materials
description: '微信公众号素材/图片上传：封面永久素材上传（material/add_material type=image）与正文图片上传（media/uploadimg 换 mmbiz.qpic.cn URL）。当用户要求“上传封面”“换正文图”“做公众号配图”时使用，也是 draft 制作时正文图与封面的前置能力。凭据从 WECHAT_APPID / WECHAT_SECRET 环境变量读取。'
---

# 素材管理（materials）

通过微信公众号官方「素材管理 / 上传图文消息内图片」接口上传封面与正文图。官方文档：素材管理、上传图文消息内的图片（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 能力与命令

统一 CLI：`../scripts/wx_api.py`。凭据环境变量见 `../SKILL.md`。

| 操作 | 官方接口 | 命令 | 说明 |
|---|---|---|---|
| 封面（永久素材） | `POST /cgi-bin/material/add_material?type=image` | `python ../scripts/wx_api.py cover ".\cover.png"` | 返回 `media_id`（供草稿 `--cover`） |
| 正文图片 | `POST /cgi-bin/media/uploadimg` | `python ../scripts/wx_api.py uploadimg ".\img.png"` | 返回 `url`（`mmbiz.qpic.cn`，放入 HTML 正文） |

## 要点

- **封面**：微信大卡封面比例 2.35:1（900×383）展示最佳；建议宽构图（如 2048×880），裁剪损失小。`draft-add --cover` 内部会调用此上传。
- **封面生成器（系列文章每篇换封面）**：`scripts/gen_cover.py --out cover-<篇号>.png [--pattern layers|guard|grid|circuit] [--seed N]`——纯几何无文字（深蓝 #1F3864 + 金 #B08D3E），`--seed` 缺省随机保证每篇不同；`--pattern` 四种意象（layers 装饰器嵌套 / guard 守卫分支 / grid 账本网格 / circuit 订单回路）。
- **正文图**：必须先 `uploadimg` 换成 `mmbiz.qpic.cn` 域名 URL 再写进 HTML，否则微信端不显示。`draft-add` 只处理 `--cover`，**正文图需在制作 HTML 时已替换**。
- **一步到位**：生成 wx 内联版 HTML 前，先把全部配图批量 `uploadimg` 换 URL，HTML 中**直接引用 mmbiz URL**（禁止先写本地路径再事后替换——本地路径一旦误推，图片全部不显示且需整篇重推）。
- **批量预上传（推荐）**：多图场景用 `scripts/upload_imgs.py` 一键完成——`python upload_imgs.py --html "<article-wx.html>" [--map mmbiz_map.json]` 自动扫描 HTML 内本地图片并逐个上传打印 mmbiz URL（也可 `--img a.png b.png` 直接给图片列表）；`--map` 可存「图片 basename → URL」映射供后续引用。**实现（3.4.0 起）：一次取 token 循环上传全部图片（不再逐张现取）；遇 45009 自动退避重试（3s/6s/9s，最多 3 次）**。凭据同样走环境变量。
- **URL 失效处理**：`uploadimg` 返回的 `mmbiz.qpic.cn` URL 为永久素材 URL（官方口径长期有效）。若隔段时间后发现草稿/已发文章中图片不显示，按「重新 `uploadimg` → 替换 HTML 中的旧 URL → `draft-update` 重推」处理；每次换会话批量处理前，建议抽查 1 篇确认 URL 是否仍可访问。
- **官方限额**：`uploadimg` 每日上限 1 万张、累计上限 20 万张（超限报错后等次日或清理）。素材（`add_material`）另有永久素材总数上限，长期高频使用留意。
- 上传使用 multipart/form-data，`../scripts/wx_api.py` 已封装。图片建议 ≤ 10MB，常见格式 jpg/png 均可。

## 排障

上传失败（`40164` IP 白名单、`43002` GET/POST、`45009` 频率）→ `../references/gotchas.md`。
