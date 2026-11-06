#!/usr/bin/env python3
"""A LOCAL MOCK of Gnani's Prisma STT REST endpoint, for testing FOREMARK's own client code.

This is NOT Gnani. It imitates the request/response shapes documented at docs.gnani.ai so the
smoke-test script and (later) the backend integration can be exercised offline: retries, error
envelopes, chunking, timeouts. A pass against this mock proves our client logic only. It proves
nothing about transcription quality or about the real service - only real calls do that.

    python backend/scripts/mock_gnani_server.py --port 8765
    GNANI_API_KEY_ID=TESTKEY python backend/scripts/gnani_smoke_test.py clip.wav --url http://127.0.0.1:8765/stt/v3

Scenarios are selected by URL path:
    /stt/v3         normal success (requires header X-API-Key-ID: TESTKEY, fields audio_file + language_code)
    /flaky429       first 2 requests -> 429 RATE_LIMITED, then success
    /timeout504     first request -> 504 UPSTREAM_TIMEOUT, then success
    /always500      always 500 TRANSCRIPTION_FAILED
    /err400         400 MAX_AUDIO_DURATION_EXCEEDED
    /err402         402 insufficient credit
    /slow           sleeps 1.5 s before answering (to test client timeouts)
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from email.parser import BytesParser
from email.policy import default as email_default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EXPECTED_KEY = "TESTKEY"
TRANSCRIPTS = {  # canned replies by language_code, used for the WER test
    "en-IN": "water is collected near the electrical panel room",
    "hi-IN": "बेसमेंट में पानी जमा है",
}


class MockGnaniServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr):
        super().__init__(addr, Handler)
        self.log: list[dict] = []  # every accepted request: path, fields, file bytes, headers
        self.counts: dict[str, int] = {}
        self.lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output quiet
        pass

    def _send(self, status: int, payload: dict, headers: dict | None = None):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        try:
            self.end_headers()
            self.wfile.write(raw)
        except ConnectionError:
            # BrokenPipeError / ConnectionResetError (Linux, macOS) and ConnectionAbortedError (Windows):
            # the client gave up first (e.g. the /slow timeout scenario). Expected, not an error.
            pass

    def do_POST(self):  # noqa: N802 (http.server naming)
        server: MockGnaniServer = self.server  # type: ignore[assignment]
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        path = self.path.split("?")[0]
        with server.lock:
            server.counts[path] = server.counts.get(path, 0) + 1
            n = server.counts[path]

        if self.headers.get("X-API-Key-ID") != EXPECTED_KEY:
            return self._send(401, {"detail": {"error_code": "INVALID_API_KEY", "message": "Invalid API key", "status_code": 401}})

        fields: dict[str, str] = {}
        audio: bytes | None = None
        filename: str | None = None
        message = BytesParser(policy=email_default).parsebytes(
            b"Content-Type: " + self.headers.get("Content-Type", "").encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
        )
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if part.get_filename():
                audio, filename = part.get_payload(decode=True), part.get_filename()
            elif name:
                fields[name] = part.get_content()

        if audio is None or "language_code" not in fields:
            return self._send(422, {"detail": [{"loc": ["body"], "msg": "field required", "type": "missing"}]})

        with server.lock:
            server.log.append(
                {"path": path, "fields": fields, "filename": filename, "audio": audio, "request_id": self.headers.get("X-API-Request-ID")}
            )

        if path == "/flaky429" and n <= 2:
            return self._send(429, {"detail": {"error_code": "RATE_LIMITED", "message": "Too many requests", "status_code": 429}})
        if path == "/timeout504" and n == 1:
            return self._send(504, {"success": False, "error": {"type": "UPSTREAM_TIMEOUT", "message": "Transcription exceeded 5000 ms"}})
        if path == "/always500":
            return self._send(500, {"success": False, "error": {"type": "TRANSCRIPTION_FAILED", "message": "internal failure"}})
        if path == "/err400":
            return self._send(400, {"success": False, "error": {"type": "MAX_AUDIO_DURATION_EXCEEDED", "message": "Audio over 30 s"}})
        if path == "/err402":
            return self._send(402, {"detail": "Insufficient credit"})
        if path == "/slow":
            time.sleep(1.5)

        language = fields["language_code"]
        transcript = TRANSCRIPTS.get(language, f"mock transcript for {filename} ({len(audio)} bytes)")
        self._send(
            200,
            {
                "success": True,
                "request_id": self.headers.get("X-API-Request-ID", "mock-request"),
                "transcript": transcript,
                "model": fields.get("model", "prisma-v2.5"),
                "detected_language_code": "hi-IN" if language.startswith("hi") else "en-IN",
                "processing_time": 0.01,
                "end_to_end_latency": 0.02,
            },
        )


def serve(host: str = "127.0.0.1", port: int = 0) -> tuple[MockGnaniServer, threading.Thread]:
    server = MockGnaniServer((host, port))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    srv, _ = serve(a.host, a.port)
    print(f"Mock Gnani STT listening on http://{a.host}:{srv.server_address[1]}/stt/v3  (key: {EXPECTED_KEY})  Ctrl+C to stop")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()
