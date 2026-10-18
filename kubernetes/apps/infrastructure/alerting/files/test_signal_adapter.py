"""Offline tests for signal_adapter.py (stdlib only, no network beyond 127.0.0.1).

Run from the repo root:
    python3 -I -m unittest discover -s kubernetes/apps/infrastructure/alerting/files -v
"""

import dataclasses
import http.client
import importlib.util
import json
import os
import pathlib
import re
import select
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
import unittest.mock
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
ADAPTER_PATH = HERE / "signal_adapter.py"


def _load_adapter(register=True):
    # Import by path: `python3 -I` keeps the script dir off sys.path.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("signal_adapter", ADAPTER_PATH)
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules["signal_adapter"] = module
    spec.loader.exec_module(module)
    return module


adapter = _load_adapter()

NUMBER = "+15550000001"
RECIPIENT = "group.dGVzdGdyb3VwaWQ="


def _alert(status="firing", **labels):
    labels.setdefault("alertname", "TargetDown")
    return {
        "status": status,
        "labels": labels,
        "annotations": {},
        "startsAt": "2026-10-18T10:00:00Z",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "http://prometheus/graph",
        "fingerprint": "abc123",
    }


def _payload(status, alerts, group_labels=None):
    return {
        "version": "4",
        "groupKey": '{}:{alertname="TargetDown"}',
        "truncatedAlerts": 0,
        "status": status,
        "receiver": "signal",
        "groupLabels": (
            group_labels
            if group_labels is not None
            else {"alertname": "TargetDown", "namespace": "monitoring"}
        ),
        "commonLabels": {"alertname": "TargetDown"},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager:9093",
        "alerts": alerts,
    }


class FormatMessageTest(unittest.TestCase):
    def test_firing_header_counts_firing_alerts_and_lists_each(self):
        a1 = _alert(namespace="monitoring", severity="critical", job="node")
        a1["annotations"] = {
            "summary": "Node exporter down",
            "description": "Target 10.0.0.5 unreachable",
        }
        a2 = _alert(namespace="monitoring", severity="warning")
        a2["annotations"] = {"description": "Only a description"}
        msg = adapter.format_message(_payload("firing", [a1, a2]), 2000)
        self.assertEqual(
            msg,
            "[FIRING:2] TargetDown (monitoring)\n"
            "- TargetDown [critical] monitoring: Node exporter down\n"
            "  Target 10.0.0.5 unreachable\n"
            "- TargetDown [warning] monitoring: Only a description",
        )

    def test_resolved_header(self):
        a = _alert(status="resolved", namespace="seafile", severity="critical")
        a["annotations"] = {"summary": "Back up"}
        msg = adapter.format_message(
            _payload(
                "resolved", [a], {"alertname": "TargetDown", "namespace": "seafile"}
            ),
            2000,
        )
        self.assertEqual(
            msg,
            "[RESOLVED] TargetDown (seafile)\n- TargetDown [critical] seafile: Back up",
        )

    def test_mixed_group_marks_resolved_alerts(self):
        firing = _alert(namespace="ns")
        resolved = _alert(status="resolved", namespace="ns")
        msg = adapter.format_message(
            _payload("firing", [firing, resolved], {"alertname": "TargetDown"}), 2000
        )
        self.assertEqual(
            msg,
            "[FIRING:1] TargetDown\n- TargetDown ns\n- RESOLVED TargetDown ns",
        )

    def test_missing_optional_labels(self):
        a = {"status": "firing", "labels": {}, "annotations": {}}
        payload = _payload("firing", [a], {})
        payload["commonLabels"] = {}
        msg = adapter.format_message(payload, 2000)
        self.assertEqual(msg, "[FIRING:1] alert\n- alert")

    def test_truncated_to_cap(self):
        alerts = []
        for i in range(50):
            a = _alert(namespace="ns")
            a["annotations"] = {"summary": "x" * 100 + str(i)}
            alerts.append(a)
        msg = adapter.format_message(_payload("firing", alerts), 300)
        self.assertEqual(len(msg), 300)
        self.assertTrue(msg.startswith("[FIRING:50] TargetDown (monitoring)\n"))
        self.assertTrue(msg.endswith("…"))

    def test_truncated_alerts_counted(self):
        firing = _payload("firing", [_alert(namespace="ns"), _alert(namespace="ns")])
        firing["truncatedAlerts"] = 3
        self.assertEqual(
            adapter.format_message(firing, 2000),
            "[FIRING:5] TargetDown (monitoring)\n"
            "- TargetDown ns\n- TargetDown ns\n+3 more",
        )
        resolved = _payload("resolved", [_alert(status="resolved")])
        resolved["truncatedAlerts"] = 1
        self.assertEqual(
            adapter.format_message(resolved, 2000),
            "[RESOLVED] TargetDown (monitoring)\n- TargetDown\n+1 more",
        )


class LoadConfigTest(unittest.TestCase):
    def test_defaults(self):
        cfg = adapter.load_config({"NUMBER": NUMBER, "RECIPIENT": RECIPIENT})
        self.assertEqual(cfg.signal_api_url, "http://signal-cli.alerting.svc:8080")
        self.assertEqual(cfg.listen_port, 8080)
        self.assertEqual(cfg.number, NUMBER)
        self.assertEqual(cfg.recipient, RECIPIENT)
        self.assertGreater(cfg.max_message_chars, 0)

    def test_overrides(self):
        cfg = adapter.load_config(
            {
                "NUMBER": NUMBER,
                "RECIPIENT": RECIPIENT,
                "SIGNAL_API_URL": "http://127.0.0.1:9/",
                "LISTEN_PORT": "9000",
                "MAX_MESSAGE_CHARS": "500",
            }
        )
        self.assertEqual(cfg.signal_api_url, "http://127.0.0.1:9")
        self.assertEqual(cfg.listen_port, 9000)
        self.assertEqual(cfg.max_message_chars, 500)

    def test_missing_required(self):
        for env in (
            {},
            {"NUMBER": NUMBER},
            {"RECIPIENT": RECIPIENT},
            {"NUMBER": " ", "RECIPIENT": RECIPIENT},
        ):
            with self.subTest(env=sorted(env)), self.assertRaises(adapter.ConfigError):
                adapter.load_config(env)

    def test_invalid_values(self):
        base = {"NUMBER": NUMBER, "RECIPIENT": RECIPIENT}
        for extra in (
            {"LISTEN_PORT": "abc"},
            {"LISTEN_PORT": "70000"},
            {"MAX_MESSAGE_CHARS": "0"},
            {"MAX_MESSAGE_CHARS": "lots"},
            {"SIGNAL_API_URL": "file:///etc/passwd"},
            {"SIGNAL_API_URL": "http://127.0.0.1:abc"},
            {"SIGNAL_API_URL": "http://127.0.0.1:99999"},
            {"SIGNAL_API_URL": "http://:8080"},
        ):
            with self.subTest(extra=extra), self.assertRaises(adapter.ConfigError):
                adapter.load_config({**base, **extra})


class FakeSignal:
    """signal-cli-rest-api stand-in: records /v2/send bodies, answers with `status`."""

    def __init__(self):
        self.status = 201
        self.location = None
        self.delay = 0.0
        self.requests = []
        self.closed = False
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                fake.requests.append(
                    (self.path, self.headers.get("Content-Type"), body)
                )
                if fake.delay:
                    time.sleep(fake.delay)
                self.send_response(fake.status)
                if fake.location:
                    self.send_header("Location", fake.location)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"timestamp":"1"}')

            do_GET = do_POST  # a followed redirect would arrive as a GET

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        self.thread.start()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.server.shutdown()
        self.server.server_close()


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.signal = FakeSignal()
        self.addCleanup(self.signal.close)
        self.config = adapter.Config(
            signal_api_url=self.signal.url,
            number=NUMBER,
            recipient=RECIPIENT,
            listen_port=0,
            max_message_chars=2000,
            send_timeout=0.5,
        )
        self.server = adapter.make_server(self.config, host="127.0.0.1")
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        # The tests talk to 127.0.0.1 only; never through a proxy from the environment.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, method, path, body=None, headers=None):
        req = urllib.request.Request(
            self.base + path, data=body, method=method, headers=headers or {}
        )
        try:
            with self.opener.open(req, timeout=5) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as err:
            return err.code, err.read()

    def post_alert(self, payload):
        return self.request(
            "POST",
            "/alert",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
        )

    def test_healthz(self):
        status, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"ok\n")

    def test_firing_alert_sent_to_signal(self):
        status, _ = self.post_alert(
            _payload("firing", [_alert(namespace="monitoring")])
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(self.signal.requests), 1)
        path, ctype, body = self.signal.requests[0]
        self.assertEqual(path, "/v2/send")
        self.assertEqual(ctype, "application/json")
        sent = json.loads(body)
        self.assertEqual(set(sent), {"message", "number", "recipients"})
        self.assertEqual(sent["number"], NUMBER)
        self.assertEqual(sent["recipients"], [RECIPIENT])
        self.assertEqual(
            sent["message"],
            "[FIRING:1] TargetDown (monitoring)\n- TargetDown monitoring",
        )

    def test_resolved_alert_sent_to_signal(self):
        status, _ = self.post_alert(
            _payload("resolved", [_alert(status="resolved", namespace="monitoring")])
        )
        self.assertEqual(status, 200)
        sent = json.loads(self.signal.requests[0][2])
        self.assertTrue(sent["message"].startswith("[RESOLVED] TargetDown"))

    def test_message_capped(self):
        self.server.config = dataclasses.replace(self.config, max_message_chars=40)
        a = _alert(namespace="monitoring")
        a["annotations"] = {"summary": "y" * 500}
        status, _ = self.post_alert(_payload("firing", [a]))
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(self.signal.requests[0][2])["message"]), 40)

    def test_signal_error_returns_502(self):
        self.signal.status = 500
        status, _ = self.post_alert(_payload("firing", [_alert()]))
        self.assertEqual(status, 502)
        self.assertEqual(len(self.signal.requests), 1)

    def test_signal_client_error_returns_502(self):
        self.signal.status = 400
        status, _ = self.post_alert(_payload("firing", [_alert()]))
        self.assertEqual(status, 502)

    def test_signal_timeout_returns_502(self):
        self.signal.delay = 1.5
        start = time.monotonic()
        status, _ = self.post_alert(_payload("firing", [_alert()]))
        self.assertEqual(status, 502)
        self.assertLess(time.monotonic() - start, 1.4)

    def test_signal_unreachable_returns_502(self):
        self.signal.close()
        status, _ = self.post_alert(_payload("firing", [_alert()]))
        self.assertEqual(status, 502)

    def test_bad_json_returns_400(self):
        status, _ = self.request(
            "POST", "/alert", b"{not json", {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(self.signal.requests, [])

    def test_wrong_shape_returns_400(self):
        for payload in (
            [],
            {"status": "firing"},
            {"status": "firing", "alerts": []},
            {"status": "firing", "alerts": "x"},
            {"status": "firing", "alerts": [{"labels": "x"}]},
            {"status": "firing", "alerts": ["x"]},
            {"status": "maybe", "alerts": [_alert()]},
        ):
            with self.subTest(payload=payload):
                status, _ = self.post_alert(payload)
                self.assertEqual(status, 400)
        self.assertEqual(self.signal.requests, [])

    def raw_connection(self):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_address[1], timeout=5
        )
        self.addCleanup(conn.close)
        return conn

    def test_missing_content_length_returns_411(self):
        conn = self.raw_connection()
        conn.putrequest("POST", "/alert")
        conn.putheader("Content-Type", "application/json")
        conn.endheaders()
        self.assertEqual(conn.getresponse().status, 411)
        self.assertEqual(self.signal.requests, [])

    def test_invalid_content_length_returns_400(self):
        for value in ("abc", "-1"):
            with self.subTest(value=value):
                conn = self.raw_connection()
                conn.putrequest("POST", "/alert")
                conn.putheader("Content-Length", value)
                conn.endheaders()
                self.assertEqual(conn.getresponse().status, 400)
        self.assertEqual(self.signal.requests, [])

    def test_deeply_nested_json_returns_400(self):
        body = b"[" * 100_000 + b"]" * 100_000
        status, _ = self.request("POST", "/alert", body)
        self.assertEqual(status, 400)
        self.assertEqual(self.signal.requests, [])

    def test_body_cap_is_256_kib(self):
        self.assertEqual(adapter.MAX_BODY_BYTES, 256 * 1024)

    def test_signal_redirect_not_followed(self):
        self.signal.status = 302
        self.signal.location = self.signal.url + "/v2/send"
        status, _ = self.post_alert(_payload("firing", [_alert()]))
        self.assertEqual(status, 502)
        self.assertEqual(len(self.signal.requests), 1)

    def test_proxy_env_ignored(self):
        with socket.socket() as unused:
            unused.bind(("127.0.0.1", 0))
            proxy = f"http://127.0.0.1:{unused.getsockname()[1]}"
        env = {"HTTP_PROXY": proxy, "http_proxy": proxy, "NO_PROXY": "", "no_proxy": ""}
        with unittest.mock.patch.dict(os.environ, env):
            # A fresh copy, so anything read from the environment at import sees the proxy.
            fresh = _load_adapter(register=False)
            status = fresh.send_to_signal(self.config, "hi")
        self.assertEqual(status, 201)
        self.assertEqual(len(self.signal.requests), 1)

    def test_get_with_body_closes_connection(self):
        conn = self.raw_connection()
        conn.request("GET", "/healthz", body=b"hello")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Connection"), "close")

    def test_alert_post_closes_connection(self):
        conn = self.raw_connection()
        body = json.dumps(_payload("firing", [_alert()])).encode()
        conn.request("POST", "/alert", body=body, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Connection"), "close")

    def test_slow_drip_closed_at_read_deadline(self):
        self.server.read_deadline = 0.5
        sock = socket.create_connection(("127.0.0.1", self.server.server_address[1]), 5)
        self.addCleanup(sock.close)
        sock.sendall(b"POST /alert HTTP/1.1\r\nContent-Length: 1000\r\n\r\n")
        start = time.monotonic()
        closed = False
        # One byte every 0.1 s keeps each recv well under the 30 s socket timeout.
        while not closed and time.monotonic() - start < 3:
            try:
                sock.sendall(b" ")
                ready, _, _ = select.select([sock], [], [], 0.1)
                closed = bool(ready) and sock.recv(1024) == b""
            except OSError:
                closed = True
        self.assertTrue(closed, "connection still open after 3 s of slow drip")
        self.assertEqual(self.signal.requests, [])

    def test_connections_over_cap_get_503(self):
        server = adapter.AdapterServer(("127.0.0.1", 0), self.config, max_connections=1)
        threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        ).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        address = ("127.0.0.1", server.server_address[1])
        holder = socket.create_connection(address, 5)  # takes the only slot, sends nothing
        time.sleep(0.2)
        with socket.create_connection(address, 2) as extra:
            self.assertTrue(extra.recv(1024).startswith(b"HTTP/1.1 503 "))
        holder.close()
        deadline = time.monotonic() + 3
        while True:  # the slot comes back once the holder's handler exits
            with socket.create_connection(address, 2) as again:
                again.sendall(b"GET /healthz HTTP/1.1\r\nHost: x\r\n\r\n")
                if again.recv(1024).startswith(b"HTTP/1.1 200 "):
                    break
            self.assertLess(time.monotonic(), deadline, "slot not released")
            time.sleep(0.05)

    def test_body_over_cap_returns_413(self):
        # Announce an oversized body and send none: the adapter must answer from the header alone.
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_address[1], timeout=5
        )
        self.addCleanup(conn.close)
        conn.putrequest("POST", "/alert")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(adapter.MAX_BODY_BYTES + 1))
        conn.endheaders()
        self.assertEqual(conn.getresponse().status, 413)
        self.assertEqual(self.signal.requests, [])

    def test_unknown_paths_return_404(self):
        self.assertEqual(self.request("GET", "/")[0], 404)
        self.assertEqual(self.request("GET", "/alert")[0], 404)
        self.assertEqual(self.request("POST", "/send", b"{}")[0], 404)
        self.assertEqual(self.signal.requests, [])

    def test_secrets_not_logged_at_info(self):
        with self.assertLogs("signal_adapter", level="DEBUG") as logs:
            self.post_alert(_payload("firing", [_alert(namespace="monitoring")]))
            self.signal.status = 500
            self.post_alert(_payload("firing", [_alert(namespace="monitoring")]))
        info_and_up = "\n".join(r.getMessage() for r in logs.records if r.levelno >= 20)
        self.assertNotIn(NUMBER, info_and_up)
        self.assertNotIn(RECIPIENT, info_and_up)
        self.assertNotIn("[FIRING", info_and_up)


def _child_env(**extra):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    env.update(extra)
    return env


class ProcessTest(unittest.TestCase):
    def test_missing_env_exits_nonzero_with_message(self):
        for env in (
            _child_env(),
            _child_env(NUMBER=NUMBER),
            _child_env(RECIPIENT=RECIPIENT),
        ):
            with self.subTest(
                keys=sorted(k for k in env if k in ("NUMBER", "RECIPIENT"))
            ):
                proc = subprocess.run(
                    [sys.executable, "-I", str(ADAPTER_PATH)],
                    env=env,
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(proc.returncode, 0)
                self.assertRegex(proc.stderr, r"(NUMBER|RECIPIENT).*required")
                self.assertNotIn(NUMBER, proc.stderr)
                self.assertNotIn(RECIPIENT, proc.stderr)

    def test_serves_healthz_and_exits_cleanly_on_sigterm(self):
        proc = subprocess.Popen(
            [sys.executable, "-I", str(ADAPTER_PATH)],
            env=_child_env(
                NUMBER=NUMBER,
                RECIPIENT=RECIPIENT,
                LISTEN_PORT="0",
                SIGNAL_API_URL="http://user:hunter2@127.0.0.1:9/base-path",
            ),
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        port = None
        deadline = time.monotonic() + 10
        lines = []
        while time.monotonic() < deadline:
            line = proc.stderr.readline()
            if not line:
                break
            lines.append(line)
            match = re.search(r"listening on [^ ]*:(\d+)", line)
            if match:
                port = int(match.group(1))
                break
        self.assertIsNotNone(port, f"no listening line in stderr: {lines!r}")
        self.assertIn("sending to http://127.0.0.1:9\n", lines[-1])
        self.assertNotIn("hunter2", lines[-1])
        self.assertNotIn("base-path", lines[-1])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/healthz", timeout=5) as resp:
            self.assertEqual(resp.status, 200)
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=10), 0)
        rest = proc.stderr.read()
        proc.stderr.close()
        self.assertNotIn(NUMBER, "".join(lines) + rest)
        self.assertNotIn(RECIPIENT, "".join(lines) + rest)


if __name__ == "__main__":
    unittest.main()
