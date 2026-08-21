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