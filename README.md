# 🔐 secret-portal

spin up a temporary web UI for securely entering secret keys and environment variables.

## why?

entering API keys over messaging apps (telegram, slack, etc.) is sketchy — they get logged, cached, and stored in chat history. this tool spins up a one-time-use web form that saves secrets directly to an env file on your server.

## install

```bash
uv tool install .
```

## usage

```bash
# basic — saves to ~/.env, local only
secret-portal

# expose publicly via cloudflared tunnel (recommended)
secret-portal --tunnel cloudflared

# single key mode with guided instructions
secret-portal -k OPENAI_API_KEY \
  -i '<strong>Get your key:</strong><ol><li>Go to platform.openai.com</li><li>Click API Keys</li><li>Create new key</li></ol>' \
  -l "https://platform.openai.com/api-keys" \
  --link-text "Open OpenAI dashboard →" \
  --tunnel cloudflared

# custom env file and timeout
secret-portal -f ~/.secrets/api-keys --timeout 600
```

the CLI will print a one-time URL with an auth token. open it in your browser, enter your secrets, and hit save. the portal auto-destructs after the first submission.

## tunneling

use `--tunnel` to expose the portal publicly so it's accessible from any device (phone, laptop, etc.).

| provider | flag | cost | notes |
|----------|------|------|-------|
| **cloudflared** (recommended) | `--tunnel cloudflared` | free | no account needed, no interstitial pages, HTTPS, auto-downloads if missing |
| ngrok | `--tunnel ngrok` | free (limited) | requires account + auth, free tier shows an interstitial warning page that blocks mobile/automated use |
| none | (default) | — | binds to `0.0.0.0`, requires the port to be open in your firewall/security group |

**we recommend cloudflared** — it just works. no signup, no config, no interstitial. if the binary isn't installed, secret-portal will download it automatically on first use.

## features

- **one-time use**: portal expires after a single submission
- **token auth**: URL contains a random 32-byte token — no token, no access
- **auto-timeout**: shuts down after 5 minutes (configurable) if unused
- **merge mode**: new secrets are merged into existing env file (won't clobber)
- **file permissions**: env file is set to `600` (owner read/write only)
- **zero dependencies**: pure python stdlib
- **single key mode**: pre-populate a key name so the user just pastes the value (`-k KEY_NAME`)
- **guided instructions**: add step-by-step instructions and a link to the key's console (`-i`, `-l`)
- **reachability check**: warns if the port isn't externally accessible and suggests `--tunnel cloudflared`
- **no value leakage**: secret values are never printed to stdout/stderr (tested)

## security notes

- cloudflared tunnels use HTTPS automatically
- without a tunnel, the portal runs over HTTP — use behind a reverse proxy or SSH tunnel for production
- the one-time token prevents unauthorized access
- secrets never touch your chat history or terminal logs
- secret values never appear in stdout/stderr (enforced by tests)
