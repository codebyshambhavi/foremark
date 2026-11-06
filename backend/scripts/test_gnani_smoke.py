#!/usr/bin/env python3
"""Tests for the Gnani smoke-test script, run against the LOCAL MOCK server (never the real API).

    python backend/scripts/test_gnani_smoke.py          (standard library only)

What passing proves: our client sends the documented request shape, chunks/converts audio,
retries only what it should, reports errors clearly and never prints the key.
What it does NOT prove: that Gnani transcribes anything correctly. Only real calls with real
speech (see docs/GNANI_VERIFICATION.md) can show that. Tests use synthetic tones as audio.

ffmpeg-dependent tests are skipped automatically when ffmpeg is not installed.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gnani_smoke_test as smoke  # noqa: E402
import mock_gnani_server as mock  # noqa: E402

SCRIPT = HERE / "gnani_smoke_test.py"
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def make_tone(path: Path, seconds: float, *args: str) -> bool:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100:duration={seconds}", *args, str(path)]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def wav_info(raw: bytes) -> tuple[float, int, int]:
    with wave.open(io.BytesIO(raw), "rb") as w:
        return w.getnframes() / w.getframerate(), w.getnchannels(), w.getframerate()


class SmokeScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, _ = mock.serve("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.tmp = Path(tempfile.mkdtemp(prefix="foremark_smoke_test_"))
        cls.short = cls.long = cls.webm = None
        if HAVE_FFMPEG:
            if make_tone(cls.tmp / "short.wav", 10, "-ac", "2"):
                cls.short = cls.tmp / "short.wav"
            if make_tone(cls.tmp / "long.wav", 70, "-ac", "2"):
                cls.long = cls.tmp / "long.wav"
            if make_tone(cls.tmp / "rec.webm", 40, "-c:a", "libopus"):
                cls.webm = cls.tmp / "rec.webm"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- helpers
    def run_cli(self, *args: str, key: str = "TESTKEY", extra_env: dict | None = None):
        env = {
            **os.environ,
            "GNANI_API_KEY_ID": key,
            "GNANI_STT_MODEL": "prisma-v3.0",
            "GNANI_STT_LANGUAGE": "indic-auto",
            "GNANI_CHUNK_SECONDS": "25",
            "GNANI_TIMEOUT_SECONDS": "30",
            "GNANI_MAX_RETRIES": "3",
            "PYTHONIOENCODING": "utf-8",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
            **(extra_env or {}),
        }
        proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8", env=env)
        out = proc.stdout + proc.stderr
        if key and not key.lower().startswith("replace-with"):
            self.assertNotIn(key, out, "the API key must never be printed")
        return proc, out

    def url(self, path: str = "/stt/v3") -> str:
        return self.base + path

    def count(self, path: str) -> int:
        return self.server.counts.get(path, 0)

    def new_log(self, since: int):
        return self.server.log[since:]

    # ---- configuration handling
    def test_missing_key_exits_2_and_says_why(self):
        proc, out = self.run_cli("whatever.wav", key="")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("GNANI_API_KEY_ID", out)

    def test_placeholder_key_is_rejected(self):
        proc, out = self.run_cli("whatever.wav", key="replace-with-your-gnani-api-key-id")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("placeholder", out)

    def test_missing_file_exits_2(self):
        proc, out = self.run_cli("does_not_exist.wav")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not found", out)

    # ---- audio preparation
    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_dry_run_needs_no_key_and_splits_long_audio(self):
        keep = self.tmp / "dry_chunks"
        proc, out = self.run_cli(str(self.long), "--dry-run", "--keep-chunks", str(keep), key="")
        self.assertEqual(proc.returncode, 0, out)
        chunks = sorted(keep.rglob("*_chunk_*.wav"))
        self.assertEqual(len(chunks), 3, out)  # 70 s -> 25 + 25 + 20
        for c in chunks:
            seconds, channels, rate = wav_info(c.read_bytes())
            self.assertLessEqual(seconds, 25.5)
            self.assertEqual((channels, rate), (1, 16000))

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_convert_never_rejects_audio_that_needs_splitting(self):
        proc, out = self.run_cli(str(self.long), "--convert", "never", "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--convert never", out)

    # ---- happy paths and request shape
    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_short_wav_is_sent_as_is_with_documented_fields(self):
        before = len(self.server.log)
        proc, out = self.run_cli(str(self.short), "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        sent = self.new_log(before)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["fields"]["model"], "prisma-v3.0")
        self.assertEqual(sent[0]["fields"]["language_code"], "indic-auto")
        self.assertEqual(sent[0]["audio"], self.short.read_bytes(), "short supported audio must be sent unmodified")
        self.assertRegex(sent[0]["request_id"], r"^[0-9a-f-]{36}$")

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_long_audio_is_chunked_and_sent_sequentially_under_the_limit(self):
        before = len(self.server.log)
        proc, out = self.run_cli(str(self.long), "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        sent = self.new_log(before)
        self.assertEqual(len(sent), 3)
        for item in sent:
            seconds, channels, rate = wav_info(item["audio"])
            self.assertLess(seconds, smoke.HARD_LIMIT_SECONDS)
            self.assertEqual((channels, rate), (1, 16000))
        self.assertIn("combined transcript", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_browser_recording_webm_is_converted_to_wav(self):
        if self.webm is None:
            self.skipTest("this ffmpeg build cannot encode opus/webm")
        before = len(self.server.log)
        proc, out = self.run_cli(str(self.webm), "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        sent = self.new_log(before)
        self.assertEqual(len(sent), 2)  # 40 s -> 25 + 15
        for item in sent:
            self.assertTrue(item["audio"].startswith(b"RIFF"), "webm must be converted to WAV before upload")

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_multiple_language_settings_are_all_sent(self):
        before = len(self.server.log)
        proc, out = self.run_cli(str(self.short), "--language", "hi-IN", "--language", "hi-IN,en-IN", "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        self.assertEqual([e["fields"]["language_code"] for e in self.new_log(before)], ["hi-IN", "hi-IN,en-IN"])

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_report_is_utf8_json_without_the_key(self):
        report = self.tmp / "report.json"
        proc, out = self.run_cli(str(self.short), "--language", "hi-IN", "--url", self.url(), "--out", str(report))
        self.assertEqual(proc.returncode, 0, out)
        text = report.read_text(encoding="utf-8")
        self.assertIn("बेसमेंट में पानी जमा है", text)  # Hindi stored readable, not \u-escaped
        self.assertNotIn("TESTKEY", text)
        self.assertEqual(json.loads(text)["runs"][0]["ok"], True)

    # ---- retries and error handling
    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_429_is_retried_then_succeeds(self):
        before = self.count("/flaky429")
        proc, out = self.run_cli(str(self.short), "--url", self.url("/flaky429"), "--backoff-base", "0.01", "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        self.assertEqual(self.count("/flaky429") - before, 3)  # 2 x 429, then success
        self.assertIn("attempts=3", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_504_upstream_timeout_is_retried(self):
        before = self.count("/timeout504")
        proc, out = self.run_cli(str(self.short), "--url", self.url("/timeout504"), "--backoff-base", "0.01", "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        self.assertEqual(self.count("/timeout504") - before, 2)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_persistent_500_exhausts_retries_and_fails_cleanly(self):
        before = self.count("/always500")
        proc, out = self.run_cli(str(self.short), "--url", self.url("/always500"), "--max-retries", "2", "--backoff-base", "0.01", "--no-report")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.count("/always500") - before, 3)  # 1 try + 2 retries
        self.assertIn("TRANSCRIPTION_FAILED", out)
        self.assertIn("FAILED", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_400_is_never_retried_and_gives_a_hint(self):
        before = self.count("/err400")
        proc, out = self.run_cli(str(self.short), "--url", self.url("/err400"), "--backoff-base", "0.01", "--no-report")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.count("/err400") - before, 1)
        self.assertIn("MAX_AUDIO_DURATION_EXCEEDED", out)
        self.assertIn("hint:", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_402_insufficient_credit_is_never_retried(self):
        before = self.count("/err402")
        proc, out = self.run_cli(str(self.short), "--url", self.url("/err402"), "--backoff-base", "0.01", "--no-report")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.count("/err402") - before, 1)
        self.assertIn("Insufficient credit", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_401_wrong_key_is_never_retried_and_key_not_echoed(self):
        before = self.count("/stt/v3")
        proc, out = self.run_cli(str(self.short), "--url", self.url(), "--backoff-base", "0.01", "--no-report", key="WRONGKEY")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.count("/stt/v3") - before, 1)
        self.assertIn("INVALID_API_KEY", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_client_timeout_is_retried_then_reported(self):
        before = self.count("/slow")
        proc, out = self.run_cli(
            str(self.short), "--url", self.url("/slow"), "--timeout", "0.3", "--max-retries", "1", "--backoff-base", "0.01", "--no-report"
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.count("/slow") - before, 2)
        self.assertIn("NETWORK_ERROR", out)

    # ---- accuracy helper
    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_wer_sidecar_english_and_hindi(self):
        en = self.tmp / "en_ref.wav"
        hi = self.tmp / "hi_ref.wav"
        shutil.copy(self.short, en)
        shutil.copy(self.short, hi)
        en.with_suffix(".txt").write_text("Water is collected near the electrical panel.", encoding="utf-8")  # mock adds the word "room"
        hi.with_suffix(".txt").write_text("बेसमेंट में पानी जमा है", encoding="utf-8")
        proc, out = self.run_cli(str(en), "--language", "en-IN", "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("WER vs en_ref.txt: 14.3%", out)  # 1 insertion / 7 reference words
        proc, out = self.run_cli(str(hi), "--language", "hi-IN", "--url", self.url(), "--no-report")
        self.assertIn("WER vs hi_ref.txt: 0.0%", out)

    # ---- Windows-specific hazards (each reproduces the failing condition directly)
    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_local_mock_is_reached_even_when_a_dead_system_proxy_is_configured(self):
        dead = {"HTTP_PROXY": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9", "NO_PROXY": "", "no_proxy": ""}
        proc, out = self.run_cli(str(self.short), "--url", self.url(), "--no-report", "--max-retries", "0", extra_env=dead)
        self.assertEqual(proc.returncode, 0, out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_reference_text_saved_with_a_utf8_bom_still_scores(self):
        clip = self.tmp / "bom_ref.wav"
        shutil.copy(self.short, clip)
        clip.with_suffix(".txt").write_bytes(b"\xef\xbb\xbf" + "बेसमेंट में पानी जमा है".encode("utf-8"))  # Notepad-style BOM
        proc, out = self.run_cli(str(clip), "--language", "hi-IN", "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("WER vs bom_ref.txt: 0.0%", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
    def test_no_split_sends_over_limit_audio_unmodified(self):
        before = len(self.server.log)
        proc, out = self.run_cli(str(self.long), "--no-split", "--url", self.url(), "--no-report")
        self.assertEqual(proc.returncode, 0, out)
        sent = self.new_log(before)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["audio"], self.long.read_bytes())

    def test_dotenv_with_bom_is_parsed_and_never_overrides_existing_variables(self):
        env_file = self.tmp / "bom.env"
        env_file.write_bytes(
            b"\xef\xbb\xbfFOREMARK_TEST_FIRST=one\r\n# a comment\r\nFOREMARK_TEST_QUOTED=\"two words\"\r\nFOREMARK_TEST_KEEP=from_file # inline\r\n"
        )
        os.environ.pop("FOREMARK_TEST_FIRST", None)
        os.environ.pop("FOREMARK_TEST_QUOTED", None)
        os.environ["FOREMARK_TEST_KEEP"] = "already_set"
        try:
            smoke.load_dotenv_files([env_file])
            self.assertEqual(os.environ.get("FOREMARK_TEST_FIRST"), "one", "first key must not carry a BOM")
            self.assertEqual(os.environ.get("FOREMARK_TEST_QUOTED"), "two words")
            self.assertEqual(os.environ.get("FOREMARK_TEST_KEEP"), "already_set")
        finally:
            for k in ("FOREMARK_TEST_FIRST", "FOREMARK_TEST_QUOTED", "FOREMARK_TEST_KEEP"):
                os.environ.pop(k, None)

    # ---- unit tests (no subprocess)
    def test_devanagari_words_are_not_shredded(self):
        self.assertEqual(smoke.word_tokens("बेसमेंट में पानी"), ["बेसमेंट", "में", "पानी"])
        self.assertNotEqual(re.findall(r"\w+", "पानी"), ["पानी"], "documents why a plain \\w tokenizer is unsafe for Hindi")

    def test_word_error_rate_basics(self):
        self.assertEqual(smoke.word_error_rate("a b c d", "a b c d"), 0.0)
        self.assertEqual(smoke.word_error_rate("a b c d", "a x c d"), 0.25)
        self.assertIsNone(smoke.word_error_rate("", "anything"))

    def test_error_envelopes_are_normalised(self):
        e = smoke.extract_error
        self.assertEqual(e(b'{"success":false,"error":{"type":"EMPTY_AUDIO","message":"m"}}'), ("EMPTY_AUDIO", "m"))
        self.assertEqual(e(b'{"detail":{"error_code":"RATE_LIMITED","message":"slow down","status_code":429}}'), ("RATE_LIMITED", "slow down"))
        self.assertEqual(e(b'{"detail":[{"msg":"field required"}]}'), ("VALIDATION_ERROR", "field required"))
        self.assertEqual(e(b'{"detail":"Insufficient credit"}'), ("HTTP_ERROR", "Insufficient credit"))
        self.assertEqual(e(b"<html>bad gateway</html>")[0], "NON_JSON_ERROR")

    def test_placeholder_detection(self):
        self.assertFalse(smoke.key_is_usable(""))
        self.assertFalse(smoke.key_is_usable("replace-with-your-gnani-api-key-id"))
        self.assertTrue(smoke.key_is_usable("abc123"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
