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
# basic — saves to ~/.env
secret-portal

# custom env file
secret-portal -f ~/.secrets/api-keys

# custom port and timeout
secret-portal -p 8080 --timeout 600
```

the CLI will print a one-time URL with an auth token. open it in your browser, enter your secrets, and hit save. the portal auto-destructs after the first submission.

## features

- **one-time use**: portal expires after a single submission
- **token auth**: URL contains a random 32-byte token — no token, no access
- **auto-timeout**: shuts down after 5 minutes (configurable) if unused
- **merge mode**: new secrets are merged into existing env file (won't clobber)
- **file permissions**: env file is set to `600` (owner read/write only)
- **zero dependencies**: pure python stdlib

## security notes

- the portal runs over HTTP — use behind a reverse proxy or SSH tunnel for production
- the one-time token prevents unauthorized access
- secrets never touch your chat history or terminal logs
