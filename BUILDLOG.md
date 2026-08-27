# Build Log

A record of where AI helped, where it was wrong, and what I changed.

## Phase 0 : Setup
Repo structure and the phase plan. No code, so nothing to get wrong.

## Phase 1 : Design

Worked through the design with an AI assistant, mostly as a way to think out loud. It laid out options and I made the calls.

Constraint profile numbers are mine. It suggested 600 for Discord and 1300 for LinkedIn, I raised them to 1000 and 1500. It also suggested 2 hashtags for X, I set all three platforms to 3.

The useful part was breaking "natural tone" into rules code can actually check. I knew what I wanted the writing to sound like but not how to enforce it. Splitting it into banned phrases, sentence count, emoji cap, and caps limit came out of that conversation.

I asked what stops a plain string column accepting "aproved" and got a real answer, which is why statuses are enums now. Worth asking rather than assuming.

The punctuation rule that came out of this phase turned out to be wrong. See Phase 2.

## Phase 2 : Ingestion Generation

Used an AI assistant for the validator. It got the structure right but had two logic bugs that only showed up when I tested by hand.

- First: the punctuation rule required text to end with . ! or ? but every variant must also contain a URL, and URLs go at the end. The two rules were in direct conflict and almost nothing could pass. I dropped the punctuation rule entirely since min_sentences already catches fragments.

- Second: count_sentences split on . ! ? which meant "https://example.com" got counted as an extra sentence. Every variant with a URL was one sentence over. Fixed by stripping URLs before counting, and added a regression test so it can't come back.

Both bugs came from the same root cause: the URL requirement interacts badly with text analysis. Worth remembering for anything else that parses variant content.

Built templates first to prove the pipeline before adding an API dependency. They work, and they pass validation, but the output is just the source text cut at a character count, so variants end mid-sentence. Templates can cut text, they cannot decide what matters. That is the gap the AI generator fills. Keeping them as a fallback for when the API is down and as deterministic data for tests.

Also worth noting: the validator passed all three of those mid-sentence variants. It checks shape, not sense. No countable rule catches "ends mid-thought".

The AI assistant gave me `gemini-2.0-flash` as the model name. It was retired, and every call came back 404. The useful part is that nothing broke: all three variants fell back to templates and the pipeline kept running, which is exactly what the fallback was built for. I found out my dependency was dead by reading a log line, not by watching the app crash.

Moved the model name into config afterwards so the next deprecation is an env var change, not a code change.

Ran the generator across three different posts and read the output properly instead of just checking it validated. Found three patterns: the same opening phrases repeating across unrelated posts, every closing being a variant of "here is the link", and an emoji on all nine variants.

Added the repeated openings to the banned list, dropped LinkedIn's emoji allowance to zero, and told the prompt that most posts need no emoji at all. The emoji line worked better than expected, all nine came back clean.

Worth noting the validator could not have caught the repetition. It sees one variant at a time, so "every post opens the same way" is invisible to it. That needed a human reading the output.

Called the generate endpoint twice and ended up with duplicate variants. Fixed it by checking which platforms already have a variant and only generating the missing ones, so calling it repeatedly does nothing after the first time. Also added a "skipped" list to the response, because without it a second call returns an empty created list and looks like it failed.

This is the same idea as the idempotency work coming in Phase 4, just applied earlier than planned.

## Phase 3

Put the transition rules in their own file. Four statuses and only certain moves between them, and if that logic sits inside the approve endpoint then the reject endpoint has its own copy and eventually they disagree.

Two more duplicate bugs, both found by double-clicking. Created the same campaign three times before noticing. Then found a variant could hold two pending slots at once. Campaigns got a unique constraint on (post_id, name), slots got a check for an existing pending one.

That is three "create" endpoints in a row that needed a duplicate guard, and I found all three by accident. Going to look for them on purpose in Phase 4.

Fixed the campaign error message too. It said "already exists for this post", which reads like you can only ever have one campaign per post. You can, you just need a different name, and now it says so.

## Phase 4

Built the mocks before Discord. If the interface was wrong I wanted to find out with a class writing to a database, not while debugging a webhook.

The Discord webhook returns 204 with an empty body by default, so there is no message id and no link. Adding wait=true to the query string makes it return the created message instead. Probe 4 needs that link, so one query parameter was the difference between the adapter working and being useless.

Made a deliberate choice that the mock adapters do not deduplicate. Every publish writes a row, even for the same key. That means the MockPost table is a count of how many times the adapter actually ran, which is how I can prove the idempotency guard works rather than just asserting it.

The guard itself is two layers. A select first for the ordinary case, then an IntegrityError catch on the unique constraint for the case where two callers both check, both see nothing, and both insert. The select alone cannot close that gap because there is always a moment between checking and acting. The constraint closes it because the database serialises the inserts.

Nearly recorded Probe 6 as passing when I had only changed the config and seen no Discord message. No publish had actually run, so the silence proved nothing. Reran it properly.

## Phase 5

Chose one recurring job over registering a job per slot. The slots table already records what should publish and when, so the scheduler only needs to be a clock. It also means a slot created while the worker is down still gets picked up.

Spent a while failing to crash the worker. Ctrl+C asks uvicorn to shut down gracefully, so it waits for the publish to finish and the attempt ends up marked success. Had to kill the process outright with Stop-Process -Force to produce a real crash. Worth knowing that a graceful stop is not a test of crash recovery.

Interrupted attempts get marked failed, not retried. When the process dies mid publish there is no way to know whether the message went out. Retrying risks a duplicate, marking it failed risks a message that shows as failed but actually sent. The second is visible in history and a person can check it. The first is not undoable.

Also silenced APScheduler's per-run logs. Two lines every thirty seconds saying nothing happened made the real worker output impossible to see.

The crash test left slot 9 pending, because the slot is only marked done on a successful publish and the interrupted attempt ended as failed. The worker kept picking it up every thirty seconds, correctly refusing to republish, and logging a failure each time. Nothing was broken and nothing was duplicated, but it would have spun forever. Fixed by closing the slot whenever an attempt for it already exists, whatever the outcome. Only found this by reading the logs the next day.

## Phase 6

The clean machine test was worth doing. My README was still the placeholder from Phase 0, so a reviewer cloning the repo would have had no instructions at all. It also showed me what the app looks like with no keys configured: templates instead of the AI, truncated variants, Discord failing outright. All of that is in the README now, because someone hitting it with no explanation would reasonably think the project was broken.

Wanted to add delete endpoints after getting confused by piled up test records. Decided against it this close to submitting. Deleting a post means deciding what happens to its campaigns, variants and publish attempts, and a published variant should probably not be deletable given the state machine treats published as final. Doing it badly would be worse than not doing it.