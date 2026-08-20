# Social Media Studio - Build Workflow

FlyRank Backend Track · Capstone 01
Repo: `flyrank-capstone-social-studio`
---

## Decisions locked

| Thing | Choice | Why |
|---|---|---|
| Language / framework | Python + FastAPI | Already used across the track assignments |
| Database | SQLite (via SQLModel) | Brief allows it; no server to start |
| Real publish target | **Discord webhook** | Telegram needs a VPN in Pakistan |
| Mock adapters | MockX + MockLinkedIn | Written by us, record to DB + preview |
| Variant text | **AI** (Gemini free tier) | Optional per brief, but chosen |
| Scheduler | APScheduler + **SQLAlchemyJobStore** | Persistent job store |
| Tests | pytest | |

**Fallback noted:** if the Discord webhook turns out to be unreachable from Pakistan,
switch the real target to Mastodon. Everything else in the plan is unchanged, that is
the whole point of the adapter layer.

---

## Standing rules

1. **One branch per phase, one PR per phase.** See the git workflow below.
2. **`main` always runs.** A reviewer clones `main` and follows the README. Nothing else.
3. **Fill `EVIDENCE.md` as you go.** The moment a test passes, paste the output. Never at the end.
4. **Small, frequent commits** with real messages. Each phase must be visible in history.
5. **`.env` in `.gitignore` before the first real commit.** No exceptions, no "just for a second".
6. **Tick the DoD tracker** after every phase.

---

## Git workflow

### Branch names - one per phase

| Phase | Branch |
|---|---|
| 0 | `phase-0-setup` |
| 1 | `phase-1-design` |
| 2 | `phase-2-ingestion-generation` |
| 3 | `phase-3-review-workflow` |
| 4 | `phase-4-adapters-idempotency` |
| 5 | `phase-5-scheduling-history` |
| 6 | `phase-6-submission-pack` |

If a phase runs long, split it.

### The loop for every phase

```bash
# 1. start from a clean, current main
git checkout main
git pull

# 2. branch for this phase
git checkout -b phase-2-ingestion-generation

# 3. work — commit after each meaningful chunk, not at the end
git add app/models.py
git commit -m "Add Post and Variant SQLModel tables"

git add app/routers/posts.py
git commit -m "Add POST /posts endpoint for markdown ingestion"

git add tests/test_ingestion.py
git commit -m "Add test for markdown ingestion"

# 4. push the branch
git push -u origin phase-2-ingestion-generation

# 5. open the PR on GitHub, fill the description (template below)

# 6. merge only when the phase gate is green

# 7. back to main for the next phase
git checkout main
git pull
```

---

## PHASE 0 — Repo & project setup · ~1 h

**Branch:** `phase-0-setup`

### Steps
- [ ] Create public GitHub repo `flyrank-capstone-social-studio`
- [ ] First commit **on main**: `README.md` skeleton + `.gitignore` (with `.env`) + MIT `LICENSE`
      — this one is the exception; branch after it exists
- [ ] `git checkout -b phase-0-setup` for everything below
- [ ] Create stub files: `EVIDENCE.md`, `BUILDLOG.md`, `.env.example`
- [ ] Create `docs/DOD_TRACKER.md` with the 10 Definition-of-Done boxes
- [ ] Local folder + virtualenv + `requirements.txt`
- [ ] Folder skeleton (see below)
- [ ] Push

### Folder skeleton
```
flyrank-capstone-social-studio/
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # settings, env vars, adapter registry
│   ├── models.py          # SQLModel tables
│   ├── database.py        # engine + session
│   ├── schemas.py         # Pydantic request/response shapes
│   ├── profiles.py        # constraint profiles per platform
│   ├── routers/           # HTTP layer
│   ├── services/          # business logic
│   ├── adapters/          # SocialPublisher + implementations
│   └── scheduler/         # APScheduler setup + worker
├── tests/
├── docs/
│   ├── DESIGN.md
│   ├── WORKFLOW.md        # this file
│   └── DOD_TRACKER.md
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── EVIDENCE.md
├── BUILDLOG.md
└── LICENSE
```

### Test
Clone the repo into a fresh folder. Confirm it is public and complete.

### GATE
Repo public, `.env` ignored before any real commit, skeleton pushed.

---

## PHASE 1 — Design 

**Branch:** `phase-1-design`

No code. Decisions only, written into `docs/DESIGN.md`.

### Steps
- [ ] **Constraint profiles** — exact rules per platform: max length, tone, max hashtags
- [ ] **`SocialPublisher` interface** — method signature: what goes in, what comes out
- [ ] **Data model** — posts, variants, statuses, slots, publish_attempts (tables, columns, relations)
- [ ] **API surface** — list every endpoint
- [ ] **One explicit non-goal** — required by the brief
- [ ] Write `docs/DESIGN.md`

### GATE
One-page design doc in the repo. PR merged.

---

## PHASE 2 — Ingestion + generation 

**Branch:** `phase-2-ingestion-generation`

### Steps
- [ ] Database setup + SQLModel models
- [ ] `POST /posts` — accept URL or pasted Markdown, store it
- [ ] URL fetch path (requests + text extraction)
- [ ] Constraint profiles as **config**, not hardcoded in functions
- [ ] Variant generator — **templates first**, wire Gemini in after it works
- [ ] The **validator** — enforce length, hashtag count, checkable tone rules
- [ ] `POST /posts/{id}/variants` — generate for all configured platforms

### Tests
- `test_ingest_markdown` — pasted text is stored
- `test_ingest_url` — URL fetched and stored
- `test_variant_too_long_is_blocked` ← **Probe 2**
- `test_variant_too_many_hashtags_is_blocked`
- `test_valid_variant_passes`

### Manual check
Ingest one post → two visibly different variants come out.

### GATE
One stored post produces two different variants; a rule-breaking variant is blocked
with a clear error.
**DoD:** Ingestion · Constraint profiles 

---

## PHASE 3 — Review workflow 

**Branch:** `phase-3-review-workflow`

### Steps
- [ ] Add `status` to variants, default `draft`
- [ ] State machine — which transitions are legal
- [ ] `POST /variants/{id}/approve`, `/reject`, `PATCH /variants/{id}`
- [ ] `GET /variants?status=draft`
- [ ] **The guard** — scheduling checks status first, refuses non-approved with 4xx

### Tests
- `test_new_variant_is_draft`
- `test_approve_moves_to_approved`
- `test_schedule_unapproved_variant_returns_4xx` ← **Probe 3**
- `test_cannot_approve_a_rejected_variant`
- `test_edit_resets_to_draft` (decide the rule deliberately, document it)

### GATE
Unapproved variant cannot be scheduled. Approved one can.
**DoD:** Review workflow 

---

## PHASE 4 — Adapters + idempotent publish 

**Branch:** `phase-4-adapters-idempotency` (split into `-4a-adapters` / `-4b-idempotency` if it runs long)

Two hard things. Do them in this order.

### Steps — A: adapters
- [ ] Define `SocialPublisher` interface (Protocol or ABC)
- [ ] `MockXPublisher` first — no network, proves the shape
- [ ] `MockLinkedInPublisher`
- [ ] Create Discord server + channel + webhook URL → into `.env`
- [ ] `DiscordPublisher` — one POST to the webhook URL
- [ ] **Adapter registry** — config picks which adapter serves which platform ← this is what makes Probe 6 pass

### Steps — B: idempotency
- [ ] `publish_attempts` table with a **unique constraint** on the idempotency key
- [ ] Key derivation: `(variant_id, slot_id)` → stable key
- [ ] Publish logic: existing successful attempt? → return it, do not publish.
      Otherwise → record attempt, publish, record result.

### Tests
- `test_mock_adapter_records_post`
- `test_publish_twice_creates_one_post` ← **Probe 5 core**
- `test_retry_after_timeout_creates_one_post`
- `test_adapter_swap_via_config` ← **Probe 6**

### Manual check
A real message appears in the Discord channel. Screenshot into `EVIDENCE.md`.

### GATE
Real message lands in your channel. Repeated publish call creates exactly one post.
**DoD:** Adapter layer · Idempotent publish 

---

## PHASE 5 — Scheduling, history, hardening 

**Branch:** `phase-5-scheduling-history`

### Steps
- [ ] APScheduler with **SQLAlchemyJobStore** (persistent, not memory)
- [ ] `POST /variants/{id}/schedule` with a time slot
- [ ] Worker: wake, find due variants, publish through the adapter
- [ ] **Crash recovery** — on startup, resolve attempts stuck "in progress"
- [ ] `GET /publish-history` — every attempt and its result
- [ ] Remaining tests
- [ ] README: architecture diagram + exact run steps

### Tests
- `test_scheduled_variant_publishes_at_time`
- `test_worker_restart_no_duplicates` ← **Probe 5**
- `test_publish_history_records_every_attempt`

### Manual check (the big one)
Schedule something 2 minutes out. Start worker. Kill it mid-publish. Restart.
→ Discord channel shows **one** message. History shows **one** success.

### GATE
Every DoD box ticked. Full test suite green.
**DoD:** Durable scheduling · Publish history · Tests 

---

## PHASE 6 — Submission pack 

**Branch:** `phase-6-submission-pack`

The phase people skip and then lose points on.

### Steps
- [ ] **The clean-machine test** — clone into a brand new folder, follow your own README
      exactly, nothing from memory. Whatever breaks, fix in the README. **Do this first.**
- [ ] `EVIDENCE.md` — walk the DoD list top to bottom, confirm every box has a pasted proof
- [ ] `BUILDLOG.md` — honest AI-usage log: where AI helped, where it was wrong, what changed
- [ ] `.env.example` — every variable, placeholder values
- [ ] README final pass: what it does, ASCII architecture diagram, run steps, seed step,
      honest limitations
- [ ] **Overview document** (separate from README, required by the Aug 17 email) —
      the problem this solves, design decisions, any twist added
- [ ] Confirm repo is public
- [ ] Paste repo URL + overview doc into the portal "Add submission" panel

### Test — probe rehearsal
Run all six acceptance probes yourself, in order, as if you were the reviewer:

1. Ingest a post → variants generated, each passes its constraint profile
2. Create a rule-breaking variant → blocked with a clear error, before review
3. Schedule an unapproved variant → honest 4xx
4. Approve + schedule 2 min out → scheduler publishes to Discord; record links to the live message
5. Stop worker mid-publish, restart → history shows exactly one success
6. Swap adapter in config (`discord` → `mock_x`) → same campaign publishes through the mock,
   no code change outside adapters

**Any probe that fails is not done.**

---

