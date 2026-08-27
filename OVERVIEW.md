# Social Media Studio

Capstone 01, Backend Track
Urooj Fatima

Repository: https://github.com/UroojFatima-052/flyrank-capstone-social-studio

## The problem

Someone writes a blog post and then has to promote it. That means writing a short punchy
version for X, a longer one for LinkedIn, something casual for Discord, checking each one
reads properly, and posting them at sensible times instead of all at once at midnight.

It is repetitive work and it is easy to get wrong. But the repetitive part is not really
the hard problem. The hard problem is what happens when something goes wrong halfway
through.

If the network drops right after Discord accepted your message but before you heard back,
you cannot tell whether it posted. Retry and there might be two. Do not retry and there
might be none. If the worker crashes mid batch and restarts, it has no idea what it
already did. And if there is no gate in front of publishing, unreviewed text goes live.

So this is a publishing system, not a posting script. The point is that it survives
those situations.

## What it does

You give it a blog post, either by pasting the text or giving it a URL to fetch. It
generates one variant per platform using Gemini, checks each variant against that
platform's rules, and stores the ones that pass as drafts. You approve or reject each
one. Approved variants can be scheduled. A background worker publishes them at their
scheduled time, and every attempt is recorded whether it worked or not.

Discord publishing is real. X and LinkedIn go through mock adapters that record what
they would have posted, since the brief rules out real accounts on those platforms.

## The parts I spent the most time on

**Making the rules enforceable.** Each platform has a constraint profile with a length
limit, a hashtag cap, an emoji cap and a sentence range. The tricky part was tone. I
wanted the output to sound like a person wrote it, not like marketing copy, but code
cannot check "sounds natural". So I broke it into things code can check: a list of banned
phrases, a sentence count, a cap on consecutive capitalised words. The banned phrase list
started as guesses and grew after I ran the generator across several posts and noticed it
kept opening with the same wording.

**Idempotent publishing.** Every publish attempt gets a key built from the variant id and
the slot id, stored with a UNIQUE constraint. The attempt row is written before the
adapter is called, so the insert itself decides whether the publish goes ahead. That
matters because a check in code always has a gap between checking and acting, and two
workers could both slip through it. A database constraint has no gap.

**Crash recovery.** If the process dies mid publish, the attempt is left marked in
progress. On restart those get marked failed rather than retried. I cannot know whether
the message actually went out. If I retry and it did, there are now two posts. If I mark
it failed and it had sent, the history shows a failure that a person can go and check.
One of those is fixable and the other is not.

**The adapter layer.** The application only ever talks to one interface. Which adapter
handles which platform is a config value, so pointing Discord at a mock is a one line
change in the environment file and nothing in the code moves.

## What I changed from the brief

**Discord instead of Telegram.** The brief suggests Telegram, Discord or Mastodon.
Telegram needs a VPN from Pakistan and I did not want every publish test to involve
connecting and disconnecting. Discord webhooks need one POST and no OAuth.

**AI generation with a template fallback.** The brief says AI is optional. I used it, but
I built the template version first so there is always something that works. That turned
out to matter more than expected. Twice during development the AI was unavailable, once
because the model name I was using had been retired and once because I hit the free tier
daily limit. Both times the system carried on with templates instead of failing.

**Idempotency earlier than planned.** While testing I found that generating variants
twice created duplicates, and creating a campaign twice did too. I fixed both before
getting to the idempotency phase, so variant generation only fills in missing platforms
and campaign names are unique per post.

## What I would do next

A small web frontend. The API is complete but a reviewer has to work through Swagger to
see the review workflow, and a screen with the drafts listed and approve buttons would
show the idea much faster. I ran out of time before submission and did not want to ship
a half finished interface, so it is the first thing I will add.

## How I know it works

There are 42 tests. They run offline, need no API keys, and each one gets its own in
memory database so they cannot interfere with each other. They cover the cases that
actually worry me: a variant that breaks its profile gets blocked, an unapproved variant
cannot be scheduled, publishing three times produces one post, a crashed publish does not
duplicate on restart, and swapping the adapter changes where a variant goes.

I also tested the crash recovery by actually killing the process mid publish. Ctrl+C did
not work for that, because uvicorn shuts down gracefully and waits for the publish to
finish. I had to kill the process outright to produce a real crash.

`EVIDENCE.md` in the repository has the output for each Definition of Done item, and
`BUILDLOG.md` records where I used AI and where it gave me code that was wrong.

## Running it

Clone it, make a virtual environment, install the requirements, run uvicorn. It works
with no configuration at all, using templates instead of the AI and mock adapters instead
of Discord. Add a Gemini key and a Discord webhook to see the full thing. Full
instructions are in the README.