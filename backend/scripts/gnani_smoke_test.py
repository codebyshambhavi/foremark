#!/usr/bin/env python3
"""FOREMARK - Gnani Prisma speech-to-text smoke test.

Sends REAL audio to Gnani's Prisma STT REST API and prints what comes back, so you can
confirm the integration works with your own key before relying on it.

    python backend/scripts/gnani_smoke_test.py path/to/clip.wav
    python backend/scripts/gnani_smoke_test.py hindi.wav english.m4a --language hi-IN --language indic-auto
    python backend/scripts/gnani_smoke_test.py long_report.webm --dry-run     # no API call, no key needed

Requirements: Python 3.11+ (tested on 3.11, 3.12, 3.13), standard library only. ffmpeg/ffprobe are strongly recommended
(needed to convert browser recordings such as .webm and to split audio longer than the limit).

Credentials: read from the GNANI_API_KEY_ID environment variable, or from a .env file in the
repository root (or backend/). The key is sent only in the X-API-Key-ID header and is never printed.

What this script does, per Gnani's documentation (docs.gnani.ai, STT REST reference):
  * POST multipart/form-data to https://api.vachana.ai/stt/v3 with fields audio_file, model,
    language_code (and optionally format).
  * Accepted formats: WAV, MP3, OGG, FLAC, AAC, M4A. Maximum 30 seconds per request, so longer
    audio is split into chunks of --chunk-seconds (default 25) and sent ONE AT A TIME
    (some accounts allow only one active request).
  * Retries only 429/5xx/504 and network errors (with backoff). It never retries 400/401/402/403/422.

Known limitation: chunks are cut at fixed intervals and can split a word at a boundary. The
production pipeline will cut at silence; this script is for connectivity and quality checks.

Optional accuracy check: if "clip.txt" sits next to "clip.wav" it is used as the reference
transcript and an (indicative) word error rate is printed. Spelling variants in Hindi/Hinglish
inflate WER, so read the transcripts as well as the number.

Exit codes: 0 = everything succeeded, 1 = at least one request failed, 2 = configuration/input error.
"""
from __future__ import annotations

import argparse
import glob
import http.client
import json
import mimetypes
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

OFFICIAL_URL = "https://api.vachana.ai/stt/v3"
ACCEPTED_EXT = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"}
HARD_LIMIT_SECONDS = 30.0  # Gnani REST maximum per request (both models)
SEND_WHOLE_MAX_SECONDS = 29.0  # keep a 1 s safety margin below the hard limit
MIN_CHUNK_SECONDS = 0.2  # Gnani returns an empty transcript below 0.1 s; skip crumbs
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

HINTS = {
    "401": "Key missing or invalid. Check GNANI_API_KEY_ID in your .env.",
    "402": "Insufficient credit on the Gnani account.",
    "403": "The key lacks the STT scope, or the account/organisation is restricted.",
    "429": "Rate limited. Some accounts allow only one active request at a time.",
    "MAX_AUDIO_DURATION_EXCEEDED": "Audio over 30 s reached the API. Chunking should have prevented this.",
    "UNSUPPORTED_AUDIO_FORMAT": "Try --convert always to send 16 kHz mono WAV.",
    "AUDIO_CONVERSION_ERROR": "Gnani could not decode the file. Try --convert always.",
    "EMPTY_AUDIO": "The file contained no usable audio.",
    "INVALID_LANGUAGE_CODE": "Use e.g. hi-IN, en-IN, indic-auto (v3.0) or hi-IN,en-IN (v3.0 hints).",
    "MODEL_UNSUPPORTED_LANGUAGE": "That language/model combination is not supported.",
    "UPSTREAM_TIMEOUT": "Gnani's own processing exceeded 5 s (v3.0). Usually transient.",
}


# ----------------------------------------------------------------------------- configuration


def load_dotenv_files(paths: Optional[list[Path]] = None) -> None:
    """Minimal .env reader (no dependency). Never overrides variables already set.

    Reads with utf-8-sig so a BOM (added by Windows Notepad / some PowerShell versions)
    does not corrupt the first variable name.
    """
    here = Path(__file__).resolve()
    for candidate in paths if paths is not None else (here.parents[2] / ".env", here.parents[1] / ".env"):
        if not candidate.is_file():
            continue
        for raw in candidate.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            else:
                value = value.split(" #")[0].strip()
            os.environ.setdefault(key, value)


def key_is_usable(key: Optional[str]) -> bool:
    return bool(key) and not key.lower().startswith("replace-with")


# ----------------------------------------------------------------------------- audio preparation


class PrepError(Exception):
    pass


@dataclass
class Chunk:
    path: Path
    index: int
    duration: Optional[float]
    converted: bool


def probe_duration(path: Path) -> Optional[float]:
    if shutil.which("ffprobe"):
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            return float(proc.stdout.strip())
        except ValueError:
            pass
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                return w.getnframes() / float(w.getframerate())
        except (wave.Error, EOFError):
            return None
    return None


def prepare_chunks(src: Path, workdir: Path, chunk_seconds: float, convert: str, no_split: bool = False) -> list[Chunk]:
    """Return the files to send. Converts/splits only when needed (or when --convert always).

    no_split=True sends the file exactly as given, however long. It exists only to observe how the
    real API reacts to over-limit audio; normal use should never need it.
    """
    duration = probe_duration(src)
    if no_split:
        return [Chunk(src, 0, duration, False)]
    supported = src.suffix.lower() in ACCEPTED_EXT
    needs_split = duration is not None and duration > SEND_WHOLE_MAX_SECONDS
    needs_convert = convert == "always" or (convert == "auto" and (not supported or needs_split))

    if convert == "never" and (not supported or needs_split):
        why = "unsupported format" if not supported else f"{duration:.1f} s exceeds the {HARD_LIMIT_SECONDS:.0f} s limit"
        raise PrepError(f"{src.name}: --convert never was given but the file needs conversion ({why}).")

    if not needs_convert and not needs_split:
        return [Chunk(src, 0, duration, False)]

    if shutil.which("ffmpeg"):
        pattern = workdir / f"{src.stem[:40]}_chunk_%03d.wav"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le"]
        if needs_split:
            cmd += ["-f", "segment", "-segment_time", str(chunk_seconds), "-reset_timestamps", "1"]
        cmd.append(str(pattern) if needs_split else str(workdir / f"{src.stem[:40]}_chunk_000.wav"))
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise PrepError(f"ffmpeg could not process {src.name}: {proc.stderr.strip()[:300]}")
        files = sorted(Path(p) for p in glob.glob(str(workdir / f"{glob.escape(src.stem[:40])}_chunk_*.wav")))
    elif src.suffix.lower() == ".wav":
        files = _split_wav_without_ffmpeg(src, workdir, chunk_seconds)
    else:
        raise PrepError(
            f"{src.name} needs conversion but ffmpeg was not found. Install it "
            "(Windows: winget install Gyan.FFmpeg | macOS: brew install ffmpeg | Linux: apt install ffmpeg) "
            "or provide a WAV/MP3/OGG/FLAC/AAC/M4A file under 29 s."
        )

    chunks: list[Chunk] = []
    for f in files:
        d = probe_duration(f)
        if d is not None and d < MIN_CHUNK_SECONDS:
            print(f"  note: skipped {d:.2f} s trailing fragment {f.name}")
            continue
        chunks.append(Chunk(f, len(chunks), d, True))
    if not chunks:
        raise PrepError(f"{src.name}: no audio chunks were produced.")
    return chunks


def _split_wav_without_ffmpeg(src: Path, workdir: Path, chunk_seconds: float) -> list[Path]:
    try:
        reader = wave.open(str(src), "rb")
    except (wave.Error, EOFError) as exc:
        raise PrepError(f"{src.name}: not a plain PCM WAV and ffmpeg is unavailable ({exc}).") from exc
    out: list[Path] = []
    with reader:
        params = reader.getparams()
        per_chunk = max(1, int(chunk_seconds * reader.getframerate()))
        index = 0
        while True:
            frames = reader.readframes(per_chunk)
            if not frames:
                break
            target = workdir / f"{src.stem[:40]}_chunk_{index:03d}.wav"
            with wave.open(str(target), "wb") as w:
                w.setparams(params)
                w.writeframes(frames)
            out.append(target)
            index += 1
    return out


# ----------------------------------------------------------------------------- HTTP


def build_multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = "----foremark" + uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        parts += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            str(value).encode("utf-8"),
        ]
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", file_path.name)
    ctype = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    parts += [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{safe_name}"'.encode(),
        f"Content-Type: {ctype}".encode(),
        b"",
        file_path.read_bytes(),
        f"--{boundary}--".encode(),
        b"",
    ]
    return b"\r\n".join(parts), f"multipart/form-data; boundary={boundary}"


def extract_error(body: bytes) -> tuple[str, str]:
    """Normalise Gnani's two error shapes: {"error": {...}} and {"detail": ...}."""
    text = body.decode("utf-8", errors="replace")
    try:
        data = json.loads(text)
    except ValueError:
        return "NON_JSON_ERROR", text[:200]
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            return str(err.get("type", "UNKNOWN")), str(err.get("message", ""))
        detail = data.get("detail")
        if isinstance(detail, dict):
            return str(detail.get("error_code", "UNKNOWN")), str(detail.get("message", ""))
        if isinstance(detail, list):
            msgs = "; ".join(str(d.get("msg", d)) for d in detail if isinstance(d, dict))
            return "VALIDATION_ERROR", msgs or str(detail)[:200]
        if isinstance(detail, str):
            return "HTTP_ERROR", detail
    return "UNKNOWN", text[:200]


@dataclass
class ApiResult:
    ok: bool
    status: Optional[int] = None
    attempts: int = 0
    request_id: Optional[str] = None
    transcript: str = ""
    detected_language_code: Optional[str] = None
    processing_time: Optional[float] = None
    end_to_end_latency: Optional[float] = None
    truncated: bool = False
    error_type: Optional[str] = None
    message: Optional[str] = None
    wall_seconds: float = 0.0


def transcribe_chunk(
    *,
    url: str,
    key: str,
    model: str,
    language: str,
    fmt: Optional[str],
    path: Path,
    timeout: float,
    max_retries: int,
    backoff_base: float,
    sleep: Callable[[float], None] = time.sleep,
) -> ApiResult:
    fields = {"language_code": language}
    if model and model not in ("default", "prisma-v2.5"):  # Gnani: omit `model` for the v2.5 default
        fields["model"] = model
    if fmt:
        fields["format"] = fmt
    body, content_type = build_multipart(fields, "audio_file", path)

    # Calls to a local mock must never go through a system proxy. On Windows, urllib reads proxy
    # settings from the registry (ignoring NO_PROXY), which can break localhost requests.
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if host in ("127.0.0.1", "localhost", "::1") else urllib.request.build_opener()

    started = time.monotonic()
    result = ApiResult(ok=False)
    for attempt in range(max_retries + 1):
        result.attempts = attempt + 1
        request_id = str(uuid.uuid4())
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"X-API-Key-ID": key, "X-API-Request-ID": request_id, "Content-Type": content_type},
        )
        retry_after: Optional[float] = None
        try:
            with opener.open(req, timeout=timeout) as resp:
                raw = resp.read()
                status = resp.status
            try:
                data = json.loads(raw.decode("utf-8"))
            except ValueError:
                result.status, result.error_type, result.message = status, "BAD_RESPONSE", "Response was not JSON."
                break
            if not isinstance(data, dict) or data.get("success") is False or not isinstance(data.get("transcript"), str):
                etype, msg = extract_error(raw)
                result.status, result.error_type, result.message = status, etype, msg or "Unexpected response shape."
                break
            result.ok = True
            result.status = status
            result.request_id = data.get("request_id", request_id)
            result.transcript = data["transcript"]
            result.detected_language_code = data.get("detected_language_code")
            result.processing_time = data.get("processing_time")
            result.end_to_end_latency = data.get("end_to_end_latency")
            result.truncated = bool(data.get("truncated", False))
            result.error_type = result.message = None
            break
        except urllib.error.HTTPError as exc:
            result.status = exc.code
            result.error_type, result.message = extract_error(exc.read())
            header = exc.headers.get("Retry-After") if exc.headers else None
            if header and header.isdigit():
                retry_after = float(header)
            if exc.code not in RETRYABLE_STATUS:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.IncompleteRead) as exc:
            result.status = None
            result.error_type = "NETWORK_ERROR"
            result.message = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"

        if attempt < max_retries:
            delay = min(30.0, backoff_base * (2**attempt) + random.uniform(0, backoff_base * 0.25))
            sleep(max(delay, retry_after or 0.0))

    result.wall_seconds = time.monotonic() - started
    return result


# ----------------------------------------------------------------------------- accuracy helper


def word_tokens(text: str) -> list[str]:
    """Split into words treating letters, combining marks and digits as word characters.

    Python's \\w does NOT include Devanagari vowel signs (they are combining marks), so a regex
    split on \\w would shred Hindi words. This keeps them intact.
    """
    text = unicodedata.normalize("NFC", text).lower()
    tokens: list[str] = []
    current: list[str] = []
    for ch in text:
        if unicodedata.category(ch)[0] in "LMN":
            current.append(ch)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def edit_distance(a: list[str], b: list[str]) -> int:
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> Optional[float]:
    ref = word_tokens(reference)
    if not ref:
        return None
    return edit_distance(ref, word_tokens(hypothesis)) / len(ref)


# ----------------------------------------------------------------------------- run


@dataclass
class RunRecord:
    file: str
    language: str
    model: str
    fmt: Optional[str]
    duration_seconds: Optional[float]
    chunks: list[dict] = field(default_factory=list)
    combined_transcript: str = ""
    reference: Optional[str] = None
    wer: Optional[float] = None
    ok: bool = False


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FOREMARK Gnani Prisma STT smoke test (real API calls).")
    p.add_argument("files", nargs="+", type=Path, help="audio file(s) to transcribe")
    p.add_argument(
        "--language",
        action="append",
        help="language_code to send; repeat to compare settings (e.g. hi-IN, en-IN, indic-auto, hi-IN,en-IN). "
        "Default: $GNANI_STT_LANGUAGE or indic-auto",
    )
    p.add_argument("--model", default=None, help="default: $GNANI_STT_MODEL or prisma-v3.0 (prisma-v2.5 omits the field)")
    p.add_argument("--format", dest="fmt", default=None, help="optional Gnani 'format' field, e.g. transcribe or codemix (v3.0)")
    p.add_argument("--url", default=None, help="default: $GNANI_STT_URL or the official endpoint")
    p.add_argument("--chunk-seconds", type=float, default=float(os.environ.get("GNANI_CHUNK_SECONDS", 25)))
    p.add_argument("--convert", choices=["auto", "always", "never"], default="auto")
    p.add_argument("--no-split", action="store_true", help="send each file as-is, however long (only to observe how the API rejects over-limit audio)")
    p.add_argument("--timeout", type=float, default=float(os.environ.get("GNANI_TIMEOUT_SECONDS", 30)))
    p.add_argument("--max-retries", type=int, default=int(os.environ.get("GNANI_MAX_RETRIES", 3)))
    p.add_argument("--backoff-base", type=float, default=1.0, help="seconds; delays are base*2^n (+jitter)")
    p.add_argument("--dry-run", action="store_true", help="prepare/chunk audio and show the plan; no API call, no key needed")
    p.add_argument("--keep-chunks", type=Path, default=None, help="directory to keep prepared chunks in (default: temp, deleted)")
    p.add_argument("--out", type=Path, default=None, help="JSON report path (default: backend/scripts/out/gnani_smoke_<time>.json)")
    p.add_argument("--no-report", action="store_true", help="do not write a JSON report")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # Hindi on Windows consoles
        except (AttributeError, ValueError):
            pass

    load_dotenv_files()
    args = parse_args(argv)

    url = args.url or os.environ.get("GNANI_STT_URL") or OFFICIAL_URL
    model = args.model or os.environ.get("GNANI_STT_MODEL") or "prisma-v3.0"
    languages = args.language or [os.environ.get("GNANI_STT_LANGUAGE") or "indic-auto"]
    key = os.environ.get("GNANI_API_KEY_ID", "")

    if not 5 <= args.chunk_seconds <= 29:
        print("error: --chunk-seconds must be between 5 and 29 (Gnani's limit is 30 s per request).", file=sys.stderr)
        return 2
    if not args.dry_run and not key_is_usable(key):
        print(
            "error: GNANI_API_KEY_ID is not set (or still the placeholder).\n"
            "  Put your key in .env (copied from .env.example) or export it in your shell.\n"
            "  Use --dry-run to check audio preparation without a key.",
            file=sys.stderr,
        )
        return 2
    missing = [str(f) for f in args.files if not f.is_file()]
    if missing:
        print("error: file(s) not found: " + ", ".join(missing), file=sys.stderr)
        return 2
    if model == "prisma-v2.5" and any("," in lang or lang == "indic-auto" for lang in languages):
        print("warning: prisma-v2.5 supports one explicit language per request; indic-auto and lists are v3.0 only.")

    print(f"Endpoint : {url}")
    print(f"Model    : {model}   Languages: {', '.join(languages)}   Format: {args.fmt or '(default)'}")
    print(f"Key      : {'(dry run - not needed)' if args.dry_run else 'loaded from environment (not displayed)'}")
    print(f"Chunks   : files over {SEND_WHOLE_MAX_SECONDS:.0f} s are split into {args.chunk_seconds:g} s pieces, sent one at a time\n")

    records: list[RunRecord] = []
    prep_failed = False
    workroot = args.keep_chunks or Path(tempfile.mkdtemp(prefix="foremark_smoke_"))
    workroot.mkdir(parents=True, exist_ok=True)

    try:
        for src in args.files:
            print(f"== {src.name}")
            workdir = workroot / re.sub(r"[^A-Za-z0-9_-]", "_", src.stem)[:40]
            workdir.mkdir(parents=True, exist_ok=True)
            try:
                chunks = prepare_chunks(src, workdir, args.chunk_seconds, args.convert, args.no_split)
            except PrepError as exc:
                print(f"  PREPARATION FAILED: {exc}\n")
                prep_failed = True
                continue
            total = probe_duration(src)
            note = "converted/split" if any(c.converted for c in chunks) else "sent as-is"
            print(f"  duration {total:.1f} s" if total is not None else "  duration unknown", f"-> {len(chunks)} chunk(s), {note}")

            sidecar = src.with_suffix(".txt")
            reference = sidecar.read_text(encoding="utf-8-sig").strip() if sidecar.is_file() else None  # -sig: tolerate Notepad's BOM

            for language in languages:
                record = RunRecord(src.name, language, model, args.fmt, total, reference=reference)
                records.append(record)
                if args.dry_run:
                    for c in chunks:
                        d = f"{c.duration:.1f} s" if c.duration is not None else "? s"
                        print(f"  [dry-run] chunk {c.index}: {c.path.name} ({d})")
                    record.ok = True
                    continue

                print(f"  language_code={language}")
                texts: list[str] = []
                all_ok = True
                for c in chunks:
                    r = transcribe_chunk(
                        url=url, key=key, model=model, language=language, fmt=args.fmt, path=c.path,
                        timeout=args.timeout, max_retries=args.max_retries, backoff_base=args.backoff_base,
                    )
                    record.chunks.append(
                        {
                            "index": c.index, "duration_seconds": c.duration, "ok": r.ok, "status": r.status,
                            "attempts": r.attempts, "request_id": r.request_id, "transcript": r.transcript,
                            "detected_language_code": r.detected_language_code, "processing_time": r.processing_time,
                            "end_to_end_latency": r.end_to_end_latency, "truncated": r.truncated,
                            "error_type": r.error_type, "message": r.message,
                        }
                    )
                    if r.ok:
                        texts.append(r.transcript)
                        extra = " TRUNCATED" if r.truncated else ""
                        print(
                            f"    chunk {c.index}: OK  request_id={r.request_id}  detected={r.detected_language_code}  "
                            f"processing={r.processing_time}s  e2e={r.end_to_end_latency}s  attempts={r.attempts}{extra}"
                        )
                        print(f"      transcript: {r.transcript or '(empty)'}")
                    else:
                        all_ok = False
                        hint = HINTS.get(str(r.error_type)) or HINTS.get(str(r.status), "")
                        print(f"    chunk {c.index}: FAILED  status={r.status}  type={r.error_type}  attempts={r.attempts}")
                        print(f"      message: {r.message}")
                        if hint:
                            print(f"      hint: {hint}")
                record.ok = all_ok
                record.combined_transcript = " ".join(t for t in texts if t).strip()
                if all_ok and len(chunks) > 1:
                    print(f"  combined transcript: {record.combined_transcript}")
                if all_ok and reference is not None:
                    record.wer = word_error_rate(reference, record.combined_transcript)
                    if record.wer is not None:
                        print(f"  WER vs {sidecar.name}: {record.wer:.1%}  (indicative only; spelling variants inflate it)")
            print()
    finally:
        if args.keep_chunks is None:
            shutil.rmtree(workroot, ignore_errors=True)

    failed = prep_failed or any(not r.ok for r in records)
    print("== Summary")
    for r in records:
        status = "OK    " if r.ok else "FAILED"
        wer = f"  WER {r.wer:.1%}" if r.wer is not None else ""
        print(f"  {status} {r.file}  [{r.language}]{wer}")
    print("A plausible-looking transcript is not verification. Compare against what was actually said;")
    print("see docs/GNANI_VERIFICATION.md before claiming support for any language or Hinglish.")

    if not args.no_report and not args.dry_run and records:
        out = args.out or (Path(__file__).resolve().parent / "out" / f"gnani_smoke_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(), "endpoint": url, "model": model,
            "runs": [r.__dict__ for r in records],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report written to {out} (contains transcripts, never the key; git-ignored)")

    if prep_failed and not records:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
