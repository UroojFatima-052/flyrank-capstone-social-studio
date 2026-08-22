from app.models import Platform, Post
from app.services import ai_generator
from app.services.generator import generate_variant
from app.services.validator import validate_variant


SAMPLE_POST = Post(
    id=1,
    title="Why retries need idempotency keys",
    content=(
        "A retry after a timeout is the hardest case in publishing. "
        "The platform may have accepted your post before the connection dropped, "
        "so retrying blindly creates a duplicate. An idempotency key lets the "
        "server recognise the second attempt as the same request. "
        "The database enforces it with a unique constraint, so two workers "
        "racing each other still produce exactly one post."
    ),
    source_url="https://example.com/idempotency",
)


def test_template_generator_produces_different_variants():
    discord = generate_variant(SAMPLE_POST, Platform.DISCORD)
    x = generate_variant(SAMPLE_POST, Platform.X)
    assert discord != x


def test_template_variants_include_source_url():
    for platform in Platform:
        text = generate_variant(SAMPLE_POST, platform)
        assert "https://example.com/idempotency" in text


def test_falls_back_to_template_without_api_key(monkeypatch):
    monkeypatch.setattr(ai_generator.settings, "gemini_api_key", "")
    text, source = ai_generator.generate_with_ai(SAMPLE_POST, Platform.X)
    assert source == "template"
    assert text == generate_variant(SAMPLE_POST, Platform.X)


def test_prompt_includes_platform_rules():
    prompt = ai_generator.build_prompt(SAMPLE_POST, Platform.X, [])
    assert "280" in prompt
    assert "https://example.com/idempotency" in prompt


def test_prompt_includes_previous_errors_on_retry():
    prompt = ai_generator.build_prompt(
        SAMPLE_POST, Platform.X, ["Too long: 340 characters, 280 allowed."]
    )
    assert "Too long" in prompt
    assert "rejected" in prompt.lower()