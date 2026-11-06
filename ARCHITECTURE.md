# FOREMARK architecture

> **Status of this document: design.** It describes what we are building and why. Only the items listed
> in section 1 exist and have been verified today. Everything else is planned and is marked as such in
> [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). Where a number here is provisional it says so.

## 1. What exists today (Batch 1)

| Item | State |
|---|---|
| Repository docs, `.env.example`, `.gitignore` additions, `.gitattributes` (LF endings), Docker Compose (PostgreSQL 16) | Written. `.gitignore` rules checked with `git check-ignore`. Compose file parses and resolves with `docker compose config`; the stack was **not** started with Docker. |
| Init SQL (`pg_trgm`, test database) | Run successfully on a real PostgreSQL 16.15 instance (outside Docker). |
| Gnani Prisma smoke-test script, local mock server, 26 automated tests | Passing against the **mock** only (Python 3.11, 3.12, 3.13, on Linux). Windows-specific hazards were fixed and tested by simulating them, but **not yet run on Windows**. |
| Real Gnani calls | **Not yet made.** See [docs/GNANI_VERIFICATION.md](docs/GNANI_VERIFICATION.md). |
| Application code (backend, frontend, engine) | Not started. |

## 2. Purpose and principles

FOREMARK is a construction-safety **memory** platform. Its differentiator is the explicit, evidence-linked
connection between a *new* observation and a *previously verified corrective action*, with a human-recorded
outcome. We make no claim about what other products do or do not offer; competitor gaps are hypotheses.

Principles that constrain every module:

1. **Humans decide.** The system proposes; a safety officer confirms, rejects or marks inconclusive. Nothing is closed, linked, blamed or concluded automatically. In particular the system never concludes that an earlier corrective action failed.
2. **Never invent.** Missing locations, times, equipment, witnesses, contractors, causes and findings stay empty or show "Not provided".
3. **Provenance on everything.** Every datum is one of: `system_recorded` (timestamps, checksums, user ids), `reporter_stated`, `rule_suggested`, or `officer_confirmed`. The UI shows which. (An app cannot independently "observe" facts, so we do not label anything "observed"; reporter statements are labelled as statements.)
4. **Explain, don't score.** Matches show concrete reasons and differences. There are no confidence percentages.
5. **Append-only history.** Reviews, verifications, evidence, transcripts and audit events are never edited or deleted.
6. **External failures never lose a report.** The report is saved first; transcription and memory checks are retried separately.
7. **Boring and lightweight.** Modular monolith, one database, no queue or search infrastructure, no LLM in any decision path.

## 3. System overview

```
 Browser (Next.js, mobile-first)
        |  HTTPS, Bearer token
        v
 FastAPI backend (one deployable)
   api/  -> auth & site scope -> services/ -> models/ (SQLAlchemy) -> PostgreSQL
                                   |  |  |
                                   |  |  +-- memory_engine/   deterministic Safety Memory Engine (pure Python)
                                   |  +----- extraction/      rule-based draft suggestions
                                   +-------- integrations/gnani/  Prisma STT client (Timbre later)
                          storage/ -> local disk (dev) | S3-compatible bucket (prod)
```

Layers: `api` (HTTP, validation, auth) -> `services` (use cases, transactions, audit) -> `models`.
`memory_engine` and `extraction` are pure functions over plain data (no HTTP, no DB session inside the
decision logic), so they are unit-testable without a database.

## 4. Repository layout

```
foremark/
  backend/
    app/{api,core,models,schemas,services,memory_engine,extraction,integrations/gnani,storage}
    alembic/            migrations (including append-only triggers)
    seed/               clearly labelled synthetic demo data
    scripts/            Gnani smoke test, mock server, trigram check   <- exists
    tests/              pytest
  frontend/             Next.js + TypeScript + Tailwind
  docs/                 verification log, demo script
  tests/e2e/            end-to-end scenario (later)
  docker/postgres/init/ DB init (pg_trgm, test database)            <- exists
  docker-compose.yml, .env.example, README.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md
```

## 5. Roles, authorisation and isolation

Roles are **per site** (`site_memberships.role`): `worker`, `supervisor`, `safety_officer`, `site_admin`.

| Capability | Worker | Supervisor | Safety officer | Site admin |
|---|---|---|---|---|
| Submit report (voice/typed/photo) | yes | yes | yes | no |
| View reports | own | own + their team's items | all at site | all at site (read-only) |
| Triage, confirm category/severity | no | no | yes | no |
| Assign corrective action | no | no | yes | no |
| Update action status, upload evidence | no | assignee team only | no | no |
| Verify / reject evidence | no | no | yes (not the evidence submitter) | no |
| Recurrence review, control review | no | no | yes | no |
| Memory overview, dashboard | no | team-scoped | yes | yes (read-only) |
| Manage zones, teams, shifts, memberships | no | no | no | yes |

Enforcement:

- **Authentication:** email + password (argon2) issues a signed JWT. The demo "role selection" screen logs in as seeded demo users; the backend still enforces everything. No frontend-only role switch.
- **Authorisation:** FastAPI dependencies `current_user`, `site_scope(site_id)` (verifies membership and returns the role) and `require_roles(...)`. Services receive a `SiteScope` object; queries filter by `scope.site_id`, never by a raw client-supplied id.
- **Cross-site context** only returns records from sites where the requesting user holds an active membership. Nothing is shared across an organisation implicitly.
- **Guard test:** a test walks every registered route and fails if one lacks an auth dependency (allow-list: login, health).
- **Separation of duties:** the verifier cannot be the user who submitted the evidence being verified.
- Tokens are sent as `Authorization: Bearer`. Frontend (Vercel) and backend (Render) are different sites, so cookies are not used. Tokens live in `sessionStorage`; this trades some XSS exposure for simplicity and is acceptable for the MVP.

## 6. Domain model

UUID primary keys, UTC `timestamptz`, real foreign keys. Enumerations are `text` + `CHECK` constraints (easier to
migrate than native enums). Tenant tables carry `site_id`; all are indexed on `(site_id, ...)`.

**Organisation and site:** `organisations`; `sites`; `zones` (a tree per site: `kind` = building | floor | zone, `parent_id`);
`users`; `site_memberships(user_id, site_id, role)`; `teams` (with optional contractor name); `shifts`.

**Reporting**

- `hazard_reports`: `record_type` (hazard_observation | near_miss | incident), `site_id`, `zone_id` (nullable; may point at a building, floor or zone depending on what the reporter knew), `location_text` (as stated), `equipment_ref` (nullable, as stated), `activity` (nullable, as stated), `observed_at` (nullable, as stated), `submitted_at` (system), `reporter_id`, `contractor` (nullable), `description`, `possible_consequence`, `immediate_action`, `witnesses` (text, as stated), `category` + `category_source` (reporter | rule_suggested | officer_confirmed), `severity` (officer only), `status` (draft | submitted | in_review | accepted | rejected), `suggestions` (JSONB, rule output, never copied silently into fields), `memory_check_status` (pending | completed | failed) + error + time, `is_synthetic`.
- `report_media`: `kind` (audio | photo), `storage_key`, `sha256`, `size_bytes`, `mime`, `original_filename`, `uploaded_by`.
- `transcriptions`: per audio media. `status` (pending | processing | completed | partial | failed), `provider`, `model`, `language_requested`, `detected_language`, `chunks` (JSONB: index, offsets, request_id, text, status, error), `original_text` (set once, immutable), `edited_text` (reporter edits), `error`.

**Safety memory**

- `hazard_cases`: the longitudinal thread (`site_id`, `title`, `category`, `created_by`). **Case state is derived, never stored or auto-advanced:** awaiting action | action in progress | verified closed, within observation window | verified closed, window elapsed with no recurrence recorded | recurrence under review | further investigation required.
- `case_reports(case_id, report_id, relation)` with `relation` in original | duplicate | recurrence | related; `report_id` unique, so a report belongs to one case.
- `recurrence_events`: one proposed relationship between a new report and a candidate case. `classification` (possible_duplicate | possible_recurrence | similar_hazard), `signals` (frozen JSONB of reasons and differences), `engine_version`, `rules_hash`. Unique `(new_report_id, candidate_case_id)`; editable only while no review exists.
- `recurrence_reviews` (append-only): `decision`, mandatory `reason`, `reviewed_by`, `supersedes_review_id`. The effective decision is the latest. *(Added beyond the original entity list so decisions are never overwritten.)*

**Corrective actions**

- `corrective_actions`: `case_id`, `report_id`, `description`, `assignee_team_id`/`assignee_user_id`, `contractor`, `due_date`, `priority`, `status`, `observation_window_days` (nullable; provisional default taken from the site, see 12).
- `action_evidence` (immutable): `action_id`, `media_id`, `note`, `submitted_by`, checksum via media.
- `verifications` (append-only): `action_id`, `decision` (accepted | rejected), `notes` (required on rejection), `verified_by`.
- `control_reviews` (append-only): `case_id`, `recurrence_event_id`, `outcome` (previous_action_appears_insufficient | different_contributing_condition_identified | new_unrelated_occurrence | insufficient_information | further_investigation_required), `findings`, `supporting_evidence_notes` (required), optional evidence references, `supersedes_review_id`.

**Audit:** `audit_events(occurred_at, actor_id, site_id, entity_type, entity_id, action, details, request_id)`, written by the service layer for every state change, including every failed verification and every rejected match. `briefings` is deferred (Timbre).

**Integrity:** database triggers reject `UPDATE`/`DELETE` on `audit_events`, `action_evidence`, `verifications`, `recurrence_reviews`, `control_reviews`, and reject changes to a non-null `transcriptions.original_text`. This protects against application bugs; a database superuser can still bypass it, so the guarantee is "tamper-evident by design", not tamper-proof.

## 7. Corrective-action lifecycle

```
 open --assign (officer)--> assigned --start (assignee)--> in_progress
                                                   ^              |
                                                   |   submit (assignee, needs >= 1 evidence)
              reject (officer, notes required)     |              v
                                                   +------ submitted_for_verification
                                                                  |
                                                  accept (officer, not the submitter)
                                                                  v
                                                          verified_closed  (terminal)
```

Only these transitions exist; everything else returns 409. `verified_closed` is terminal: a later recurrence never reopens it.
It leads to a recurrence review and, if the officer decides, a **new** action. Three different facts stay distinct:
*completed* (assignee submitted), *verified* (an authorised officer accepted the evidence at that time), and
*no recurrence recorded during the observation window* (absence of reports is not proof the hazard is gone).

## 8. Safety Memory Engine

Deterministic, explainable, testable. No LLM and no learned score. It runs after a report is saved (so an engine fault
cannot lose a report; `memory_check_status` records failures and a retry endpoint exists) and again on officer request.

### 8.1 Inputs compared

Structured: site, location node (building / floor / zone), category, activity, equipment reference, record type,
`observed_at` (falling back to `submitted_at`, **labelled** as such), plus the candidate case's actions, evidence and
verifications. Unstructured: description and location text.

### 8.2 Retrieval (same site)

Candidates come from the same site within a configurable lookback (provisional: 365 days), then are narrowed by location tier:

| Tier | Relationship between the two locations |
|---|---|
| 1 | same node, or one is an ancestor/descendant of the other (e.g. building-level report vs a zone inside it) |
| 2 | nearby: same floor different zone, or same building different floor |
| 3 | same site, different building |
| unknown | either side has no location. **Never guessed.** |

Tier 3 candidates are returned only with a matching equipment reference or a high description band; otherwise they are dropped.
Same-zone is **not** required: tier 2 candidates are retrieved, and the location difference is stated in the reasons.

### 8.3 Signals (the reasons shown to the officer)

Each signal has a status (`match`, `partial`, `differs`, `not_provided`) and plain-language detail:
same site; building / floor / zone relationship; category (and whether it is rule-suggested or officer-confirmed);
equipment reference; activity; description similarity (band: high / moderate / low, with both texts side by side);
shared hazard terms from the lexicon (see 8.5); time between observations (stated in plain units); previous action
status; previous verification date and verifier; and an explicit list of **differences**. There is no numeric confidence.

### 8.4 Classification (fixed decision table; thresholds are provisional)

| Class | Required conditions | Never when |
|---|---|---|
| **possible_recurrence** | candidate case has actions and **all** are `verified_closed` (at least one accepted verification); new observation is **after** the latest verification; location tier 1, or tier 2 with at least two supporting signals; at least one supporting signal (category same, equipment same, description band at least moderate, shared hazard terms) | any action on the case is open, assigned, in progress or submitted; location is unknown on either side |
| **possible_duplicate** | same site; location tier 1; the new observation is **not** after the case's latest verified closure; category same or missing; **and at least two same-occurrence indicators** from: identical media checksum; same equipment reference; description band high; times consistent with one occurrence | location unknown; new observation after verified closure |
| **similar_hazard** | resembles an earlier case but does not meet the above. Includes: case still has an open action (flagged `open_action`), location only tier 2/3, or location unknown | n/a |
| *(none)* | no supporting signal | n/a |

How "same occurrence" is judged without a fixed time window: the question depends on the record type.
For **incidents and near misses** (discrete events) times must be present on both and consistent with one event
(provisional tolerance 120 minutes) *and* corroborated by a second indicator. For **hazard observations** (conditions)
the second report must fall inside the same unresolved episode, i.e. before the earlier case's action was verified closed.
Time is only ever one indicator among several; two similar descriptions alone never make a duplicate.

Server-side invariants (enforced in code, covered by tests, independent of the UI):

- A case with any non-`verified_closed` action can never be classified `possible_recurrence`, and the API rejects a `same_recurring_issue` decision for it (409).
- Cross-site and tier-3 results are **context**: computed on demand, shown with the label "this does not link anything", never persisted as a link and never written to `case_reports`.
- Missing location caps the class at `similar_hazard` and the reasons say "Location not provided".

### 8.5 Text similarity: a measured decision

`pg_trgm` was tested on a real PostgreSQL 16.15 instance with the script `backend/scripts/check_trgm_multilingual.sql`
(8 synthetic sentence pairs; a small sample, not a validation):

| Pair | `C` locale | `C.utf8` locale | Python (locale-independent) |
|---|---|---|---|
| English, same hazard reworded | 0.556 | 0.556 | 0.556 |
| English, different hazard | 0.027 | 0.027 | 0.027 |
| Hinglish (Latin), same hazard | 0.672 | 0.672 | 0.672 |
| Hinglish, different hazard | 0.082 | 0.082 | 0.082 |
| **Hindi (Devanagari), same hazard** | **0.000 (zero trigrams)** | 0.780 | 0.784 |
| **Hindi, different hazard** | **0.000 (zero trigrams)** | 0.080 | 0.077 |
| Devanagari vs Latin, same meaning | 0.000 | 0.000 | 0.000 |
| English vs Hindi, same meaning | 0.000 | 0.000 | 0.000 |

Findings and decisions:

1. Under a plain `C` locale, `pg_trgm` extracts **no trigrams from Devanagari**, so every Hindi comparison scores 0. Whether Hindi matching works would silently depend on the database locale, which we cannot control on every managed Postgres. The official `postgres:16` image's default locale (`en_US.utf8`) was **not** tested here; the script is there so you can run it on your own database.
2. **Decision:** similarity is computed **in Python** on the small candidate set that structured filters already produced. It matched `pg_trgm` under a UTF-8 locale and does not depend on the database. `pg_trgm` stays enabled (harmless, possible later index use) but the engine does not rely on it.
3. The tokenizer must treat combining marks as word characters. Python's `\w` and `str.isalnum()` split Devanagari words at vowel signs (`पानी` becomes two fragments), so we tokenise by Unicode category (letters, marks, digits). A test locks this in.
4. Trigram similarity cannot see across scripts or languages (rows 7 and 8). To make "water" / "pani" / "पानी" comparable, a small hand-written **hazard-term lexicon** maps terms to concepts; shared concepts are one more displayed signal. The lexicon must be reviewed by a Hindi speaker with site knowledge before the demo.
5. Band thresholds (provisional: high at least 0.50, moderate at least 0.25) come from the pairs above, where same-hazard pairs scored 0.56 to 0.78 and different-hazard pairs 0.03 to 0.08. Real reports will be noisier. They are tuned and tested against the labelled synthetic set (section 13), not trusted blindly.

### 8.6 Human review

The officer sees the new report and the historical case side by side: reasons, differences, the original action,
earlier evidence and the verification history. Allowed decisions depend on the class:

| Class | Allowed decisions |
|---|---|
| possible_recurrence | same_recurring_issue, related_different_issue, unrelated, insufficient_information |
| possible_duplicate | duplicate_report, related_different_issue, unrelated, insufficient_information |
| similar_hazard | related_different_issue, unrelated, insufficient_information; duplicate_report only if the case has an open action |

A reason is mandatory. Decisions are appended to `recurrence_reviews`; changing one adds a row. Effects:
`same_recurring_issue` and `duplicate_report` insert a `case_reports` link and a timeline event; the other decisions
link nothing but remain in history, and a rejected pair is not suggested again. After a recurrence decision the UI
**prompts, but does not force,** a `control_review` with the five outcomes. A case whose latest control review is
`further_investigation_required` appears on the dashboard.

## 9. Voice pipeline (Gnani Prisma)

Client and limits are specified in [docs/GNANI_VERIFICATION.md](docs/GNANI_VERIFICATION.md).

1. Browser records with `MediaRecorder` (Chrome: webm/opus; Safari: mp4/aac). The UI caps recording length (provisional: 120 s) and uploads the original.
2. Backend stores the **original** unmodified (SHA-256, size, MIME), creates `report_media` and a `transcriptions` row (`pending`), and returns immediately.
3. A background task transcodes a **derivative** to 16 kHz mono WAV with ffmpeg (webm is not on Gnani's documented format list) and splits it into chunks of at most 25 s (Gnani's REST limit is 30 s). Splitting at silence is the production goal; the smoke script uses fixed cuts.
4. Chunks are sent **one at a time** (a process-wide limit of one in-flight Gnani request, because some accounts allow only one). Model `prisma-v3.0`, language `indic-auto` or hints such as `hi-IN,en-IN`. Retries with backoff on 429, 5xx, 504 and network errors; never on 400, 401, 402, 403, 422.
5. Results are stored per chunk (`chunks` JSONB with Gnani's `request_id`). `original_text` is set once from the joined chunks and never changes; the reporter edits `edited_text`. If some chunks fail, status is `partial`, nothing is fabricated, and the reporter can retry or type.
6. **A failed transcription never blocks submission**: the report can be submitted with audio and typed text, and the transcript can be retried later.
7. The API key is read only from the backend environment (`GNANI_API_KEY_ID`), never logged, never sent to the browser.

Hinglish is treated as **unverified** until real audio shows otherwise. Timbre (spoken briefings) is optional and comes last.

## 10. Rule-based extraction (draft assistance)

`extraction/` exposes an `Extractor` interface with one implementation, `RuleBasedExtractor`. A language-model implementation
can be added later without touching callers; nothing in reporting or the Safety Memory workflow depends on an external LLM.

- Input: description (+ optional transcript). Output: a `suggestions` object. **Nothing is written into report fields silently**; the reporter or officer accepts suggestions, which then carry `rule_suggested` or `officer_confirmed` provenance.
- Suggests: category (from the lexicon, listing the matched terms), activity keywords copied from the text, missing-information flags (location, time, consequence) and static follow-up questions. It does **not** write consequence text, equipment IDs, causes, contractors or witnesses.
- Priority is suggested only from explicit trigger words (for example "injury", "fire", "fall"), always labelled as a suggestion. Severity is set only by an officer.
- The category list and lexicon are configuration, versioned, and explicitly **not** presented as an official standard.

## 11. File storage

`StorageBackend` protocol: `put(key, stream, content_type) -> StoredObject(key, size, sha256)`, `open(key)`, `exists(key)`. There is
deliberately no public delete. Implementations: local disk (development) and S3-compatible (production). Keys include organisation, site
and report. Files are served only through authorised API endpoints, never by public URL. Uploads are size-limited
(`MAX_UPLOAD_MB`), type-checked by content, and filenames are sanitised. The checksum is computed server-side while streaming.

## 12. Provisional values (to confirm, not facts)

| Value | Provisional setting | Why provisional |
|---|---|---|
| Observation window default | 30 days, per site, nullable | not specified; a site-safety decision |
| Lookback for candidates | 365 days | tunable |
| Same-event tolerance (incident / near miss) | 120 minutes | tunable |
| Similarity bands | 0.50 / 0.25 | derived from 8 pairs only |
| Max voice recording | 120 s | UX choice |
| Chunk length | 25 s | 5 s margin under documented 30 s |

## 13. Testing strategy

pytest with a dedicated PostgreSQL test database (`TEST_DATABASE_URL`). The Gnani client is tested against the local mock
server and an injected failing transport. Tests marked `live` call the real API and run only on explicit request with a key set.

The engine is tested against a **labelled synthetic set** (`is_synthetic = true`, clearly marked) with **at least as many
negative cases as positive ones**: same words in another building, same place with a different hazard, an open action, a
second report that is a duplicate, a missing location, Hindi and Hinglish variants, cross-site context.

Required coverage (from the project brief): report creation and persistence; transcript preservation and edit storage;
action lifecycle; evidence upload and checksums; verification and failed verification; duplicate vs similar vs recurrence;
false-match rejection; cross-site context without linking; missing location; audit preservation; role permissions;
organisation and site isolation; Gnani failure handling.

## 14. Deployment (planned, unverified)

Frontend on Vercel; backend as a Docker image on a container host (Render is the default candidate) because ffmpeg is required; managed
PostgreSQL; S3-compatible object storage, because container disks are ephemeral. Free-tier terms (sleep on idle, database expiry, locale,
extension support) must be checked before relying on them. Migrations run at deploy time. `/healthz` checks the database. If deployment
risk threatens the deadline, the fallback is a local `docker compose` demo with a screen recording.

## 15. Decision log

| # | Decision | Reason |
|---|---|---|
| D1 | Modular monolith, one PostgreSQL | scope and deadline; no extra infrastructure |
| D2 | Engine similarity in Python, not `pg_trgm` | Hindi scored 0 under a `C` locale; locale-independent (section 8.5) |
| D3 | Roles per site via memberships | one person can hold different roles at different sites |
| D4 | Bearer tokens, not cookies | frontend and backend are on different sites |
| D5 | `text` + `CHECK` instead of native enums | simpler migrations |
| D6 | Case state derived, not stored | nothing can "auto-close"; avoids drift |
| D7 | Added `recurrence_reviews` table | decisions must be append-only and auditable |
| D8 | Triggers enforce append-only | protects against application bugs |
| D9 | Chunks <= 25 s, sent sequentially | documented 30 s limit and possible one-request concurrency |
| D10 | Rule-based extraction behind an interface | no external LLM dependency for core workflow |
| D11 | Cross-site context limited to sites the user is a member of | no implicit data sharing |
| D12 | Prisma v3.0 as default model | supports `indic-auto` and code-mix options; verify live |

## 16. Open questions

1. Category list and Hindi/Hinglish lexicon need review by someone with site and language knowledge.
2. Default observation window and similarity thresholds need a decision after seeing the synthetic set results.
3. Production object storage provider.
4. Hinglish STT quality: unknown until real audio is run (section 2 of the verification log).
