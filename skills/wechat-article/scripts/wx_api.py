# -*- coding: utf-8 -*-
"""
微信公众号 API CLI（草稿箱 + 素材 + 发布权限探测）

官方文档：
  微信公众平台开发文档（developers.weixin.qq.com/doc/offiaccount）
  - 草稿管理与商品卡片：Draft_Box/Add_draft.html, Update_draft.html, Delete_draft.html, Get_draft.html, Batchget_draft.html, Count_draft.html
  - 素材管理：Material/Add_material.html（封面永久素材）
  - 图片上传：Media/Uploadimg.html（正文图片换 mmbiz URL）

凭据从环境变量读取（禁止硬编码 / 写文件 / 打日志）：
  WECHAT_APPID   - 公众号 AppID
  WECHAT_SECRET  - 公众号 AppSecret
  WECHAT_AUTHOR  - 作者名（可选，缺省省略 author 字段；部分账号作者字段长度很小，超限报 45110）

用法：
  python wx_api.py token
  python wx_api.py cover <img_path>
  python wx_api.py uploadimg <img_path>
  python wx_api.py draft-add  --title <短标题≤64字节> --digest <摘要≤120字符> --content <html文件> [--cover <img>] [--author <名>] [--source-url <原文链接>]
  python wx_api.py draft-update --media <media_id> --title ... --digest ... --content <html> [--cover <img>] [--source-url <原文链接>]
  python wx_api.py draft-get <media_id>
  python wx_api.py draft-list [--offset 0] [--count 20]
  python wx_api.py draft-count
  python wx_api.py draft-delete <media_id>
  python wx_api.py check-perm                         # 发布接口权限预探测（个人未认证账号实测 48001）

注意：
  - access_token 有效期 7200 秒，每次调用现取，不缓存。
  - 正文图片必须先 uploadimg 换成 mmbiz.qpic.cn URL 才能显示。
  - 微信会剥离 <style> 与 <pre>；代码块必须用 <section>+逐行<p>+&nbsp; 结构。
  - draft-add/draft-update 的 --source-url 对应官方 content_source_url（原文链接，可选）。
  - draft-update 被腾讯 WAF 501 拦截时自动绕行：回读原封面 → delete 旧草稿 → add 新草稿，返回新 media_id（原 media_id 失效）。
"""
import os
import sys
import json
import uuid
import mimetypes
import urllib.request
import urllib.error
import urllib.parse

API = "https://api.weixin.qq.com/cgi-bin"


def http_json(url, data=None, headers=None, method=None):
    kw = {"url": url, "data": data, "headers": headers or {}}
    if method:
        kw["method"] = method
    req = urllib.request.Request(**kw)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            return json.loads(raw)
        except Exception:
            # 网关/WAF 拦截返回非 JSON（如腾讯 waf 501 页），原样输出便于诊断
            return {"errcode": e.code, "errmsg": "non-JSON response",
                    "raw": raw[:400]}


def get_token(appid, secret):
    url = f"{API}/token?grant_type=client_credential&appid={appid}&secret={secret}"
    return http_json(url)


def multipart_upload(token, path, endpoint, extra=""):
    """构造 multipart/form-data 上传。endpoint 形如 material/add_material?type=image"""
    url = f"{API}/{endpoint}&access_token={token}" if "?" in endpoint else f"{API}/{endpoint}?access_token={token}"
    boundary = "----WxBoundary" + uuid.uuid4().hex
    fn = os.path.basename(path)
    ct = mimetypes.guess_type(fn)[0] or "image/png"
    with open(path, "rb") as f:
        body = f.read()
    payload = b""
    payload += f"--{boundary}\r\n".encode()
    payload += f'Content-Disposition: form-data; name="media"; filename="{fn}"\r\n'.encode()
    payload += f"Content-Type: {ct}\r\n\r\n".encode()
    payload += body
    payload += b"\r\n"
    payload += f"--{boundary}--\r\n".encode()
    return http_json(
        url,
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def build_article(kv, content_html, thumb, author):
    art = {
        "title": kv.get("title", ""),
        "digest": kv.get("digest", ""),
        "content": content_html,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    if author:
        art["author"] = author  # 空则整体省略：部分账号作者字段上限很小，超限报 45110
    if thumb:
        art["thumb_media_id"] = thumb  # 空封面不传：draft/update 时传空串会 40007，省略则保留原封面
    if kv.get("source_url"):
        art["content_source_url"] = kv["source_url"]
    return art


def parse_args(argv):
    kv = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--title", "--digest", "--content", "--cover", "--author",
                 "--media", "--offset", "--count", "--source-url"):
            kv[a.lstrip("-")] = argv[i + 1]
            i += 2
        elif a in ("--full", "--yes"):
            kv[a.lstrip("-")] = "1"
            i += 1
        else:
            i += 1
    return kv


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    kv = parse_args(argv[1:])

    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_SECRET")
    if not appid or not secret:
        print("ERR: WECHAT_APPID / WECHAT_SECRET 未设置", file=sys.stderr)
        sys.exit(1)

    tok = get_token(appid, secret)
    if "access_token" not in tok:
        print("ERR token:", json.dumps(tok, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    token = tok["access_token"]
    author = os.environ.get("WECHAT_AUTHOR", "")  # 默认空：省略 author 字段，避免部分账号 45110

    if cmd == "token":
        print("TOKEN ok, expires_in:", tok.get("expires_in"))
        return

    if cmd == "cover":
        up = multipart_upload(token, kv.get("cover", argv[1]), "material/add_material?type=image")
        print(json.dumps(up, ensure_ascii=False))
        return

    if cmd == "uploadimg":
        up = multipart_upload(token, kv.get("cover", argv[1]), "media/uploadimg")
        print(json.dumps(up, ensure_ascii=False))
        return

    if cmd in ("draft-add", "draft-update"):
        if not kv.get("content"):
            print("ERR: --content <html 文件> 必填", file=sys.stderr)
            sys.exit(1)
        with open(kv["content"], "r", encoding="utf-8") as f:
            content = f.read()
        thumb = ""
        if kv.get("cover"):
            up = multipart_upload(token, kv["cover"], "material/add_material?type=image")
            if "media_id" in up:
                thumb = up["media_id"]
            else:
                print("WARN cover:", json.dumps(up, ensure_ascii=False), file=sys.stderr)
        if cmd == "draft-update":
            if not kv.get("media"):
                print("ERR: --media <media_id> 必填", file=sys.stderr)
                sys.exit(1)
            if not thumb:
                # draft/update 必须携带有效 thumb_media_id（省略/空串会 40007）；
                # 未传 --cover 时回读原草稿封面，保证 update 不改变封面。
                try:
                    got = http_json(
                        f"{API}/draft/get?access_token={token}",
                        data=json.dumps({"media_id": kv["media"]}, ensure_ascii=False).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
                    thumb = (got.get("news_item") or [{}])[0].get("thumb_media_id", "")
                except Exception:
                    thumb = ""
        article = build_article(kv, content, thumb, author)
        if cmd == "draft-add":
            res = http_json(
                f"{API}/draft/add?access_token={token}",
                data=json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
        else:
            res = http_json(
                f"{API}/draft/update?access_token={token}",
                data=json.dumps({"media_id": kv["media"], "index": 0, "articles": article},
                                ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            if res.get("errcode") == 501:
                # 腾讯 WAF 拦截 draft/update（gotchas B5）：退避无效，自动绕行 delete+add
                print("WARN draft/update 被 WAF 501 拦截，自动绕行 delete+add ...", file=sys.stderr)
                if not thumb:
                    try:
                        got = http_json(
                            f"{API}/draft/get?access_token={token}",
                            data=json.dumps({"media_id": kv["media"]}, ensure_ascii=False).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                        )
                        thumb = (got.get("news_item") or [{}])[0].get("thumb_media_id", "")
                    except Exception:
                        thumb = ""
                article = build_article(kv, content, thumb, author)  # thumb 可能已更新，重建
                del_res = http_json(
                    f"{API}/draft/delete?access_token={token}",
                    data=json.dumps({"media_id": kv["media"]}, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                add_res = http_json(
                    f"{API}/draft/add?access_token={token}",
                    data=json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                if "media_id" in add_res:
                    res = {"errcode": 0, "bypass": True, "old_media_id": kv["media"],
                           "media_id": add_res["media_id"]}
                else:
                    res = {"errcode": -1, "bypass": True, "delete_result": del_res,
                           "add_result": add_res}
        print(json.dumps(res, ensure_ascii=False))
        return

    if cmd == "draft-get":
        res = http_json(
            f"{API}/draft/get?access_token={token}",
            data=json.dumps({"media_id": kv.get("media", argv[1])}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        print(json.dumps(res, ensure_ascii=False))
        return

    if cmd == "draft-list":
        off = int(kv.get("offset", "0"))
        cnt = int(kv.get("count", "20"))
        res = http_json(
            f"{API}/draft/batchget?access_token={token}",
            data=json.dumps({"offset": off, "count": cnt, "no_content": 1}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        print(json.dumps(res, ensure_ascii=False))
        return

    if cmd == "draft-count":
        res = http_json(f"{API}/draft/count?access_token={token}")
        print(json.dumps(res, ensure_ascii=False))
        return

    if cmd == "draft-delete":
        res = http_json(
            f"{API}/draft/delete?access_token={token}",
            data=json.dumps({"media_id": kv.get("media", argv[1])}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        print(json.dumps(res, ensure_ascii=False))
        return

    if cmd == "check-perm":
        probe = http_json(
            f"{API}/freepublish/batchget?access_token={token}",
            data=json.dumps({"offset": 0, "count": 1, "no_content": 1}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if probe.get("errcode") in (48001, 53010):
            print(json.dumps({"perm": False, "errcode": probe.get("errcode"),
                              "errmsg": probe.get("errmsg")}, ensure_ascii=False))
        elif "errcode" not in probe or probe.get("errcode") == 0:
            print(json.dumps({"perm": True, "total_count": probe.get("total_count", 0)},
                             ensure_ascii=False))
        else:
            print(json.dumps({"perm": "unknown", "detail": probe}, ensure_ascii=False))
        return

    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
