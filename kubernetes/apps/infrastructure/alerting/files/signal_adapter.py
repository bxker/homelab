"""Alertmanager webhook -> signal-cli-rest-api adapter (stdlib only).

POST /alert   Alertmanager webhook (payload version 4). One Signal message per
              notification (= per alert group), sent to $SIGNAL_API_URL/v2/send.
              200 when Signal accepts it; 502 when Signal fails, so Alertmanager
              retries; 400 bad JSON or shape; 411/413 missing or oversized body.
GET /healthz  200 "ok".
At most MAX_CONCURRENT_CONNECTIONS connections are served at once (more get 503), and
each request must arrive within REQUEST_READ_DEADLINE_SECONDS.

Env: NUMBER, RECIPIENT (required); SIGNAL_API_URL, LISTEN_PORT, MAX_MESSAGE_CHARS.
NUMBER, RECIPIENT and message bodies are never logged at info level or above.
"""

import dataclasses
import http.client
import json
import logging
import os
import signal
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = logging.getLogger("signal_adapter")

DEFAULT_SIGNAL_API_URL = "http://signal-cli.alerting.svc:8080"
DEFAULT_LISTEN_PORT = 8080
# Signal sends longer texts as an attachment; stay below that.
DEFAULT_MAX_MESSAGE_CHARS = 2000
MAX_BODY_BYTES = 256 * 1024
SEND_TIMEOUT_SECONDS = 10.0
REQUEST_SOCKET_TIMEOUT_SECONDS = 30
# Overall time to read one request (line, headers, body); stops a slow drip that
# keeps each recv under the socket timeout.
REQUEST_READ_DEADLINE_SECONDS = 10.0
MAX_CONCURRENT_CONNECTIONS = 16
ELLIPSIS = "…"


class ConfigError(Exception):
    """Invalid or missing configuration; the message names the variable, never its value."""


class PayloadError(ValueError):
    """The webhook body is not an Alertmanager notification."""


@dataclasses.dataclass(frozen=True)
class Config:
    signal_api_url: str
    number: str
    recipient: str
    listen_port: int = DEFAULT_LISTEN_PORT
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS
    send_timeout: float = SEND_TIMEOUT_SECONDS

    def __repr__(self):  # keeps NUMBER and RECIPIENT out of logs and tracebacks
        return f"Config(signal_api_url={self.signal_api_url!r}, listen_port={self.listen_port})"


def _int_env(env, name, default, low, high):
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer") from None
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return value


def load_config(env):
    """Build a Config from an environment mapping; raise ConfigError when invalid."""
    missing = [
        name for name in ("NUMBER", "RECIPIENT") if not env.get(name, "").strip()
    ]
    if missing:
        raise ConfigError(
            f"{' and '.join(missing)} required (set from the signal ExternalSecret)"
        )
    url = env.get("SIGNAL_API_URL", "").strip() or DEFAULT_SIGNAL_API_URL
    parts = urllib.parse.urlsplit(url)
    try:
        parts.port  # raises ValueError for a non-numeric or out-of-range port
    except ValueError:
        raise ConfigError("SIGNAL_API_URL has an invalid port") from None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ConfigError("SIGNAL_API_URL must be an http(s) URL")
    return Config(
        signal_api_url=url.rstrip("/"),
        number=env["NUMBER"].strip(),
        recipient=env["RECIPIENT"].strip(),
        listen_port=_int_env(env, "LISTEN_PORT", DEFAULT_LISTEN_PORT, 0, 65535),
        max_message_chars=_int_env(
            env, "MAX_MESSAGE_CHARS", DEFAULT_MAX_MESSAGE_CHARS, 1, 100_000
        ),
    )


def url_origin(url):
    """scheme://host:port of url: no credentials, path or query, so it is safe to log."""
    parts = urllib.parse.urlsplit(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return f"{parts.scheme}://{parts.hostname}:{port}"


def validate_payload(payload):
    """Raise PayloadError unless payload has the webhook fields format_message reads."""
    if not isinstance(payload, dict):
        raise PayloadError("body must be a JSON object")
    if payload.get("status") not in ("firing", "resolved"):
        raise PayloadError("status must be firing or resolved")
    alerts = payload.get("alerts")
    if not isinstance(alerts, list) or not alerts:
        raise PayloadError("alerts must be a non-empty list")
    for alert in alerts:
        if not isinstance(alert, dict):
            raise PayloadError("each alert must be an object")
        for key in ("labels", "annotations"):
            if not isinstance(alert.get(key, {}), dict):
                raise PayloadError(f"alert {key} must be an object")
    for key in ("groupLabels", "commonLabels"):
        if not isinstance(payload.get(key, {}), dict):
            raise PayloadError(f"{key} must be an object")


def _text(value):
    return " ".join(str(value).split()) if value is not None else ""


def _alert_lines(alert, group_status):
    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}
    line = "- "
    if group_status == "firing" and alert.get("status") == "resolved":
        line += "RESOLVED "
    line += _text(labels.get("alertname")) or "alert"
    if labels.get("severity"):
        line += f" [{_text(labels['severity'])}]"
    if labels.get("namespace"):
        line += " " + _text(labels["namespace"])
    summary = _text(annotations.get("summary"))
    description = _text(annotations.get("description"))
    if summary or description:
        line += ": " + (summary or description)
    lines = [line]
    if summary and description:
        lines.append("  " + description)
    return lines


def format_message(payload, max_chars):
    """One Signal message for one Alertmanager notification, at most max_chars long."""
    status = payload.get("status")
    alerts = payload.get("alerts") or []
    group = payload.get("groupLabels") or {}
    common = payload.get("commonLabels") or {}
    name = _text(group.get("alertname") or common.get("alertname")) or "alert"
    namespace = _text(group.get("namespace") or common.get("namespace"))
    # Alerts Alertmanager left out (max_alerts); their status is unknown, so count them.
    truncated = payload.get("truncatedAlerts")
    if not isinstance(truncated, int) or isinstance(truncated, bool) or truncated < 0:
        truncated = 0
    if status == "firing":
        firing = sum(1 for alert in alerts if alert.get("status") != "resolved")
        header = f"[FIRING:{firing + truncated}] {name}"
    else:
        header = f"[RESOLVED] {name}"
    if namespace:
        header += f" ({namespace})"
    lines = [header]
    for alert in alerts:
        lines.extend(_alert_lines(alert, status))
    if truncated:
        lines.append(f"+{truncated} more")
    message = "\n".join(lines)
    if len(message) > max_chars:
        message = message[: max_chars - len(ELLIPSIS)] + ELLIPSIS
    return message


class SignalSendError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


# In-cluster service: never use a proxy from the environment, never follow redirects.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def send_to_signal(config, message):
    """POST message to signal-cli-rest-api; return its status or raise SignalSendError."""
    body = json.dumps(
        {"message": message, "number": config.number, "recipients": [config.recipient]}
    ).encode()
    request = urllib.request.Request(
        config.signal_api_url + "/v2/send",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _OPENER.open(request, timeout=config.send_timeout) as response:
            response.read(64 * 1024)
            return response.status
    except urllib.error.HTTPError as err:
        err.close()
        raise SignalSendError(f"signal API returned HTTP {err.code}") from None
    except (urllib.error.URLError, OSError, http.client.HTTPException) as err:
        reason = getattr(err, "reason", err)
        raise SignalSendError(
            f"signal API unreachable: {type(reason).__name__}"
        ) from None


class Handler(BaseHTTPRequestHandler):
    server_version = "signal-adapter"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = REQUEST_SOCKET_TIMEOUT_SECONDS

    def _reply(self, status, text):
        body = (text + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _route(self):
        return urllib.parse.urlsplit(self.path).path

    def handle_one_request(self):
        self._read_timer = threading.Timer(
            self.server.read_deadline, self._read_timed_out
        )
        self._read_timer.daemon = True
        self._read_timer.start()
        try:
            super().handle_one_request()
        finally:
            self._read_timer.cancel()

    def _read_timed_out(self):
        # Unblocks the handler's pending recv; it then sees EOF and drops the connection.
        LOG.debug("request not read within %ss, closing", self.server.read_deadline)
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # already closed

    def do_GET(self):
        self._read_timer.cancel()
        if self.headers.get("Content-Length", "0") != "0" or self.headers.get(
            "Transfer-Encoding"
        ):
            self.close_connection = True  # body left unread
        if self._route() == "/healthz":
            self._reply(200, "ok")
        else:
            self._reply(404, "not found")

    def do_POST(self):
        # One webhook per connection: a keep-alive client can't hold a slot past
        # the read deadline, and the timer can't fire into a reused connection.
        self.close_connection = True
        if self._route() != "/alert":
            self.close_connection = True  # body left unread
            self._reply(404, "not found")
            return
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            self.close_connection = True
            self._reply(411, "Content-Length required")
            return
        try:
            length = int(raw_length)
            if length < 0:
                raise ValueError
        except ValueError:
            self.close_connection = True
            self._reply(400, "invalid Content-Length")
            return
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            LOG.warning(
                "rejected webhook: body of %d bytes over cap %d", length, MAX_BODY_BYTES
            )
            self._reply(413, "body too large")
            return
        body = self.rfile.read(length)
        self._read_timer.cancel()
        if len(body) < length:
            self.close_connection = True
            LOG.warning("rejected webhook: body incomplete (read deadline or EOF)")
            return
        try:
            payload = json.loads(body)
            validate_payload(payload)
        except (ValueError, RecursionError, PayloadError) as err:
            # json.JSONDecodeError and UnicodeDecodeError are ValueErrors;
            # RecursionError comes from deeply nested JSON.
            reason = str(err) if isinstance(err, PayloadError) else "invalid JSON"
            LOG.warning("rejected webhook: %s", reason)
            self._reply(400, reason)
            return
        config = self.server.config
        message = format_message(payload, config.max_message_chars)
        LOG.debug("message: %s", message)
        try:
            status = send_to_signal(config, message)
        except SignalSendError as err:
            LOG.warning(
                "send failed (%s alerts, status %s): %s",
                len(payload["alerts"]),
                payload["status"],
                err,
            )
            self._reply(502, "signal send failed")
            return
        LOG.info(
            "sent %s notification with %d alerts (signal HTTP %d)",
            payload["status"],
            len(payload["alerts"]),
            status,
        )
        self._reply(200, "sent")

    def log_message(self, fmt, *args):
        LOG.debug("%s " + fmt, self.address_string(), *args)


_BUSY_RESPONSE = (
    b"HTTP/1.1 503 Service Unavailable\r\n"
    b"Content-Length: 0\r\nConnection: close\r\n\r\n"
)


class AdapterServer(ThreadingHTTPServer):
    daemon_threads = True
    read_deadline = REQUEST_READ_DEADLINE_SECONDS

    def __init__(self, address, config, max_connections=MAX_CONCURRENT_CONNECTIONS):
        self.config = config
        self._slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        # Runs on the serving thread: answer 503 there instead of starting a thread.
        if not self._slots.acquire(blocking=False):
            LOG.warning("busy: all connection slots in use, answering 503")
            try:
                request.sendall(_BUSY_RESPONSE)
            except OSError:
                pass  # the client is gone; nothing to tell it
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()

    def handle_error(self, request, client_address):
        # Mostly a client that went away or hit the read deadline; no traceback at info.
        LOG.warning("connection dropped: %s", sys.exc_info()[0].__name__)
        LOG.debug("connection error", exc_info=True)


def make_server(config, host=""):
    return AdapterServer((host, config.listen_port), config)


def main():
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    try:
        config = load_config(os.environ)
    except ConfigError as err:
        LOG.error("config error: %s", err)
        return 2
    server = make_server(config)

    def stop(signum, _frame):
        LOG.info("received %s, shutting down", signal.Signals(signum).name)
        # Handler threads are daemons: a send in flight may be cut off when the process
        # exits. Alertmanager then sees no 200 and retries, so a duplicate is possible.
        # shutdown() blocks until serve_forever returns, so not from this (serving) thread.
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    host, port = server.server_address[:2]
    LOG.info(
        "listening on %s:%d, sending to %s",
        host or "0.0.0.0",
        port,
        url_origin(config.signal_api_url),
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
    LOG.info("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
