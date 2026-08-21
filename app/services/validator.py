import re
from dataclasses import dataclass
from app.models import Platform
from app.profiles import BRAND_VOICE, get_profile

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)

URL_PATTERN = re.compile(r"https?://\S+")


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


def count_hashtags(text: str) -> int:
    return len(re.findall(r"#\w+", text))


def count_emoji(text: str) -> int:
    return len(EMOJI_PATTERN.findall(text))


def count_sentences(text: str) -> int:
    without_urls = URL_PATTERN.sub("", text)
    parts = re.split(r"[.!?]+", without_urls)
    return len([p for p in parts if p.strip()])


def longest_caps_run(text: str) -> int:
    longest = 0
    current = 0
    for word in text.split():
        stripped = re.sub(r"[^A-Za-z]", "", word)
        if len(stripped) > 1 and stripped.isupper():
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def validate_variant(content: str, platform: Platform) -> ValidationResult:
    profile = get_profile(platform)
    errors: list[str] = []

    text = content.strip()

    if len(text) > profile.max_length:
        errors.append(
            f"Too long: {len(text)} characters, {profile.max_length} allowed."
        )

    if len(text) < profile.min_length:
        errors.append(
            f"Too short: {len(text)} characters, {profile.min_length} required."
        )

    hashtags = count_hashtags(text)
    if hashtags > profile.max_hashtags:
        errors.append(
            f"Too many hashtags: {hashtags} found, {profile.max_hashtags} allowed."
        )

    emoji = count_emoji(text)
    if emoji > profile.max_emoji:
        errors.append(f"Too many emoji: {emoji} found, {profile.max_emoji} allowed.")

    sentences = count_sentences(text)
    if sentences < profile.min_sentences:
        errors.append(
            f"Too few sentences: {sentences} found, {profile.min_sentences} required."
        )
    if sentences > profile.max_sentences:
        errors.append(
            f"Too many sentences: {sentences} found, {profile.max_sentences} allowed."
        )

    lowered = text.lower()
    for phrase in BRAND_VOICE.banned_phrases:
        if phrase in lowered:
            errors.append(f"Banned phrase: '{phrase}'.")

    caps_run = longest_caps_run(text)
    if caps_run > BRAND_VOICE.max_consecutive_caps_words:
        errors.append(
            f"Too many consecutive capitalised words: {caps_run} in a row."
        )

    if BRAND_VOICE.must_mention_source and not URL_PATTERN.search(text):
        errors.append("Must include the source post URL.")

    return ValidationResult(valid=not errors, errors=errors)