from app.models import Platform
from app.services.validator import validate_variant


GOOD_X = (
    "Spent the week rebuilding how our scheduler handles retries. "
    "Turns out most double-posting bugs come down to one missing constraint. "
    "Read more at https://example.com #backend"
)


def test_valid_variant_passes():
    result = validate_variant(GOOD_X, Platform.X)
    assert result.valid
    assert result.errors == []


def test_variant_too_long_is_blocked():
    long_text = "This is a post about backends. " * 20 + "https://example.com"
    result = validate_variant(long_text, Platform.X)
    assert not result.valid
    assert any("Too long" in e for e in result.errors)


def test_variant_too_short_is_blocked():
    result = validate_variant("Short. https://example.com", Platform.X)
    assert not result.valid
    assert any("Too short" in e for e in result.errors)


def test_variant_too_many_hashtags_is_blocked():
    text = (
        "Rebuilt the retry logic this week and learned a lot. "
        "Read more at https://example.com #ai #backend #python #dev"
    )
    result = validate_variant(text, Platform.X)
    assert not result.valid
    assert any("Too many hashtags" in e for e in result.errors)


def test_banned_phrase_is_blocked():
    text = (
        "This new tool will revolutionize how you work every single day. "
        "Read more at https://example.com"
    )
    result = validate_variant(text, Platform.X)
    assert not result.valid
    assert any("Banned phrase" in e for e in result.errors)


def test_shouting_is_blocked():
    text = (
        "This SEAMLESS NEW TOOL changes how retries work in our scheduler. "
        "Read more at https://example.com"
    )
    result = validate_variant(text, Platform.X)
    assert not result.valid
    assert any("capitalised words" in e for e in result.errors)


def test_missing_source_url_is_blocked():
    text = "Rebuilt the retry logic this week and learned a lot about constraints."
    result = validate_variant(text, Platform.X)
    assert not result.valid
    assert any("source post URL" in e for e in result.errors)


def test_url_does_not_inflate_sentence_count():
    text = (
        "First sentence here about retries. Second sentence about constraints. "
        "https://example.com"
    )
    result = validate_variant(text, Platform.X)
    assert not any("sentences" in e for e in result.errors)


def test_same_text_passes_x_but_fails_linkedin():
    short = "New post is up. Read more at https://example.com"
    assert validate_variant(short, Platform.X).valid
    assert not validate_variant(short, Platform.LINKEDIN).valid