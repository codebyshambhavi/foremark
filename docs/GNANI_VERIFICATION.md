# Gnani Prisma verification log

This file is the single source of truth for what has **actually been verified** against Gnani's real
API. Nothing here is marked verified until a real call has been made and the result written down.

Source for the API facts below: Gnani's official documentation (docs.gnani.ai), read on 2026-11-06.
The documentation may change; re-check it if something behaves differently.

## 1. What the documentation says (not yet confirmed by our own calls)

| Item | Documented value |
|---|---|
| STT REST endpoint | `POST https://api.vachana.ai/stt/v3` (multipart/form-data) |
| Auth | header `X-API-Key-ID` |
| Optional correlation header | `X-API-Request-ID` (echoed back as `request_id`) |
| Required form fields | `audio_file`, `language_code` |
| Optional form fields | `model` (`prisma-v3.0`; omit for default `prisma-v2.5`), `format` (`verbatim`, `transcribe`; `codemix`/`transliterate` are v3.0 only) |
| Language codes | bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, pa-IN, ta-IN, te-IN. v3.0 also accepts `indic-auto` or up to 4 comma-separated codes (hints, not locks) |
| Audio formats | WAV, MP3, OGG, FLAC, AAC, M4A (converted internally to 16 kHz mono) |
| Max duration | 30 s per request (reference page and quick-start). The overview page says 60 s for v2.5. We design for 30 s. |
| Max file size | not stated |
| Rate limits | no numeric limit; some accounts allow one active request at a time (429 `RATE_LIMITED`, no `Retry-After`) |
| Errors | `{"success":false,"error":{"type","message"}}` for most; auth/rate-limit use `{"detail":{"error_code","message","status_code"}}`; 422 uses `{"detail":[...]}` |
| Transient errors | 429, 5xx, and 504 `UPSTREAM_TIMEOUT` (v3.0, processing over 5 s) |
| Hinglish | **No dedicated STT language code is documented** (`hi-en` appears only in the TTS docs). v3.0 has a `codemix` format and the vendor describes code-mixed support. Accuracy is unverified. |

## 2. What we have verified ourselves

Update this table only after running the commands in section 4 with real audio.

| Claim | Status | Date | Evidence (clips, settings, result) |
|---|---|---|---|
| Authentication and a basic call succeed with our key | Not yet run | | |
| English (en-IN) transcription is usable | Not yet run | | |
| Hindi (hi-IN) transcription is usable | Not yet run | | |
| `indic-auto` detects Hindi / English correctly | Not yet run | | |
| **Hinglish** transcription is usable (state which settings) | Not yet run | | |
| Browser recordings (webm/opus, mp4/aac) work after our WAV conversion | Not yet run | | |
| Audio over 30 s is rejected as documented | Not yet run | | |
| Chunked long recordings join into a sensible transcript | Not yet run | | |
| 429 / 504 behaviour matches the docs | Not yet run | | |

**Rule:** Hinglish support is not claimed in the product, the README or the demo until its row above has
evidence from real Hinglish audio.

## 3. Decide the bar BEFORE you run anything

Write your acceptance criteria here first, so the results cannot be rationalised afterwards:

- Minimum number of clips per category (suggested: at least 5 per language, from more than one speaker if possible): ______
- Word error rate (WER) you consider acceptable: ______ (WER is indicative only for Hindi/Hinglish: spelling variants inflate it)
- Key-term check: which hazard words must appear (e.g. water, electrical, cable, panel): ______
  For this product, whether the key hazard terms are captured matters more than perfect word-for-word accuracy.

## 4. How to run the tests

Commands are for **Windows 11 PowerShell**, run from the repository root. Use `py -3` rather than `python`. If you have
not installed ffmpeg: `winget install Gyan.FFmpeg`, then open a new terminal.

Record short clips (about 10-25 s) on your phone or laptop. Use **synthetic or self-written content only**; do
not record real people's incident details. Save them in `backend\scripts\samples\` (git-ignored). For an
objective score, put a reference transcript next to each clip with the same name: `english1.m4a` and `english1.txt`.
Save the `.txt` as UTF-8 in VS Code (Notepad's "UTF-8 with BOM" also works).

Suggested synthetic reading scripts (edit freely; they mirror the demo scenario):

- English: "Water has collected on the floor near the electrical panel room in Basement Two. A cable is lying close to the water. I have informed the supervisor."
- Hindi: "बेसमेंट दो में इलेक्ट्रिकल पैनल रूम के पास फर्श पर पानी जमा है। एक केबल पानी के पास पड़ी है। मैंने सुपरवाइज़र को बता दिया है।"
- Hinglish: "Basement two mein electrical panel room ke paas floor par pani jama hai. Ek cable pani ke paas pada hai. Maine supervisor ko bata diya hai."

Also record some clips with background noise (a fan, traffic, a hallway), since site conditions are noisy.

```powershell
# 0. Offline self-test of our tooling (uses a local mock, never your key). Expect: Ran 26 tests ... OK
py -3 backend\scripts\test_gnani_smoke.py

# 1. Check audio preparation without spending credit
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\english1.m4a --dry-run

# 2. English and Hindi, explicit language
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\english1.m4a --language en-IN
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\hindi1.m4a --language hi-IN

# 3. Hinglish, compared across settings (keep each result)
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\hinglish1.m4a --language indic-auto --language hi-IN --language "hi-IN,en-IN"
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\hinglish1.m4a --language "hi-IN,en-IN" --format codemix

# 4. A recording longer than 30 s (exercises chunking), and a browser recording
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\long_report.m4a --language "hi-IN,en-IN"
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\browser_recording.webm --language en-IN

# 5. Optional: observe how the real API rejects over-limit audio (sends a >30 s file unsplit, on purpose)
py -3 backend\scripts\gnani_smoke_test.py backend\scripts\samples\long_report.m4a --language en-IN --no-split --convert never
```

(macOS/Linux: the same commands with `python3` and forward slashes.)

Each run writes a JSON report to `backend\scripts\out\` (git-ignored; it contains transcripts, never the key).
If Hindi text looks like boxes or question marks in the terminal, use Windows Terminal and run
`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` first; the saved JSON report is UTF-8 regardless.

## 5. Results log

Add one row per run. Paste the transcript and what was actually said.

| Date | Clip | Settings | Said (reference) | Gnani returned | Key terms captured | WER | Notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
