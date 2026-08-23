# Evidence

One proof per Definition of Done box, a test name with its output, a log line, or a curl transcript. Filled in as each phase completes.

## Constraint profiles enforced by code

Nine deterministic tests covering length, hashtags, banned phrases, shouting, missing source URL, and cross-platform profile differences.

Tests: test_valid_variant_passes, test_variant_too_long_is_blocked,
test_variant_too_short_is_blocked, test_variant_too_many_hashtags_is_blocked,
test_banned_phrase_is_blocked, test_shouting_is_blocked,
test_missing_source_url_is_blocked, test_url_does_not_inflate_sentence_count,
test_same_text_passes_x_but_fails_linkedin

## Ingestion

A post enters as URL or Markdown and is stored. Generation reads only the stored post.

POST /posts with pasted markdown → 201, stored with the given title.
POST /posts with only source_url → 201, page fetched and text extracted.
POST /posts with a blocked page → 422 "Page returned 403."
POST /posts with a thin page → 422 "Could not extract enough text from the page."

Tests: test_fetch_rejects_unreachable_host

## Variant generation

One stored post produces different variants per platform, each passing its constraint profile.

POST /campaigns/1/variants → 3 variants created (discord, x, linkedin), failed: {}
Second call to the same endpoint → created: [], skipped: [discord, x, linkedin]

Tests: test_template_generator_produces_different_variants,
test_template_variants_include_source_url

## Resilience: AI failure falls back to templates

When Gemini is unavailable the generator returns template output instead of failing.
Verified live twice: a retired model name (404) and a free-tier quota limit (429).
Both times all three variants were produced from templates with no crash.

Tests: test_falls_back_to_template_without_api_key

## Review workflow

Statuses draft / approved / rejected / published. Only approved variants can be scheduled.

POST /variants/2/approve → 200, status "approved"
POST /variants/2/approve again → 409, "Cannot move an approved variant to approved."
POST /variants/2/reject then approve → 409, rejected can only return to draft
PATCH /variants/2 with valid content → 200, status back to "draft"
PATCH /variants/2 with content missing the source URL → 409 with the validation errors listed

Tests: test_new_variant_is_draft, test_approve_moves_to_approved, test_cannot_approve_twice,
test_cannot_approve_a_rejected_variant, test_edit_resets_to_draft,
test_edit_rejects_invalid_content, test_published_variant_cannot_be_edited,
test_published_is_terminal

## An unapproved variant cannot be scheduled

POST /variants/1/schedule while the variant is draft → 409
"Only approved variants can be scheduled. This one is draft."

After approving the same variant, the identical request → 201 with a pending slot.

Tests: test_cannot_schedule_a_draft_variant, test_cannot_schedule_a_rejected_variant,
test_approved_variant_can_be_scheduled

## Scheduling guards

Past date → 409 "Scheduled time must be in the future."
Second slot for a variant that already has one pending → 409
Cancel then reschedule → 201 with a new slot

Tests: test_cannot_schedule_in_the_past, test_cannot_double_schedule_the_same_variant,
test_cancelling_frees_the_variant_for_rescheduling

## Duplicate campaigns prevented

Creating the same campaign name for the same post twice → 409 naming the existing campaign id
and explaining that a different name is allowed. Enforced both in the service and by a
UNIQUE constraint on (post_id, name).

## Adapter layer

One SocialPublisher interface, one real platform, two mocks. The application depends on the
interface and never on a platform.

```
app/adapters/base.py       SocialPublisher protocol and PublishResult
app/adapters/discord.py    real Discord webhook
app/adapters/mock.py       MockXPublisher, MockLinkedInPublisher
app/adapters/registry.py   maps platform to adapter using config
```

Real Discord publish, the first message the system sent:

```
PublishResult(success=True,
              external_id='1541026761477853276',
              message_url='https://discord.com/channels/@me/1541025855755784205/1541026761477853276',
              error=None)
```

## Adapter swap changes destination with no code change

With `DISCORD_ADAPTER=mock_x` in `.env`, a discord variant published through the mock:

```
first   attempt_id=3 status=success external_id=x-cb80d4028271
second  attempt_id=3 status=success external_id=x-cb80d4028271
third   attempt_id=3 status=success external_id=x-cb80d4028271
```

The external id is a mock id rather than a Discord snowflake, and no message appeared in
the Discord channel. Only the config value changed.

Tests: test_adapter_swap_changes_the_destination

## Idempotent publish

The key is derived from (variant_id, slot_id) and stored with a UNIQUE constraint. The
attempt row is written as in_progress before the adapter is called, so the insert itself is
the gate rather than a check in application code.

Three publishes against slot 2:

```
first   attempt_id=2 status=success external_id=x-d043a73e1785
second  attempt_id=2 status=success external_id=x-d043a73e1785
third   attempt_id=2 status=success external_id=x-d043a73e1785
```

The mock adapter deliberately does not deduplicate, so the MockPost table counts how many
times the adapter actually ran:

```
1 x variant-2-slot-2
```

One row from three calls. Calls two and three never reached the adapter.

Tests: test_idempotency_key_is_stable, test_publish_succeeds_and_records_an_attempt,
test_publishing_twice_creates_one_attempt, test_publishing_twice_reaches_the_adapter_once,
test_successful_publish_marks_variant_published

## Durable scheduling

APScheduler runs one recurring job every 30 seconds using SQLAlchemyJobStore, so the
schedule survives a restart. The slots table is the source of truth; the scheduler is
only the clock.

A slot scheduled for 14:05 UTC published on its own with no manual trigger:

```
2026-08-23 22:12:15 INFO app.scheduler.worker: Publishing slot 8
```

The message appeared in the Discord channel at that time. The gap between the scheduled
time and the publish is the 30 second polling interval.

Tests: test_due_slots_include_past_pending_slots, test_due_slots_exclude_future_slots,
test_due_slots_exclude_cancelled_slots, test_published_slot_is_no_longer_due

## Crash mid-batch, restart, zero duplicates

The process was killed during a publish with Stop-Process -Force. Ctrl+C does not work
for this test because uvicorn shuts down gracefully and lets the publish finish.

State immediately after the kill, showing the ambiguous case: the adapter had already
written its record, but the attempt was never resolved.

```
attempts:
  6  variant-11-slot-9  in_progress
mock posts:
  4  variant-11-slot-9
```

On restart:

```
2026-08-23 22:26:23 WARNING app.scheduler.worker: Attempt 6 for key variant-11-slot-9 was interrupted, marking failed
2026-08-23 22:26:23 WARNING app.scheduler.runner: Recovered 1 interrupted attempt(s) on startup
```

State after the worker had been polling for several minutes:

```
attempts:
  6  variant-11-slot-9  failed
mock posts:
  4  variant-11-slot-9
```

Still four mock posts. The slot was never republished because the idempotency key
already exists.

Interrupted attempts are marked failed rather than retried. When a process dies mid
publish there is no way to know whether the platform received the message, and a false
failure is something a human can check, while a duplicate post cannot be undone.

Tests: test_recovery_marks_interrupted_attempts_failed,
test_recovery_does_nothing_when_no_attempts_are_stuck,
test_interrupted_slot_is_never_republished

## Publish history

Every attempt is recorded with its result, successes and failures together, newest first.

```
GET /publish-history
GET /publish-history/{variant_id}
```

## Test suite

All tests are deterministic and run offline. No network calls, no API keys required.

$ pytest -v
collected 42 items

```
tests/test_fetcher.py::test_fetch_rejects_unreachable_host PASSED
tests/test_generator.py::test_template_generator_produces_different_variants PASSED
tests/test_generator.py::test_template_variants_include_source_url PASSED
tests/test_generator.py::test_falls_back_to_template_without_api_key PASSED
tests/test_generator.py::test_prompt_includes_platform_rules PASSED
tests/test_generator.py::test_prompt_includes_previous_errors_on_retry PASSED
tests/test_publisher.py::test_idempotency_key_is_stable PASSED
tests/test_publisher.py::test_publish_succeeds_and_records_an_attempt PASSED
tests/test_publisher.py::test_publishing_twice_creates_one_attempt PASSED
tests/test_publisher.py::test_publishing_twice_reaches_the_adapter_once PASSED
tests/test_publisher.py::test_successful_publish_marks_variant_published PASSED
tests/test_publisher.py::test_adapter_swap_changes_the_destination PASSED
tests/test_review_workflow.py::test_new_variant_is_draft PASSED
tests/test_review_workflow.py::test_approve_moves_to_approved PASSED
tests/test_review_workflow.py::test_cannot_approve_twice PASSED
tests/test_review_workflow.py::test_cannot_approve_a_rejected_variant PASSED
tests/test_review_workflow.py::test_edit_resets_to_draft PASSED
tests/test_review_workflow.py::test_edit_rejects_invalid_content PASSED
tests/test_review_workflow.py::test_published_variant_cannot_be_edited PASSED
tests/test_review_workflow.py::test_published_is_terminal PASSED
tests/test_schedule.py::test_cannot_schedule_a_draft_variant PASSED
tests/test_schedule.py::test_cannot_schedule_a_rejected_variant PASSED
tests/test_schedule.py::test_approved_variant_can_be_scheduled PASSED
tests/test_schedule.py::test_cannot_schedule_in_the_past PASSED
tests/test_schedule.py::test_cannot_double_schedule_the_same_variant PASSED
tests/test_schedule.py::test_cancelling_frees_the_variant_for_rescheduling PASSED
tests/test_validator.py::test_valid_variant_passes PASSED
tests/test_validator.py::test_variant_too_long_is_blocked PASSED
tests/test_validator.py::test_variant_too_short_is_blocked PASSED
tests/test_validator.py::test_variant_too_many_hashtags_is_blocked PASSED
tests/test_validator.py::test_banned_phrase_is_blocked PASSED
tests/test_validator.py::test_shouting_is_blocked PASSED
tests/test_validator.py::test_missing_source_url_is_blocked PASSED
tests/test_validator.py::test_url_does_not_inflate_sentence_count PASSED
tests/test_validator.py::test_same_text_passes_x_but_fails_linkedin PASSED
tests/test_worker.py::test_due_slots_include_past_pending_slots PASSED
tests/test_worker.py::test_due_slots_exclude_future_slots PASSED
tests/test_worker.py::test_due_slots_exclude_cancelled_slots PASSED
tests/test_worker.py::test_published_slot_is_no_longer_due PASSED
tests/test_worker.py::test_recovery_marks_interrupted_attempts_failed PASSED
tests/test_worker.py::test_recovery_does_nothing_when_no_attempts_are_stuck PASSED
tests/test_worker.py::test_interrupted_slot_is_never_republished PASSED

42 passed in 3.69s
```