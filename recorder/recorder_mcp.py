#!/usr/bin/env python3
"""Stdio MCP server that queries the FrameMemo iPhone app over the local network."""

import argparse
import base64
import http.server
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

CONFIG_PATH = os.path.expanduser("~/.config/recorder-mcp/config.json")
PAIR_LOCK = os.path.expanduser("~/.config/recorder-mcp/pairing.lock")
PAIR_URL = os.path.expanduser("~/.config/recorder-mcp/pairing.url")
PAIR_QR = os.path.expanduser("~/.config/recorder-mcp/pairing.png")
PAIR_TIMEOUT = 600
PROTOCOL_VERSION = "2025-06-18"

# The app is reached over the LAN, where a system HTTP proxy would answer 502.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def fetch_tools():
    return request("/tools", {}).get("tools", [])


def save_config(url, token):
    directory = os.path.dirname(CONFIG_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(CONFIG_PATH, "w") as handle:
        json.dump({"url": url.rstrip("/"), "token": token}, handle, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def lan_ip():
    for interface in ("en0", "en1"):
        try:
            value = subprocess.check_output(
                ["ipconfig", "getifaddr", interface], text=True
            ).strip()
            if value:
                return value
        except (OSError, subprocess.SubprocessError):
            pass

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def computer_name():
    try:
        value = subprocess.check_output(
            ["scutil", "--get", "ComputerName"], text=True
        ).strip()
        if value:
            return value
    except (OSError, subprocess.SubprocessError):
        pass
    return socket.gethostname()


def render_qr(payload):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pair_qr.swift")
    output = os.path.join(tempfile.mkdtemp(prefix="recorder-pair-"), "qr.png")
    candidates = [
        "/Applications/Xcode.app/Contents/Developer/usr/bin/swift",
        shutil.which("swift"),
    ]
    environment = dict(os.environ)
    environment.setdefault("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")

    for swift in candidates:
        if not swift or not os.path.exists(swift):
            continue
        try:
            result = subprocess.run(
                [swift, script, payload, output],
                env=environment,
                capture_output=True,
                timeout=90,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and os.path.exists(output):
            with open(output, "rb") as handle:
                return base64.b64encode(handle.read()).decode("ascii")
        print(result.stderr.decode("utf-8", "replace"), file=sys.stderr)

    return None


def pairing_page(payload, qr_base64, mac_name):
    qr_html = (
        '<img alt="Pairing code" width="280" height="280" '
        'src="data:image/png;base64,' + qr_base64 + '">'
        if qr_base64
        else '<p style="color:#b33">Could not draw the code here. '
        "Paste the link below into the app instead.</p>"
    )

    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pair with FrameMemo</title>
<style>
body {{ font-family: -apple-system, sans-serif; background:#f6f7f9; color:#12151a; margin:0; }}
main {{ max-width: 520px; margin: 48px auto; background:#fff; border-radius: 16px; padding: 32px; text-align:center; }}
h1 {{ font-size: 22px; margin: 0 0 8px; }}
p {{ color:#5c6470; line-height:1.5; }}
code {{ display:block; word-break:break-all; font-size:12px; background:#eef1f5; border-radius:8px; padding:12px; margin:16px 0; color:#12151a; }}
button {{ font: inherit; padding: 8px 16px; border-radius: 8px; border: 1px solid #d5d9e0; background:#fff; }}
#status {{ margin-top: 16px; font-weight: 600; }}
</style>
</head>
<body>
<main>
<h1>Pair with {mac_name}</h1>
<p>On your iPhone, open FrameMemo → Settings → Agent Access → Add computer, then scan this code.</p>
{qr}
<code id="link">{payload}</code>
<button onclick="navigator.clipboard.writeText(document.getElementById('link').textContent)">Copy link</button>
<p id="status">Waiting for the phone…</p>
</main>
<script>
async function poll() {{
  try {{
    const response = await fetch('/status');
    const data = await response.json();
    if (data.paired) {{
      document.getElementById('status').textContent = 'Paired with ' + data.name;
      return;
    }}
  }} catch (error) {{}}
  setTimeout(poll, 1000);
}}
poll();
</script>
</body>
</html>
""".format(mac_name=mac_name, qr=qr_html, payload=payload)


def run_pair(auto_open=True):
    nonce = secrets.token_urlsafe(12)
    ip = lan_ip()
    mac_name = computer_name()
    state = {"paired": None}
    values = {"payload": "", "qr": None}

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/status":
                paired = state["paired"]
                self.reply(200, {
                    "paired": paired is not None,
                    "name": (paired or {}).get("name", ""),
                })
                return
            if self.path != "/":
                self.reply(404, {"ok": False})
                return

            body = pairing_page(values["payload"], values["qr"], mac_name).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path != "/pair":
                self.reply(404, {"ok": False})
                return

            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                data = json.loads(raw.decode("utf-8"))
            except ValueError:
                self.reply(400, {"ok": False, "error": "bad_json"})
                return

            if state["paired"] is not None:
                self.reply(409, {"ok": False, "error": "already_paired"})
                return
            if data.get("nonce") != nonce:
                self.reply(403, {"ok": False, "error": "bad_nonce"})
                return

            token = str(data.get("token") or "")
            name = str(data.get("name") or "iPhone")
            try:
                port = int(data.get("port") or 0)
            except (TypeError, ValueError):
                port = 0
            if not token or not (0 < port < 65536):
                self.reply(400, {"ok": False, "error": "bad_request"})
                return

            url = "http://{}:{}".format(self.client_address[0], port)
            save_config(url, token)
            state["paired"] = {"name": name, "url": url}
            self.reply(200, {"ok": True})
            threading.Thread(target=self.stop_soon, daemon=True).start()

        def stop_soon(self):
            time.sleep(5)
            server.shutdown()

    server = http.server.ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    port = server.server_address[1]
    values["payload"] = "recorder://pair?host={}&port={}&nonce={}&name={}".format(
        ip, port, nonce, urllib.parse.quote(mac_name)
    )
    page_url = "http://127.0.0.1:{}/".format(port)
    print("Pairing page: " + page_url, file=sys.stderr)
    # Publish the page and the lock before drawing the QR: drawing shells out to
    # Swift and can take seconds, while pairing_link() only waits a few.
    try:
        os.makedirs(os.path.dirname(PAIR_URL), exist_ok=True)
        with open(PAIR_URL, "w") as handle:
            handle.write(page_url)
        with open(PAIR_LOCK, "w") as handle:
            handle.write(str(int(time.time())))
    except OSError:
        pass

    values["qr"] = render_qr(values["payload"])
    if values["qr"]:
        try:
            with open(PAIR_QR, "wb") as handle:
                handle.write(base64.b64decode(values["qr"]))
            print("QR image: " + PAIR_QR, file=sys.stderr)
        except OSError:
            pass
    if auto_open:
        threading.Thread(target=webbrowser.open, args=(page_url,), daemon=True).start()

    timer = threading.Timer(PAIR_TIMEOUT, server.shutdown)
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        for path in (PAIR_LOCK, PAIR_URL, PAIR_QR):
            try:
                os.remove(path)
            except OSError:
                pass

    if state["paired"]:
        print(
            "Paired with {}. Settings saved to {}".format(
                state["paired"]["name"], CONFIG_PATH
            ),
            file=sys.stderr,
        )
    else:
        print("Pairing timed out.", file=sys.stderr)
        sys.exit(1)


def claim_pair_lock():
    """Claim the pairing lock atomically; False when another session owns it."""

    directory = os.path.dirname(PAIR_LOCK)
    if directory:
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError:
            return False

    for _ in range(2):
        try:
            descriptor = os.open(PAIR_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(PAIR_LOCK) < PAIR_TIMEOUT + 60:
                    return False
                os.remove(PAIR_LOCK)
            except OSError:
                return False
            continue
        except OSError:
            return False
        try:
            os.write(descriptor, str(int(time.time())).encode("utf-8"))
        finally:
            os.close(descriptor)
        return True
    return False


def start_pairing(auto_open=True):
    if not claim_pair_lock():
        return False

    command = [sys.executable, os.path.abspath(__file__), "pair"]
    if not auto_open:
        command.append("--no-open")
    try:
        subprocess.Popen(
            command,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        try:
            os.remove(PAIR_LOCK)
        except OSError:
            pass
        return False
    return True


def auto_pair(force=False):
    if not force:
        try:
            load_config()
            return
        except RuntimeError:
            pass

    start_pairing()


def pairing_link():
    """Pairing page URL for the user to open themselves; never opens a browser."""

    def live():
        try:
            if time.time() - os.path.getmtime(PAIR_URL) < PAIR_TIMEOUT:
                with open(PAIR_URL) as handle:
                    return handle.read().strip() or None
        except OSError:
            pass
        return None

    link = live()
    if link:
        return link

    try:
        starting = time.time() - os.path.getmtime(PAIR_LOCK) < PAIR_TIMEOUT + 60
    except OSError:
        starting = False

    if not starting:
        start_pairing(auto_open=False)

    for _ in range(40):
        time.sleep(0.1)
        link = live()
        if link:
            return link
    return None


def qr_hint():
    return "\nQR image: {}".format(PAIR_QR) if os.path.exists(PAIR_QR) else ""


def load_config():
    url = os.environ.get("RECORDER_URL", "")
    token = os.environ.get("RECORDER_TOKEN", "")
    if not url or not token:
        try:
            with open(CONFIG_PATH, "r") as handle:
                saved = json.load(handle)
            url = url or saved.get("url", "")
            token = token or saved.get("token", "")
        except (OSError, ValueError):
            pass
    if not url or not token:
        raise RuntimeError(
            "FrameMemo is not configured. Run: python3 recorder_mcp.py set "
            "--url http://<ip>:<port> --token <token>"
        )
    return url.rstrip("/"), token


def request(path, params=None, body=None):
    base_url, token = load_config()
    values = {key: value for key, value in (params or {}).items() if value is not None}
    url = base_url + path
    if values:
        url = url + "?" + urllib.parse.urlencode(values)

    headers = {"Authorization": "Bearer " + token}
    data = None
    method = "GET"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 401:
            auto_pair(force=True)
            raise RuntimeError(
                "Not authorized. A pairing page has opened on your Mac; pair this "
                "computer again from FrameMemo > Settings > Agent Access."
            )
        raise RuntimeError("FrameMemo returned HTTP {}".format(error.code))
    except OSError as error:
        # URLError is an OSError; a peer that drops the response mid-read raises
        # ConnectionResetError, which is an OSError but not a URLError.
        reason = getattr(error, "reason", error)
        link = pairing_link()
        extra = (
            "\nIf the iPhone changed networks, open this page and scan the code "
            "from FrameMemo > Settings > Agent Access (valid for {} minutes):\n{}{}".format(
                PAIR_TIMEOUT // 60, link, qr_hint()
            )
            if link
            else "\nIf the iPhone changed networks, run `python3 {} pair`.".format(
                os.path.abspath(__file__)
            )
        )
        raise RuntimeError(
            "Cannot reach FrameMemo at {} ({}).\n"
            "Check that the iPhone is unlocked, FrameMemo is open, and that this Mac "
            "and the iPhone are on the same Wi-Fi.{}".format(
                base_url, reason, extra
            )
        )


def call_tool(name, arguments):
    if not name:
        raise RuntimeError("tool name is required")
    return request("/tools/call", body={"name": name, "arguments": arguments})


def result(request_id, payload):
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def failure(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(message):
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if method == "initialize":
        return result(request_id, {
            "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "recorder", "version": "0.1.0"},
        })

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "ping":
        return result(request_id, {})

    if method == "tools/list":
        try:
            tools = fetch_tools()
        except Exception as error:
            return failure(request_id, -32603, str(error))
        return result(request_id, {"tools": tools})

    if method == "tools/call":
        try:
            data = call_tool(params.get("name", ""), params.get("arguments") or {})
            return result(request_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps(data, ensure_ascii=False, indent=2),
                }],
                "isError": False,
            })
        except Exception as error:
            return result(request_id, {
                "content": [{"type": "text", "text": str(error)}],
                "isError": True,
            })

    return failure(request_id, -32601, "Method not found: {}".format(method))


def serve():
    auto_pair()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps(failure(None, -32700, "Parse error")) + "\n")
            sys.stdout.flush()
            continue

        response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def run_set(argv):
    parser = argparse.ArgumentParser(prog="recorder_mcp.py set")
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    save_config(args.url, args.token)


def run_status():
    try:
        base_url, _token = load_config()
    except RuntimeError:
        print("FrameMemo is not paired yet.")
        link = pairing_link()
        if link:
            print("Pair within {} minutes:".format(PAIR_TIMEOUT // 60))
            print(link)
            if os.path.exists(PAIR_QR):
                print("QR image: " + PAIR_QR)
            print(
                "On the iPhone: FrameMemo > Settings > Agent Access, turn on Allow agent access, "
                "tap Add computer and scan the page."
            )
        else:
            print("Start pairing with: python3 {} pair".format(os.path.abspath(__file__)))
        return 1

    try:
        request("/health")
    except RuntimeError as error:
        print(str(error))
        return 1
    print("FrameMemo is reachable at {}.".format(base_url))
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "set":
        run_set(sys.argv[2:])
        print("Saved " + CONFIG_PATH)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "pair":
        run_pair(auto_open="--no-open" not in sys.argv[2:])
        return
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        sys.exit(run_status())
    serve()


if __name__ == "__main__":
    main()
