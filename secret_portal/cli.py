"""secret-portal: temporary web UI for securely entering secret keys."""

from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import signal
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def generate_html(
    token: str,
    env_file: str,
    key_name: str | None = None,
    instructions: str | None = None,
    link: str | None = None,
    link_text: str = "Open console →",
) -> str:
    """Generate the single-page HTML UI."""
    single_key = key_name is not None
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔐 Secret Portal</title>
<style>
  :root {{
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --green: #3fb950;
    --red: #f85149;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }}
  .container {{
    max-width: 560px;
    width: 100%;
  }}
  .header {{
    text-align: center;
    margin-bottom: 2rem;
  }}
  .header h1 {{
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }}
  .header p {{
    color: var(--muted);
    font-size: 0.875rem;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
  }}
  .entry {{
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    align-items: center;
  }}
  .entry input {{
    flex: 1;
    padding: 0.6rem 0.75rem;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 0.875rem;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }}
  .entry input:focus {{
    outline: none;
    border-color: var(--accent);
  }}
  .entry input.key-input {{
    flex: 0.8;
    text-transform: uppercase;
  }}
  .entry input.val-input {{
    flex: 1.2;
  }}
  .entry .remove-btn {{
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 1.2rem;
    padding: 0.25rem;
    border-radius: 4px;
    line-height: 1;
  }}
  .entry .remove-btn:hover {{ color: var(--red); }}
  .actions {{
    display: flex;
    gap: 0.75rem;
    margin-top: 1.25rem;
  }}
  .btn {{
    padding: 0.6rem 1.25rem;
    border: none;
    border-radius: 8px;
    font-size: 0.875rem;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.15s;
  }}
  .btn-primary {{
    background: var(--accent);
    color: var(--bg);
    flex: 1;
  }}
  .btn-primary:hover {{ background: var(--accent-hover); }}
  .btn-secondary {{
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
  }}
  .btn-secondary:hover {{ border-color: var(--muted); }}
  .btn:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
  }}
  .status {{
    text-align: center;
    margin-top: 1.25rem;
    padding: 0.75rem;
    border-radius: 8px;
    font-size: 0.875rem;
    display: none;
  }}
  .status.success {{
    display: block;
    background: rgba(63, 185, 80, 0.1);
    color: var(--green);
    border: 1px solid rgba(63, 185, 80, 0.2);
  }}
  .status.error {{
    display: block;
    background: rgba(248, 81, 73, 0.1);
    color: var(--red);
    border: 1px solid rgba(248, 81, 73, 0.2);
  }}
  .meta {{
    text-align: center;
    margin-top: 1.5rem;
    color: var(--muted);
    font-size: 0.75rem;
  }}
  .guide {{
    background: rgba(88, 166, 255, 0.05);
    border: 1px solid rgba(88, 166, 255, 0.15);
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    font-size: 0.875rem;
    line-height: 1.7;
    color: var(--muted);
  }}
  .guide ol, .guide ul {{
    padding-left: 1.25rem;
    margin: 0.5rem 0;
  }}
  .guide li {{
    margin-bottom: 0.35rem;
  }}
  .guide strong {{
    color: var(--text);
  }}
  .guide code {{
    background: var(--bg);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.8rem;
    color: var(--accent);
  }}
  .guide a {{
    color: var(--accent);
    text-decoration: none;
  }}
  .guide a:hover {{
    text-decoration: underline;
  }}
  .guide-link {{
    display: inline-block;
    margin-top: 0.75rem;
    padding: 0.5rem 1rem;
    background: rgba(88, 166, 255, 0.1);
    border: 1px solid rgba(88, 166, 255, 0.25);
    border-radius: 8px;
    color: var(--accent);
    text-decoration: none;
    font-weight: 500;
    font-size: 0.85rem;
    transition: all 0.15s;
  }}
  .guide-link:hover {{
    background: rgba(88, 166, 255, 0.2);
    text-decoration: none;
  }}
  .single-entry {{
    text-align: center;
  }}
  .key-label {{
    display: block;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 0.75rem;
    letter-spacing: 0.5px;
  }}
  .single-entry .val-input {{
    width: 100%;
    padding: 0.75rem;
    font-size: 1rem;
    text-align: center;
  }}
  .meta code {{
    background: var(--surface);
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    font-size: 0.7rem;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🔐 secret portal</h1>
    <p>enter secrets below. they'll be saved server-side.<br>this page expires after one submission.</p>
  </div>
  <div class="card">
    {"" if not instructions and not link else '<div class="guide">' + (instructions or "") + ("" if not link else f'<br><a class="guide-link" href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(link_text)}</a>') + '</div>'}
    <div id="entries">
      {"" if single_key else """<div class="entry">
        <input type="text" class="key-input" placeholder="KEY_NAME" spellcheck="false">
        <input type="password" class="val-input" placeholder="value" spellcheck="false">
        <button class="remove-btn" onclick="removeEntry(this)" title="remove">×</button>
      </div>"""}
      {"" if not single_key else f"""<div class="single-entry">
        <label class="key-label">{html.escape(key_name or "")}</label>
        <input type="password" class="val-input" id="single-val" placeholder="paste your secret here" spellcheck="false" autocomplete="off">
      </div>"""}
    </div>
    <div class="actions">
      {"" if single_key else '<button class="btn btn-secondary" onclick="addEntry()">+ add</button>'}
      <button class="btn btn-primary" id="submitBtn" onclick="submit()">{"save" if single_key else "save secrets"}</button>
    </div>
    <div class="status" id="status"></div>
  </div>
  <div class="meta">saving to <code>{html.escape(env_file)}</code></div>
</div>
<script>
const TOKEN = "{token}";
const SINGLE_KEY = {"'" + html.escape(key_name or "") + "'" if single_key else "null"};

function addEntry() {{
  const div = document.createElement('div');
  div.className = 'entry';
  div.innerHTML = `
    <input type="text" class="key-input" placeholder="KEY_NAME" spellcheck="false">
    <input type="password" class="val-input" placeholder="value" spellcheck="false">
    <button class="remove-btn" onclick="removeEntry(this)" title="remove">×</button>
  `;
  document.getElementById('entries').appendChild(div);
  div.querySelector('.key-input').focus();
}}

function removeEntry(btn) {{
  const entries = document.querySelectorAll('.entry');
  if (entries.length > 1) btn.parentElement.remove();
}}

async function submit() {{
  const secrets = {{}};

  if (SINGLE_KEY) {{
    const v = document.getElementById('single-val').value;
    if (!v) {{
      showStatus('please enter the secret value', 'error');
      return;
    }}
    secrets[SINGLE_KEY] = v;
  }} else {{
    const entries = document.querySelectorAll('.entry');
    let valid = true;
    entries.forEach(e => {{
      const k = e.querySelector('.key-input').value.trim();
      const v = e.querySelector('.val-input').value;
      if (k && v) secrets[k] = v;
      else if (k || v) valid = false;
    }});
    if (!valid || Object.keys(secrets).length === 0) {{
      showStatus('enter at least one complete key-value pair', 'error');
      return;
    }}
  }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'saving...';

  try {{
    const res = await fetch('/save', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Token': TOKEN }},
      body: JSON.stringify(secrets)
    }});
    const data = await res.json();
    if (data.ok) {{
      showStatus(`saved ${{data.count}} secret(s). this portal is now closed.`, 'success');
      btn.textContent = 'done ✓';
      document.querySelectorAll('input').forEach(i => i.disabled = true);
    }} else {{
      showStatus(data.error || 'something went wrong', 'error');
      btn.disabled = false;
      btn.textContent = 'save secrets';
    }}
  }} catch (e) {{
    showStatus('connection failed — server may have shut down', 'error');
    btn.disabled = false;
    btn.textContent = 'save secrets';
  }}
}}

function showStatus(msg, type) {{
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status ' + type;
}}

// focus first input
(document.getElementById('single-val') || document.querySelector('.key-input')).focus();
</script>
</body>
</html>"""


class PortalHandler(BaseHTTPRequestHandler):
    """HTTP handler for the secret portal."""

    server: "PortalServer"

    def log_message(self, fmt, *args):
        # suppress default logging
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        provided = params.get("t", [None])[0]

        if parsed.path != "/" or provided != self.server.token:
            self.send_response(403)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h3>invalid or expired link</h3>")
            return

        if self.server.used:
            self.send_response(410)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h3>this portal has already been used</h3>")
            return

        body = generate_html(
            self.server.token, self.server.env_file, self.server.key_name,
            self.server.instructions, self.server.link, self.server.link_text,
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/save":
            self.send_response(404)
            self.end_headers()
            return

        provided = self.headers.get("X-Token", "")
        if provided != self.server.token or self.server.used:
            self._json_response(403, {"ok": False, "error": "invalid or expired"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            self._json_response(400, {"ok": False, "error": "invalid JSON"})
            return

        if not isinstance(data, dict) or not data:
            self._json_response(400, {"ok": False, "error": "no secrets provided"})
            return

        # Write to env file
        env_path = Path(self.server.env_file).expanduser()
        env_path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing content
        existing = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    existing[k.strip()] = v.strip()

        # Merge new secrets
        existing.update(data)

        # Write back
        lines = [f"{k}={v}" for k, v in sorted(existing.items())]
        env_path.write_text("\n".join(lines) + "\n")
        env_path.chmod(0o600)

        self.server.used = True
        count = len(data)
        keys = list(data.keys())
        self.server.saved_keys = keys
        print(f"✅ saved {count} secret(s)", flush=True)
        print(f"   → {env_path}", flush=True)

        self._json_response(200, {"ok": True, "count": count})

        # Schedule shutdown
        threading.Timer(1.0, self.server.shutdown).start()

    def _json_response(self, code: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class PortalServer(HTTPServer):
    """Extended HTTPServer with portal state."""

    def __init__(self, addr, handler, token: str, env_file: str, key_name: str | None = None,
                 instructions: str | None = None, link: str | None = None, link_text: str = "Open console →"):
        super().__init__(addr, handler)
        self.token = token
        self.env_file = env_file
        self.key_name = key_name
        self.instructions = instructions
        self.link = link
        self.link_text = link_text
        self.used = False
        self.saved_keys: list[str] = []


def main():
    parser = argparse.ArgumentParser(
        description="Spin up a temporary web portal for entering secrets"
    )
    parser.add_argument(
        "-f", "--env-file",
        default="~/.env",
        help="Path to env file to save secrets to (default: ~/.env)",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=0,
        help="Port to listen on (default: random available port)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Auto-shutdown after N seconds with no submission (default: 300)",
    )
    parser.add_argument(
        "-k", "--key",
        default=None,
        help="Pre-populate a single key name (user only needs to enter the value)",
    )
    parser.add_argument(
        "-i", "--instructions",
        default=None,
        help="Instructions/guide text shown above the input (supports basic HTML)",
    )
    parser.add_argument(
        "-l", "--link",
        default=None,
        help="URL where the user can get/create the key (shown as a button)",
    )
    parser.add_argument(
        "--link-text",
        default="Open console →",
        help="Label for the link button (default: 'Open console →')",
    )
    parser.add_argument(
        "--tunnel",
        choices=["ngrok", "cloudflared", "none"],
        default="none",
        help="Tunnel provider to expose the portal publicly (default: none). "
             "cloudflared is recommended — it's free, has no interstitial pages, "
             "and auto-downloads if missing. ngrok free tier shows a warning page "
             "that blocks automated/mobile use.",
    )
    args = parser.parse_args()

    token = secrets.token_urlsafe(32)
    server = PortalServer(
        (args.host, args.port), PortalHandler, token, args.env_file,
        args.key, args.instructions, args.link, args.link_text,
    )
    port = server.server_address[1]

    # Determine public URL
    tunnel_process = None
    if args.tunnel == "ngrok":
        import subprocess, time as _time
        tunnel_process = subprocess.Popen(
            ["ngrok", "http", str(port), "--log", "stdout", "--log-format", "json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        public_url = None
        deadline = _time.time() + 10
        while _time.time() < deadline:
            try:
                import urllib.request
                resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2)
                tunnels = json.loads(resp.read())
                for t in tunnels.get("tunnels", []):
                    if t.get("public_url", "").startswith("https://"):
                        public_url = t["public_url"]
                        break
                if public_url:
                    break
            except Exception:
                pass
            _time.sleep(0.5)
        if not public_url:
            print("❌ failed to start ngrok tunnel", flush=True)
            tunnel_process.kill()
            sys.exit(1)
        url = f"{public_url}/?t={token}"

    elif args.tunnel == "cloudflared":
        import subprocess, time as _time, re as _re
        cf_bin = "cloudflared"
        # check common locations
        for candidate in ["cloudflared", os.path.expanduser("~/cloudflared")]:
            if os.path.isfile(candidate) or os.system(f"which {candidate} >/dev/null 2>&1") == 0:
                cf_bin = candidate
                break
        tunnel_process = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        public_url = None
        deadline = _time.time() + 15
        while _time.time() < deadline:
            # cloudflared prints URL to stderr
            import select
            if select.select([tunnel_process.stderr], [], [], 0.5)[0]:
                line = tunnel_process.stderr.readline().decode(errors="ignore")
                m = _re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
                if m:
                    public_url = m.group(1)
                    break
        if not public_url:
            print("❌ failed to start cloudflared tunnel", flush=True)
            tunnel_process.kill()
            sys.exit(1)
        url = f"{public_url}/?t={token}"

    else:
        hostname = os.environ.get("PORTAL_HOST", "")
        if not hostname:
            try:
                import urllib.request
                hostname = urllib.request.urlopen(
                    "http://checkip.amazonaws.com", timeout=2
                ).read().decode().strip()
            except Exception:
                hostname = "localhost"

        if ":" not in hostname:
            hostname = f"{hostname}:{port}"

        url = f"http://{hostname}/?t={token}"

    # Self-check: verify the portal is reachable if no tunnel
    if args.tunnel == "none":
        try:
            import urllib.request
            ext_url = f"http://{hostname}/"
            urllib.request.urlopen(ext_url, timeout=3)
        except urllib.error.HTTPError:
            pass  # 403 = reachable, just no token
        except Exception:
            print(f"⚠️  WARNING: port {port} may not be reachable from the internet.", flush=True)
            print(f"   the server is running locally but external connections will likely fail.", flush=True)
            print(f"   fix: use --tunnel cloudflared (recommended) or open port {port} in your firewall/security group.", flush=True)
            print(f"", flush=True)

    print(f"🔐 secret portal is live!", flush=True)
    print(f"   url: {url}", flush=True)
    print(f"   saving to: {args.env_file}", flush=True)
    print(f"   expires: after first submission or {args.timeout}s timeout", flush=True)
    print(f"   waiting for secrets...", flush=True)

    # Timeout timer
    def timeout_shutdown():
        if not server.used:
            print(f"\n⏰ timed out after {args.timeout}s with no submission")
            server.shutdown()

    timer = threading.Timer(args.timeout, timeout_shutdown)
    timer.daemon = True
    timer.start()

    # Handle Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: (print("\n👋 shutting down"), server.shutdown()))

    try:
        server.serve_forever()
    finally:
        timer.cancel()

    if tunnel_process:
        tunnel_process.kill()
        tunnel_process.wait()

    if server.saved_keys:
        print(f"\n✨ done! saved {len(server.saved_keys)} secret(s)")
    else:
        print("\n🚫 no secrets were saved")

    sys.exit(0)


if __name__ == "__main__":
    main()
