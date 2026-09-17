# 微信公众号官方接口 → 文档章节映射

官方文档基址：**微信公众平台开发文档** `https://developers.weixin.qq.com/doc/offiaccount/`
所有接口均位于 `api.weixin.qq.com/cgi-bin`，POST（除 token 为 GET）。

| 能力 | 官方接口 | 文档章节 |
|---|---|---|
| 获取 access_token | `GET /cgi-bin/token` | 入门指引 / 获取 access_token |
| 封面上传（永久素材） | `POST /cgi-bin/material/add_material?type=image` | 素材管理 / 新增永久素材 |
| 正文图片上传 | `POST /cgi-bin/media/uploadimg` | 素材管理 / 上传图文消息内的图片 |
| 新增草稿 | `POST /cgi-bin/draft/add` | 草稿管理和商品卡片 / 新增草稿 |
| 更新草稿 | `POST /cgi-bin/draft/update` | 草稿管理和商品卡片 / 更新草稿 |
| 获取草稿详情 | `POST /cgi-bin/draft/get` | 草稿管理和商品卡片 / 获取草稿详情 |
| 获取草稿列表 | `POST /cgi-bin/draft/batchget` | 草稿管理和商品卡片 / 获取草稿列表 |
| 获取草稿总数 | `POST /cgi-bin/draft/count` | 草稿管理和商品卡片 / 获取草稿总数 |
| 删除草稿 | `POST /cgi-bin/draft/delete` | 草稿管理和商品卡片 / 删除草稿 |
| 发布草稿 | `POST /cgi-bin/freepublish/submit` | 发布能力 / 发布草稿 |
| 发布状态查询 | `POST /cgi-bin/freepublish/get` | 发布能力 / 发布状态查询 |
| 获取已发布列表 | `POST /cgi-bin/freepublish/batchget` | 发布能力 / 获取已发布的消息列表 |
| 删除已发布文章 | `POST /cgi-bin/freepublish/delete` | 发布能力 / 删除发布文章 |

## 关键请求体

- `draft/add`：`{"articles": [<article>]}`（数组）
- `draft/update`：`{"media_id": "...", "index": 0, "articles": <article>}`（**单对象**，index 为多图文位置，单图文为 0）
- `draft/get`：`{"media_id": "..."}`；`draft/delete`：`{"media_id": "..."}`
- `draft/batchget`：`{"offset": 0, "count": 20, "no_content": 1}`（no_content=1 不含正文，=0 含正文与 URL）
- `freepublish/submit`：`{"media_id": "..."}` → 返回 `publish_id`
- `freepublish/get`：`{"publish_id": "..."}` → `publish_status`（0 成功 / 1 发布中 / 2 原创失败 / 3 常规失败 / 4 审核不通过 / 5 成功后删除 / 6 成功后封禁）
- `freepublish/batchget`：`{"offset": 0, "count": 20, "no_content": 1}`
- `freepublish/delete`：`{"article_id": "..."}`

## article 字段（draft/add 与 draft/update）

| 字段 | 必填 | 说明 |
|---|---|---|
| title | 是 | ≤64 字节 |
| author | 否 | 作者名（默认取 WECHAT_AUTHOR） |
| digest | 否 | ≤120 字符 |
| content | 是 | 微信兼容 HTML（内联样式，正文图 mmbiz URL） |
| content_source_url | 否 | 原文链接（`--source-url`） |
| thumb_media_id | 是 | 封面永久素材 media_id（add_material type=image 返回） |
| need_open_comment | 否 | 1 开启评论 |
| only_fans_can_comment | 否 | 1 仅粉丝可评论 |

## 官方限额（实测与文档口径）

- access_token：有效期 7200 秒；每日获取上限 2000 次。
- `media/uploadimg`：每日 1 万张、累计 20 万张；图片 ≤10MB；URL 长期有效。
- 永久素材（`add_material`）：图片有总数上限（5000 以内，未认证账号更低），长期高频使用注意清理。
