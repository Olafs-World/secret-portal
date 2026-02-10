"""Tests that secret values are NEVER exposed in stdout, stderr, or logs."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

PORTAL_CMD = [sys.executable, "-m", "secret_portal.cli"]
SECRET_VALUE = "super_secret_value_DEADBEEF_1234567890"
ANOTHER_SECRET = "xK9#mP2$vL7@nQ4&wR8"
KEY_NAME = "TEST_API_KEY"


def wait_for_server(port: int, timeout: float = 10) -> None:
    """Wait for the server to start listening."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=1)
        except urllib.error.HTTPError:
            return  # 403 = server is up
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"Server didn't start on port {port}")


def submit_secret(port: int, token: str, key: str, value: str) -> dict:
    """Submit a secret to the portal."""
    data = json.dumps({key: value}).encode()
    req = urllib.request.Request(
        f"http://localhost:{port}/save",
        data=data,
        headers={"Content-Type": "application/json", "X-Token": token},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=5)
    return json.loads(resp.read())


def extract_token_from_output(output: str) -> str:
    """Extract the auth token from the portal's startup output."""
    for line in output.splitlines():
        if "?t=" in line:
            return line.split("?t=")[1].strip()
    raise ValueError(f"Could not find token in output: {output}")


class TestNoSecretLeakage:
    """Ensure secret values never appear in any output."""

    def test_single_key_value_not_in_stdout(self, tmp_path: Path):
        """Submit a single secret and verify its VALUE never appears in stdout/stderr."""
        env_file = tmp_path / "secrets.env"
        port = 19876

        proc = subprocess.Popen(
            PORTAL_CMD + ["-f", str(env_file), "-k", KEY_NAME, "-p", str(port), "--timeout", "30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            wait_for_server(port)

            # Read partial stdout to get token
            time.sleep(1)
            # We need to get the token — read from the process
            # Use a non-blocking approach: hit the server to find out
            # Actually, let's parse the startup output by reading stderr too
            import select
            import io

            # Give it a moment to print startup
            time.sleep(0.5)

            # We'll get the token by trying a request and checking the startup output
            # Alternative: read the env file path from /proc or just try common approach
            # Simplest: use a known token by reading from output after process ends
            # But we need the token before submitting...

            # Let's use a different approach: read stdout lines until we find the URL
            import threading
            output_lines = []

            def reader(pipe, lines):
                for line in pipe:
                    lines.append(line)

            t = threading.Thread(target=reader, args=(proc.stdout, output_lines))
            t.daemon = True
            t.start()

            deadline = time.time() + 5
            token = None
            while time.time() < deadline:
                for line in output_lines:
                    if "?t=" in line:
                        token = line.split("?t=")[1].strip()
                        break
                if token:
                    break
                time.sleep(0.2)

            assert token, f"Could not find token in output: {output_lines}"

            # Submit the secret
            result = submit_secret(port, token, KEY_NAME, SECRET_VALUE)
            assert result["ok"] is True

            # Wait for server to shut down
            proc.wait(timeout=10)

            # Collect all output
            t.join(timeout=2)
            all_stdout = "".join(output_lines)
            all_stderr = proc.stderr.read()

            # THE CRITICAL ASSERTIONS
            assert SECRET_VALUE not in all_stdout, \
                f"SECRET VALUE LEAKED IN STDOUT: {all_stdout}"
            assert SECRET_VALUE not in all_stderr, \
                f"SECRET VALUE LEAKED IN STDERR: {all_stderr}"

            # Key name IS allowed in output
            # (we don't assert it's there, just that the value isn't)

            # Verify the file was written correctly
            assert env_file.exists()
            content = env_file.read_text()
            assert f"{KEY_NAME}={SECRET_VALUE}" in content

        finally:
            proc.kill()
            proc.wait()

    def test_multi_key_values_not_in_stdout(self, tmp_path: Path):
        """Submit multiple secrets and verify NONE of their values appear in output."""
        env_file = tmp_path / "secrets.env"
        port = 19877

        proc = subprocess.Popen(
            PORTAL_CMD + ["-f", str(env_file), "-p", str(port), "--timeout", "30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            wait_for_server(port)
            time.sleep(0.5)

            import threading
            output_lines = []

            def reader(pipe, lines):
                for line in pipe:
                    lines.append(line)

            t = threading.Thread(target=reader, args=(proc.stdout, output_lines))
            t.daemon = True
            t.start()

            deadline = time.time() + 5
            token = None
            while time.time() < deadline:
                for line in output_lines:
                    if "?t=" in line:
                        token = line.split("?t=")[1].strip()
                        break
                if token:
                    break
                time.sleep(0.2)

            assert token, f"Could not find token in output: {output_lines}"

            secrets = {
                "API_KEY": SECRET_VALUE,
                "DB_PASSWORD": ANOTHER_SECRET,
                "WEBHOOK_TOKEN": "whk_live_abc123def456",
            }

            # Submit all secrets
            data = json.dumps(secrets).encode()
            req = urllib.request.Request(
                f"http://localhost:{port}/save",
                data=data,
                headers={"Content-Type": "application/json", "X-Token": token},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=5)
            result = json.loads(resp.read())
            assert result["ok"] is True
            assert result["count"] == 3

            proc.wait(timeout=10)
            t.join(timeout=2)
            all_stdout = "".join(output_lines)
            all_stderr = proc.stderr.read()

            # Assert NO secret value appears anywhere
            for key, value in secrets.items():
                assert value not in all_stdout, \
                    f"SECRET VALUE FOR {key} LEAKED IN STDOUT"
                assert value not in all_stderr, \
                    f"SECRET VALUE FOR {key} LEAKED IN STDERR"

        finally:
            proc.kill()
            proc.wait()

    def test_value_not_in_file_path_or_url(self, tmp_path: Path):
        """Verify secret values don't end up in URLs or file paths."""
        env_file = tmp_path / "secrets.env"
        port = 19878

        proc = subprocess.Popen(
            PORTAL_CMD + ["-f", str(env_file), "-k", KEY_NAME, "-p", str(port), "--timeout", "30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            wait_for_server(port)
            time.sleep(0.5)

            import threading
            output_lines = []

            def reader(pipe, lines):
                for line in pipe:
                    lines.append(line)

            t = threading.Thread(target=reader, args=(proc.stdout, output_lines))
            t.daemon = True
            t.start()

            deadline = time.time() + 5
            token = None
            while time.time() < deadline:
                for line in output_lines:
                    if "?t=" in line:
                        token = line.split("?t=")[1].strip()
                        break
                if token:
                    break
                time.sleep(0.2)

            assert token

            result = submit_secret(port, token, KEY_NAME, SECRET_VALUE)
            assert result["ok"]

            proc.wait(timeout=10)
            t.join(timeout=2)
            all_output = "".join(output_lines) + (proc.stderr.read() or "")

            # Check that the value doesn't appear URL-encoded either
            import urllib.parse
            encoded_value = urllib.parse.quote(SECRET_VALUE)
            assert encoded_value not in all_output, \
                "SECRET VALUE (URL-ENCODED) LEAKED IN OUTPUT"

        finally:
            proc.kill()
            proc.wait()

    def test_rejected_submission_no_leak(self, tmp_path: Path):
        """Verify that even failed submissions don't leak values in output."""
        env_file = tmp_path / "secrets.env"
        port = 19879

        proc = subprocess.Popen(
            PORTAL_CMD + ["-f", str(env_file), "-k", KEY_NAME, "-p", str(port), "--timeout", "10"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            wait_for_server(port)
            time.sleep(0.5)

            # Submit with WRONG token — should be rejected
            try:
                data = json.dumps({KEY_NAME: SECRET_VALUE}).encode()
                req = urllib.request.Request(
                    f"http://localhost:{port}/save",
                    data=data,
                    headers={"Content-Type": "application/json", "X-Token": "wrong_token"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
            except urllib.error.HTTPError:
                pass  # expected 403

            proc.wait(timeout=15)

            all_stdout = proc.stdout.read()
            all_stderr = proc.stderr.read()

            assert SECRET_VALUE not in all_stdout, \
                "SECRET VALUE LEAKED IN STDOUT ON REJECTED SUBMISSION"
            assert SECRET_VALUE not in all_stderr, \
                "SECRET VALUE LEAKED IN STDERR ON REJECTED SUBMISSION"

        finally:
            proc.kill()
            proc.wait()
