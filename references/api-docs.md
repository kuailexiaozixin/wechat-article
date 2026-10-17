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

## 关键请求体

- `draft/add`：`{"articles": [<article>]}`（数组）
- `draft/update`：`{"media_id": "...", "index": 0, "articles": <article>}`（**单对象**，index 为多图文位置，单图文为 0）
- `draft/get`：`{"media_id": "..."}`；`draft/delete`：`{"media_id": "..."}`
- `draft/batchget`：`{"offset": 0, "count": 20, "no_content": 1}`（no_content=1 不含正文，=0 含正文与 URL）
- 发布接口族（freepublish/submit|get|batchget|delete）：个人未认证账号实测整体返回 48001 无权限，本技能不封装；发布走公众号后台手动操作（见 gotchas A3）。认证账号如需使用，见官方文档「发布能力」章节。

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

## 官方限额（口径与出处）

出处为官方文档基址下「素材管理」章节的「上传图文消息内的图片获取URL」与「新增永久素材」两页（章节名见上表，按基址逐级进入即可查到）；下列引用为该页原文措辞；页面上没有的内容已单独标注，不当作官方口径使用。

- access_token：有效期 7200 秒；每日获取上限 2000 次。
- `media/uploadimg`（正文图）：**「图片仅支持 jpg/png 格式，大小必须在 1MB 以下」**；「该接口所上传的图片，不占用公众号的素材库中图片数量的 100000 个的限制」。格式不符报 `40005 invalid file type`，尺寸超限报 `40009 invalid image size`。`upload_imgs.py` 上传前按 1MB 预检，超限直接 FAIL，不发请求。
  - 返回的 `url` 有效期：官方页只列 `url` 字段，未写有效期与使用范围。本技能把返回 URL 当长期可用处理（历史产物隔月复核仍可访问）；一旦不显示，按 `gotchas.md` C2 重新上传换 URL 后重推。
  - 「每日 1 万张、累计 20 万张」为早前记录的经验值，当前官方页未列该数量限制；触发频率限制时按 `45009` 退避处理。
- `material/add_material?type=image`（封面永久素材）：官方口径图片 10M，支持 bmp/png/jpg/jpeg/gif；素材库总上限为图文消息素材与图片各 100000、其他类型 1000。未认证账号额度更低，长期高频使用注意清理。
