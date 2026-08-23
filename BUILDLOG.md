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