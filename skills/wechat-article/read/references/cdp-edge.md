# CDP 连接本机 Edge（读取公众号验证墙文章）

验证墙场景下的最终手段：通过本机已运行的 Microsoft Edge 的 CDP WebSocket 端口，用浏览器上下文加载文章并提取正文。本方法自包含、经实测验证（不再依赖任何外部浏览器自动化技能）。

**原则（本机实测）**：Edge 的 CDP 只开放 WebSocket 端点，HTTP 端点（`GET /json/version`）返回 404——必须读 `DevToolsActivePort` 文件拿端口和 WebSocket 路径，直接连 `ws://`，严禁用 HTTP 端点。

## 1. 读取 DevToolsActivePort（两行都要）

文件位置：`%LOCALAPPDATA%\Microsoft\Edge\User Data\DevToolsActivePort`（`%LOCALAPPDATA%` 即 `C:\Users\<用户名>\AppData\Local`）

第一行是端口号，第二行是 WebSocket 路径（`/devtools/browser/<uuid>`）。**两行都要读**，只用端口连不上。

```python
import os
port_file = os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data\DevToolsActivePort")
with open(port_file, encoding="utf-8") as f:
    port = int(f.readline().strip())   # 第一行：端口号
    ws_path = f.readline().strip()     # 第二行：WebSocket 路径，如 /devtools/browser/<uuid>
ws_url = f"ws://127.0.0.1:{port}{ws_path}"
```

PowerShell 等价写法：

```powershell
$lines = Get-Content "$env:LOCALAPPDATA\Microsoft\Edge\User Data\DevToolsActivePort"
$wsUrl = "ws://127.0.0.1:$($lines[0])$($lines[1])"
```

**UUID 每次重启都会变**：Edge 重启后 `DevToolsActivePort` 第二行的 UUID 重新生成，严禁硬编码 UUID，必须每次现场读取。

## 2. WebSocket 连接（禁止 Origin 头 + 帧必须 masked）

```python
import websocket
ws = websocket.create_connection(ws_url, suppress_origin=True)
```

- **禁止携带 Origin 头**：握手带任何 Origin 头 Edge 都返回 `403 Forbidden`（`websocket-client` 的 `suppress_origin=True` 即清空 Origin）。CDP 的身份验证依赖 `DevToolsActivePort` 文件的本地文件系统权限——能读到该文件的本地进程才能连接，这本身就是安全屏障，不需要 Origin 校验。
- **客户端帧必须设 mask 位**（`websocket-client` 默认满足；手写帧协议时注意）。

## 3. CDP 调用序列

```python
import json

def cdp(ws, method, params=None, msg_id=1):
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    # 关键坑：CDP 会夹带页面事件消息，必须循环读取直到 id 匹配，
    # 单次 recv() 会读到错误响应导致后续调用失败
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == msg_id:
            return msg

cdp(ws, "Target.createTarget", {"url": article_url})           # 返回 targetId
cdp(ws, "Target.activateTarget", {"targetId": tid})
cdp(ws, "Target.attachToTarget", {"targetId": tid, "flatten": True})  # 返回 sessionId
# 用 sessionId 调 Runtime.evaluate 取 #js_content 的 innerHTML
```

调用顺序：`Target.createTarget(url)` → `Target.activateTarget` → `Target.attachToTarget(flatten:true)` → `Runtime.evaluate` 取 `document.querySelector('#js_content').innerHTML`。

## 4. 前置条件与排障

- **Edge 必须已运行**且调试端口有效：`DevToolsActivePort` 文件存在 + 端口监听。文件不存在 = Edge 未启动或未开远程调试，先确认 Edge 运行状态。
- **HTTP 端点不可用是常态**：`/json/version` 返回 404 属正常（DevToolsActivePort 机制只暴露 WebSocket），不要改用 HTTP 探测。
- **消息夹带**：连接后 `ws.recv()` 可能先收到 `Target.targetCreated` 等事件消息——按第 3 节的 `id` 循环匹配处理，不要假定首条响应就是应答。
- 单 URL 重试不超过 3 次（避免触发微信风控）；内容仅供合规场景使用，遵守版权。
