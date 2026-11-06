# FOREMARK

**Construction Safety Memory & Learning Platform**

> Don't just record what went wrong. Remember what happened next.

Large construction projects generate many hazard observations, near misses and incident records. Most tools
focus on recording a report, assigning a corrective action and closing it. FOREMARK focuses on what happens
**after closure**: it keeps a longitudinal, evidence-linked history of a hazard, so that when something similar is
reported again the safety officer sees the earlier report, the corrective action, the evidence submitted, who
verified it and when, and can record their own investigation outcome.

FOREMARK never decides that an earlier corrective action failed. It proposes possible relationships and explains
its reasons; a safety officer confirms, rejects or marks the match inconclusive, and every decision is preserved.

## Status

**Early development (foundation batch).** No application features exist yet. What exists:

| Component | State |
|---|---|
| Architecture and plan | Written: [ARCHITECTURE.md](ARCHITECTURE.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) |
| Local PostgreSQL via Docker Compose | Configuration written; not yet run by the maintainer |
| Gnani Prisma smoke-test tooling | Tested against a local mock only. **Not yet verified against the real API** ([log](docs/GNANI_VERIFICATION.md)) |
| Hindi / Hinglish term list | Draft awaiting review: [docs/LEXICON_REVIEW.md](docs/LEXICON_REVIEW.md) |
| Backend, frontend, Safety Memory Engine | Not started |

Hinglish speech recognition is **not claimed** until verified with real audio.

## The workflow it is being built around

1. A worker reports a hazard by voice or text.
2. Gnani Prisma transcribes the audio; the reporter reviews and submits. The original audio and transcript are preserved.
3. A safety officer reviews the report and assigns a corrective action.
4. The responsible team submits evidence; the officer verifies it and the action becomes *Verified Closed*.
5. Later, a similar report arrives. FOREMARK retrieves the earlier case with its action, evidence and verification history and explains why it may be related.
6. The officer investigates and records the outcome. The case timeline shows the whole history.

Duplicate reports, similar hazards and possible recurrences after verified closure are treated as different things.

## Principles

- Humans decide; the system proposes and explains. No confidence percentages.
- Missing information stays empty or shows "Not provided". Nothing is invented.
- Reporter statements, rule-based suggestions and officer-confirmed findings are kept visibly separate.
- Reviews, verifications, evidence and audit events are append-only.
- An external service failure never loses a report.
- All demo data is synthetic and labelled as such. FOREMARK makes no claim of regulatory compliance.

## Planned stack

Next.js, TypeScript, Tailwind CSS · FastAPI, SQLAlchemy, Pydantic, Alembic · PostgreSQL · Gnani Prisma (speech-to-text)
· a deterministic Python Safety Memory Engine · Docker Compose for local development.

## Quick start (what works today)

Commands are written for **Windows 11 PowerShell** (run from the repository root). macOS/Linux equivalents are noted.

Prerequisites: Docker Desktop, Python 3.11 or newer (the Gnani tooling was tested on 3.11, 3.12 and 3.13; older
versions are untested), and [ffmpeg](https://ffmpeg.org) for the audio tools.

```powershell
py -3 --version                    # use "py -3" instead of "python": plain "python" can open the Microsoft Store
winget install Gyan.FFmpeg         # then open a NEW terminal so PATH updates
ffmpeg -version
```

Create your local environment file and start the database:

```powershell
Copy-Item .env.example .env        # macOS/Linux: cp .env.example .env
code .env                          # edit in VS Code, saved as UTF-8. Never commit this file or paste its secrets anywhere.
docker compose up -d db            # PostgreSQL 16 with pg_trgm
docker compose ps                  # wait until the db shows "healthy"
```

Check the Gnani tooling offline (uses a local mock; never touches your key):

```powershell
py -3 backend\scripts\test_gnani_smoke.py       # expect: 26 tests ... OK (with ffmpeg + ffprobe)
```

Without both `ffmpeg` and `ffprobe`, audio-conversion/chunking tests are skipped automatically; the remaining tests still run. Install ffmpeg using the instructions above if you want the full 26-test run.

Try the real Prisma API with your own key. Put `GNANI_API_KEY_ID` in `.env` (never in source code, chat or GitHub), then:

```powershell
py -3 backend\scripts\gnani_smoke_test.py "C:\path\to\clip.wav" --language en-IN
py -3 backend\scripts\gnani_smoke_test.py "C:\path\to\hindi.m4a" --language hi-IN
py -3 backend\scripts\gnani_smoke_test.py "C:\path\to\clip.wav" --dry-run      # no API call, no key needed
```

Follow [docs/GNANI_VERIFICATION.md](docs/GNANI_VERIFICATION.md) to record results properly, especially for Hinglish.

Check how `pg_trgm` handles Hindi text in **your** database (see ARCHITECTURE section 8.5). Copy the file into the
container instead of piping it: Windows PowerShell 5.1 pipes text to programs as ASCII, which would turn Hindi into `?`.

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8     # so Devanagari displays (Windows Terminal recommended)
docker compose cp backend/scripts/check_trgm_multilingual.sql db:/tmp/check.sql
docker compose exec db psql -U foremark -d foremark -f /tmp/check.sql
```

Stop the database with `docker compose down` (keeps data) or `docker compose down -v` (deletes local data).

## Repository layout (planned)

```
backend/    FastAPI application, migrations, seed data, tests, scripts
frontend/   Next.js application
docs/       verification log, lexicon review, demo documentation
docker/     database init scripts
```

## License

MIT. See [LICENSE](LICENSE).
