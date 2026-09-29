# 通用排版主题（theme-default）

本文是公众号文章的**排版样式单一来源（默认主题）**。所有样式逐条提取自已推送、已发布文章的真实产物，未经改动。新文章一律套用本资产，不得手写漂移样式；如需新主题，以本文件为模板另建 `theme-<名称>.md` 并同样遵守「样式必须来自已验证产物」原则。

## 设计变量（主色系）

| 变量 | 值 | 用途 |
|---|---|---|
| 主色（深蓝） | `#1F3864` | 大标题、章节标题文字 |
| 点缀色（金） | `#B08D3E` | 标题下装饰线、章节标题左竖条 |
| 正文色 | `#3f3f3f` | 正文段落 |
| 代码块底色 | `#F6F8FA` | 代码块容器背景 |
| 代码块边框 | `#E4E7EC` | 代码块容器边框 |
| 代码文字 | `#24292E` | 代码行文字 |
| 行内代码底/字 | `#F0F2F5` / `#C7254E` | 行内代码 |
| 图注色 | `#9A9A9A` | 图片下方图注 |
| 分割线色 | `#D5DCE6` | 文末分隔 |

## 组件库（已验证组件，样式与已发布文章逐字一致）

### 1. 文章大标题
```html
<p style="font-size:22px;color:#1F3864;text-align:center;font-weight:bold;margin:24px 0 10px;line-height:1.6;">完整标题</p>
```

### 2. 标题下装饰线（金色短线）
```html
<div style="width:64px;height:3px;background:#B08D3E;margin:12px auto 26px;"></div>
```
注：此组件在已发布产物中为 `<div>`（API 推送路径实测微信不清洗、显示正常）；校验器对其仅 WARN。若走编辑器粘贴路径，可换 `<p style="...">&nbsp;</p>`。

### 3. 二级章节标题（左竖条）
```html
<p style="font-size:18px;color:#1F3864;font-weight:bold;margin:28px 0 14px;padding-left:10px;border-left:4px solid #B08D3E;">一、章节标题</p>
```

### 4. 正文段落（首行缩进两字符）
```html
<p style="font-size:16px;color:#3f3f3f;line-height:1.9;letter-spacing:0.02em;text-indent:2em;margin:0 0 14px;text-align:justify;">正文内容……</p>
```

### 5. 行内代码
```html
<code style="background:#F0F2F5;color:#C7254E;border-radius:4px;padding:1px 4px;font-size:14px;">create_order(oid, customer_id)</code>
```
注意：行内代码内 `<` `>` `&` 同样须转义。

### 6. 代码块（section + 逐行 p）
```html
<section style="background:#F6F8FA;border:1px solid #E4E7EC;border-radius:8px;padding:14px 16px;margin:16px 0;overflow-x:auto;">
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;def create_order(oid, customer_id):</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if oid &lt; 0: raise ValueError("invalid id")</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;return order</p>
</section>
```
要点：每行一个 `<p>`、`margin:0`、`text-indent:0`；缩进用 `&nbsp;`（4 空格 = 4 个 `&nbsp;`）；空行 `<p>…&nbsp;</p>`；代码内 `<` `>` `&` 转义；长代码（>15 行）正文只截关键片段并注明仓库路径。

### 7. 正文图片
```html
<img src="http://mmbiz.qpic.cn/…" alt="图注文字" style="max-width:100%;border-radius:10px;margin-bottom:6px;">
```

### 8. 图注（图下小字）
```html
<p style="font-size:12.5px;color:#9A9A9A;text-align:center;margin:6px 0 18px;">图 1 说明文字</p>
```

### 9. 分割线
```html
<p style="border:none;border-top:1px solid #D5DCE6;margin:22px 0;">&nbsp;</p>
```

## 系列约定

- 每个「大标题 → 装饰线 → 引言段」为开篇固定组合；章节标题统一「一、二、三…」中文序号。
- 图注文字格式「图 N 说明」按文章内序号递增。
- 封面每篇更换（纯几何、无文字、2.35:1 宽构图），**不属于**本文档组件，见 Write 主规范。
- 引用框、药丸标签、卡片等组件**系列文章暂未使用**（既有产物中未出现），需要时先设计验证再加入本文档，不得凭空使用。

## 与校验的关系

- 任何新组件加入前，样式必须通过 `validate_wx_html.py`（禁 `<pre>`/`class` 等红线；`<div>` 为 WARN，见组件 2 注）。
- 修改本文档组件样式 = 全系列样式变更，改前在 CHANGELOG 记录，改后抽查已发布文章确认无回归。
