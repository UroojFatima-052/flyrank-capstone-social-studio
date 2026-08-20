# Design - Social Media Studio

Phase 1. Decisions made before writing code.

---

## The problem

Take one blog post, turn it into posts for a few social platforms, get someone to approve each one, and publish them at a set time.

The easy version is a script that loops over platforms and posts. It falls apart fast. If the network dies right after Discord accepted your message, you don't know whether it worked — retry and you've posted twice. If the worker crashes mid-batch, it has no idea what it already did. And nothing stops unreviewed text going live.

So the real job here isn't posting. It's making the posting survive things going wrong.

---

## Stack

| | |
|---|---|
| Framework | Python + FastAPI |
| Models | SQLModel |
| Database | SQLite |
| Scheduler | APScheduler + SQLAlchemyJobStore |
| Variant text | Gemini free tier |
| Real target | Discord webhook |
| Mock targets | X, LinkedIn |
| Tests | pytest |

**SQLite, not Postgres.** No database server to start means one less thing between a reviewer and a running app.

**Discord as the real target.** Telegram needs a VPN from Pakistan, which would make every test a connect/disconnect cycle. Discord webhooks are one POST, no OAuth.

**APScheduler with a persistent job store.** The default memory store loses every job when the process stops. That's the opposite of durable.

---

## Constraint profiles

Each platform gets a rulebook. The validator enforces it — break a rule and the variant never reaches review.

The hard part was tone. Code can't check "natural" or "not generic", so I broke it into things code *can* check: a banned-phrase list, sentence count, emoji cap, punctuation.

### Shared rules on every platform

| Rule | Value |
|---|---|
| `banned_phrases` | list below |
| `must_end_with_punctuation` | `.` `!` `?` |
| `max_consecutive_caps_words` | 1 |
| `must_mention_source` | true — must contain the post URL |

```
game-changer, game changer, dive into, deep dive, in today's fast-paced,
unlock the power, revolutionize, elevate your, seamless, leverage,
delve into, tapestry, testament to, ever-evolving landscape,
look no further, buckle up, let's face it, the bottom line is,
take your ... to the next level
```

This list will grow. Better to add phrases when I actually catch the model using them than to guess everything up front.

### Per platform

| | Discord | X | LinkedIn |
|---|---|---|---|
| Platform limit | 2000 | 280 | 3000 |
| `max_length` | **1000** | **280** | **1500** |
| `min_length` | 40 | 40 | 120 |
| `max_hashtags` | 3 | 3 | 3 |
| `min_sentences` | 2 | 1 | 3 |
| `max_sentences` | 8 | 3 | 8 |
| `max_emoji` | 3 | 1 | 1 |

X's 280 is a real ceiling. Discord and LinkedIn allow far more than I've set — a 3000-character post isn't a post, it's an article. My limit is the tighter one on purpose.

One sentence works on X. On LinkedIn it looks lazy, so three minimum.

**Known tension:** on X, a URL eats ~23 characters and three hashtags ~45, leaving about 210 for actual words. X variants will fail validation more than the others. The fix is a better prompt, not a looser rule — a validator that never blocks anything proves nothing.

Profiles live in `app/profiles.py` as config, so changing a number doesn't mean touching logic.

---

## The SocialPublisher interface

One interface, three implementations. The app only ever talks to the interface, so adding a platform means adding an adapter and changing a config value.

```python
class SocialPublisher(Protocol):
    def publish(self, content: str, idempotency_key: str) -> PublishResult:
        ...
```

```python
@dataclass
class PublishResult:
    success: bool
    external_id: str | None    # the platform's ID for the message
    message_url: str | None    # link to the live message
    error: str | None
```

**Adapters never raise.** A failed publish returns `success=False` with a reason instead of throwing. The whole point of this system is surviving failure — a worker that dies on one bad publish is exactly what I'm trying to avoid. So failure is just data to check.

**`message_url` is there because the publish record has to link to the live message.** Only the adapter knows how that platform's URLs are shaped, so it's the adapter's job.

```
SocialPublisher
├── DiscordPublisher      → POSTs to a Discord webhook (real)
├── MockXPublisher        → records to the database, shows a preview
└── MockLinkedInPublisher → same
```

A mock adapter is a real implementation — it just writes to the database instead of the internet. That's what makes swapping adapters testable without a real account.

---

## Data model

```
posts
  └── campaigns
        └── variants (discord / x / linkedin)
              └── schedule_slots
                    └── publish_attempts
```

**`posts`** — `id`, `title`, `content` (stored markdown, the source of truth), `source_url` (null if pasted), `created_at`

**`campaigns`** — `id`, `post_id`, `name`, `status` (`draft`/`active`/`completed`), `created_at`

**`variants`** — `id`, `campaign_id`, `post_id`, `platform`, `content`, `status` (`draft`/`approved`/`rejected`/`published`), `created_at`, `updated_at`

**`schedule_slots`** — `id`, `variant_id`, `scheduled_for`, `status` (`pending`/`done`/`cancelled`), `created_at`

**`publish_attempts`** — `id`, `variant_id`, `slot_id`, `idempotency_key` (**UNIQUE**), `status` (`in_progress`/`success`/`failed`), `external_id`, `message_url`, `error`, `attempted_at`

### Three things worth explaining

**The UNIQUE on `idempotency_key` is the whole idempotency guarantee.** The key comes from `(variant_id, slot_id)`, so the same variant in the same slot always makes the same key. If two workers wake at once and both check "published yet?" and both see no, the database still refuses the second insert. I'm not relying on my code checking carefully enough — the database makes the duplicate impossible.

**`publish_attempts` stores failures too.** That's what makes it history rather than a success log — you can see it fail at 09:00 and succeed at 09:01. And `in_progress` is what makes crash recovery work: on startup, anything still sitting at `in_progress` was interrupted, so the worker resolves those before doing anything new.

**`variants.post_id` is redundant** — you could reach the post through the campaign. I kept it because it makes "which post is this from?" one lookup instead of two, and it still works if a campaign ever pulls from more than one post.

### Statuses are enums, not strings

A string column happily accepts `"aproved"`. It saves fine, then `status == "approved"` returns False, and I spend an hour hunting a bug that's a missing letter. An enum makes the bad value impossible to assign. Same idea as the UNIQUE constraint — let the machine enforce it instead of trusting myself to be careful.

---

## API

**Posts**
- `POST /posts` — ingest a URL or pasted markdown
- `GET /posts` · `GET /posts/{id}`

**Campaigns**
- `POST /campaigns` — create from a post
- `GET /campaigns` · `GET /campaigns/{id}` (with variants and their statuses)

**Variants**
- `POST /campaigns/{id}/variants` — generate for every platform
- `GET /variants` (filter by `status`, `platform`) · `GET /variants/{id}`
- `PATCH /variants/{id}` — edit the text
- `POST /variants/{id}/approve` · `POST /variants/{id}/reject`

**Scheduling**
- `POST /variants/{id}/schedule` — 4xx unless approved
- `GET /schedule` · `DELETE /schedule/{id}`

**History**
- `GET /publish-history` · `GET /publish-history/{variant_id}`

### Two decisions

**Approve and reject are their own endpoints, not a status field on PATCH.** If status were editable, anyone could patch a variant straight to `published` and skip review entirely. Making every status change go through an action means the state machine always runs.

**There's no publish endpoint.** Publishing belongs to the scheduler. The only route to the outside world is approve → schedule → worker, which keeps the approval gate on the one path that reaches a real platform.

---

## Review workflow

```
draft ──approve──► approved ──worker publishes──► published
  │
  └───reject────► rejected
```

- Variants start as `draft`.
- Only `approved` can be scheduled. Anything else gets a 4xx.
- Editing the text sends it back to `draft` — you approved specific wording, so changed wording hasn't been approved.
- `published` is set by the worker, never by a client.

---

## Non-goals

**No user accounts or auth.** Single-user. Multi-tenancy would mean an owner column on every table and an auth layer on every endpoint — real work that doesn't exercise anything this capstone is testing. The data model could take it later.

**No real publishing to X or LinkedIn.** Both are mocks that record what they'd have posted. The brief rules out real accounts on those platforms anyway, and one real target is enough to prove the interface works against something that can actually fail.

Also out, per the brief: image generation, analytics, engagement tracking.

---

## Known risks

**The model failing validation.** X's profile is tight enough that some output won't pass. Handled with a retry and a better prompt.

**Timezones.** Everything stored in UTC. Mixed representations mean a scheduler that fires an hour early.

