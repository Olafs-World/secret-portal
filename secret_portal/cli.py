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


def generate_html(token: str, env_file: str) -> str:
    """Generate the single-page HTML UI."""
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
    <div id="entries">
      <div class="entry">
        <input type="text" class="key-input" placeholder="KEY_NAME" spellcheck="false">
        <input type="password" class="val-input" placeholder="value" spellcheck="false">
        <button class="remove-btn" onclick="removeEntry(this)" title="remove">×</button>
      </div>
    </div>
    <div class="actions">
      <button class="btn btn-secondary" onclick="addEntry()">+ add</button>
      <button class="btn btn-primary" id="submitBtn" onclick="submit()">save secrets</button>
    </div>
    <div class="status" id="status"></div>
  </div>
  <div class="meta">saving to <code>{html.escape(env_file)}</code></div>
</div>
<script>
const TOKEN = "{token}";

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
  const entries = document.querySelectorAll('.entry');
  const secrets = {{}};
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
document.querySelector('.key-input').focus();
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

        body = generate_html(self.server.token, self.server.env_file).encode()
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
        print(f"✅ saved {count} secret(s): {', '.join(keys)}", flush=True)
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

    def __init__(self, addr, handler, token: str, env_file: str):
        super().__init__(addr, handler)
        self.token = token
        self.env_file = env_file
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
    args = parser.parse_args()

    token = secrets.token_urlsafe(32)
    server = PortalServer((args.host, args.port), PortalHandler, token, args.env_file)
    port = server.server_address[1]

    # Try to detect public IP/hostname
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

    if server.saved_keys:
        print(f"\n✨ done! saved: {', '.join(server.saved_keys)}")
    else:
        print("\n🚫 no secrets were saved")

    sys.exit(0)


if __name__ == "__main__":
    main()
