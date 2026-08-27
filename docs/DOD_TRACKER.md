# Definition of Done — Tracker

Ticked as each phase's gate goes green. Every box needs a matching proof in EVIDENCE.md.

- [x] Ingestion: post enters as URL or Markdown and is stored; generation reads only the stored post
- [x] Constraint profiles enforced by code (length, tone, hashtag count); a test proves a bad variant is blocked
- [x] Review workflow: draft / approved / rejected / published; only approved can be scheduled; unapproved → 4xx
- [x] Adapter layer: one interface, one real platform, ≥2 mocks; swap changes config not business logic; a test proves it
- [x] Idempotent publish: same variant + slot never posts twice under retries; a test proves it
- [x] Durable scheduling: worker restart mid-batch → zero duplicates
- [x] Publish history: each attempt recorded and visible with its result
- [x] Secrets clean: tokens in .env only; .env.example present
- [x] Tests green and deterministic: blocked variant, refused schedule, duplicate publish, adapter swap
- [x] README: what it does, architecture diagram, exact run steps; a stranger runs it with one command