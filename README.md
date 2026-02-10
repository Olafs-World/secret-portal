![secret-portal banner](https://raw.githubusercontent.com/Olafs-World/secret-portal/main/banner.png)

[![CI](https://github.com/Olafs-World/secret-portal/actions/workflows/ci.yml/badge.svg)](https://github.com/Olafs-World/secret-portal/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/secret-portal.svg)](https://pypi.org/project/secret-portal/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# 🔐 Secret Portal

Spin up a temporary web UI for securely entering secret keys and environment variables.

## Why?

Entering API keys over messaging apps (Telegram, Slack, etc.) is sketchy — they get logged, cached, and stored in chat history. This tool spins up a one-time-use web form that saves secrets directly to an env file on your server.

## Install

```bash
uv tool install secret-portal
```

Or with pip:

```bash
pip install secret-portal
```

## Usage

```bash
# Basic — saves to ~/.env, local only
secret-portal

# Expose publicly via cloudflared tunnel (recommended)
secret-portal --tunnel cloudflared

# Single key mode with guided instructions
secret-portal -k OPENAI_API_KEY \
  -i '<strong>Get your key:</strong><ol><li>Go to platform.openai.com</li><li>Click API Keys</li><li>Create new key</li></ol>' \
  -l "https://platform.openai.com/api-keys" \
  --link-text "Open OpenAI dashboard →" \
  --tunnel cloudflared

# Custom env file and timeout
secret-portal -f ~/.secrets/api-keys --timeout 600
```

The CLI will print a one-time URL with an auth token. Open it in your browser, enter your secrets, and hit save. The portal auto-destructs after the first submission.

## Tunneling

Use `--tunnel` to expose the portal publicly so it's accessible from any device (phone, laptop, etc.).

| Provider | Flag | Cost | Notes |
|----------|------|------|-------|
| **Cloudflared** (recommended) | `--tunnel cloudflared` | Free | No account needed, no interstitial pages, HTTPS, auto-downloads if missing |
| ngrok | `--tunnel ngrok` | Free (limited) | Requires account + auth, free tier shows an interstitial warning page that blocks mobile/automated use |
| None | (default) | — | Binds to `0.0.0.0`, requires the port to be open in your firewall/security group |

**We recommend Cloudflared** — it just works. No signup, no config, no interstitial. If the binary isn't installed, Secret Portal will download it automatically on first use.

## Features

- **One-time use**: Portal expires after a single submission
- **Token auth**: URL contains a random 32-byte token — no token, no access
- **Auto-timeout**: Shuts down after 5 minutes (configurable) if unused
- **Merge mode**: New secrets are merged into existing env file (won't clobber)
- **File permissions**: Env file is set to `600` (owner read/write only)
- **Zero dependencies**: Pure Python stdlib
- **Single key mode**: Pre-populate a key name so the user just pastes the value (`-k KEY_NAME`)
- **Guided instructions**: Add step-by-step instructions and a link to the key's console (`-i`, `-l`)
- **Reachability check**: Warns if the port isn't externally accessible and suggests `--tunnel cloudflared`
- **No value leakage**: Secret values are never printed to stdout/stderr (tested)

## Security Notes

- Cloudflared tunnels use HTTPS automatically
- Without a tunnel, the portal runs over HTTP — use behind a reverse proxy or SSH tunnel for production
- The one-time token prevents unauthorized access
- Secrets never touch your chat history or terminal logs
- Secret values never appear in stdout/stderr (enforced by tests)

## Links

- [PyPI](https://pypi.org/project/secret-portal/)
- [GitHub](https://github.com/Olafs-World/secret-portal)

## License

MIT © [Olaf](https://olafs-world.vercel.app)
