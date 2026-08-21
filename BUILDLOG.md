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

First: the punctuation rule required text to end with . ! or ? but every variant must also contain a URL, and URLs go at the end. The two rules were in direct conflict and almost nothing could pass. I dropped the punctuation rule entirely since min_sentences already catches fragments.

Second: count_sentences split on . ! ? which meant "https://example.com" got counted as an extra sentence. Every variant with a URL was one sentence over. Fixed by stripping URLs before counting, and added a regression test so it can't come back.

Both bugs came from the same root cause: the URL requirement interacts badly with text analysis. Worth remembering for anything else that parses variant content.