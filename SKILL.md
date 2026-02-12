---
name: secret-portal
description: Spin up a temporary one-time web UI for securely entering secret keys, API tokens, and environment variables. Use when you need to collect sensitive credentials over chat without exposing them in logs. Keywords - secret, API key, token, credentials, environment variables, env file, secure input, tunnel, cloudflared
license: MIT
metadata:
  author: Olafs-World
  version: "0.1.0"
---

# Secret Portal

Spin up a temporary web UI for securely entering secret keys and environment variables without exposing them in chat logs.

## Requirements

- Python 3.10+
- Optional: cloudflared (auto-downloaded) or ngrok for public tunneling

## Quick Usage

```bash
# Basic — saves to ~/.env, local only
secret-portal

# Recommended — expose via cloudflared tunnel
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

## Key Options

| Option | Description |
|--------|-------------|
| `-k, --key KEY` | Pre-populate a single key name (user just pastes value) |
| `-f, --file PATH` | Path to env file (default: `~/.env`) |
| `-i, --instructions HTML` | Step-by-step HTML instructions for obtaining the key |
| `-l, --link URL` | Link to key management console |
| `--link-text TEXT` | Custom link button text |
| `--tunnel {cloudflared,ngrok}` | Expose publicly via tunnel provider |
| `--timeout SECONDS` | Auto-shutdown timeout (default: 300) |

## Security Features

- **One-time use**: Portal expires after first submission
- **Token auth**: 32-byte random token required in URL
- **Auto-timeout**: Shuts down after 5 minutes if unused
- **File permissions**: Env file set to 600 (owner read/write only)
- **Merge mode**: New secrets merged into existing file without clobbering
- **No value leakage**: Secret values never printed to stdout/stderr

## Tunneling

Use `--tunnel cloudflared` (recommended) for public access from any device:
- No account required
- HTTPS automatic
- No interstitial pages
- Auto-downloads binary if missing

## Tips

- Use single key mode (`-k`) for better UX when collecting one specific credential
- Cloudflared tunnel recommended over ngrok (no signup, no interstitial warning)
- Without tunnel, requires port to be open in firewall/security group
- Portal auto-destructs after first use — safe for sharing the URL once
- Values never appear in terminal logs or chat history

## When to Use

- Collecting API keys from users over chat (Telegram, Slack, Discord)
- Avoiding credential leakage in message logs
- Remote credential setup without SSH or terminal access
- Secure onboarding flows requiring sensitive input
