#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Push an article to a WeChat Official Account (公众号) draft box.

Credentials are read from environment variables (NEVER hardcode them):
  WECHAT_APPID   - Official Account AppID
  WECHAT_SECRET  - Official Account AppSecret
  WECHAT_AUTHOR  - author name shown in article (optional, default 映星视界)

Usage:
  python wx_draft_push.py --html <path.html> --title "<title>" --digest "<digest>" [--cover <img>]

Steps performed:
  1. GET access_token  (cgi-bin/token)
  2. POST cover image  (cgi-bin/material/add_material?type=image) -> thumb_media_id
  3. POST draft        (cgi-bin/draft/add) -> media_id

Notes:
  - Uses only stdlib (urllib). The WeChat API REQUIRES POST when a body is sent;
    urllib auto-selects POST when `data` is provided and method is left unset.
  - Cover is optional. Omit --cover to push a draft without a thumbnail.
  - JSON is serialized with ensure_ascii=False so Chinese stays readable.
"""
import os
import sys
import json
import uuid
import mimetypes
import urllib.request
import urllib.error

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
        return json.loads(e.read().decode("utf-8", "ignore"))


def get_token(appid, secret):
    url = f"{API}/token?grant_type=client_credential&appid={appid}&secret={secret}"
    return http_json(url)


def upload_image(token, path):
    url = f"{API}/material/add_material?access_token={token}&type=image"
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


def create_draft(token, article):
    url = f"{API}/draft/add?access_token={token}"
    body = json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8")
    return http_json(url, data=body, headers={"Content-Type": "application/json"})


def parse_args(argv):
    kv = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--html", "--title", "--digest", "--cover"):
            kv[a.lstrip("-")] = argv[i + 1]
            i += 2
        else:
            i += 1
    return kv


def main():
    kv = parse_args(sys.argv[1:])
    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_SECRET")
    if not appid or not secret:
        print("ERR: WECHAT_APPID / WECHAT_SECRET env vars are not set")
        sys.exit(1)
    if not kv.get("html"):
        print("ERR: --html <path> is required")
        sys.exit(1)

    tok = get_token(appid, secret)
    if "access_token" not in tok:
        print("ERR get_token:", json.dumps(tok, ensure_ascii=False))
        sys.exit(1)
    token = tok["access_token"]
    print("TOKEN ok, expires_in:", tok.get("expires_in"))

    thumb = ""
    if kv.get("cover"):
        up = upload_image(token, kv["cover"])
        if "media_id" in up:
            thumb = up["media_id"]
            print("COVER media_id:", thumb)
        else:
            print("WARN cover upload:", json.dumps(up, ensure_ascii=False))

    with open(kv["html"], "r", encoding="utf-8") as f:
        content = f.read()

    article = {
        "title": kv.get("title", ""),
        "author": os.environ.get("WECHAT_AUTHOR", "映星视界"),
        "digest": kv.get("digest", ""),
        "content": content,
        "thumb_media_id": thumb,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    res = create_draft(token, article)
    if "media_id" in res:
        print("DRAFT_OK media_id:", res["media_id"])
    else:
        print("ERR create_draft:", json.dumps(res, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
