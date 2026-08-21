import logging

from google import genai

from app.config import settings
from app.models import Platform, Post
from app.profiles import BRAND_VOICE, get_profile
from app.services import generator as template_generator
from app.services.validator import validate_variant

logger = logging.getLogger(__name__)

MODEL = settings.gemini_model
MAX_ATTEMPTS = 3


def build_prompt(post: Post, platform: Platform, previous_errors: list[str]) -> str:
    profile = get_profile(platform)
    link = template_generator.source_link(post)
    banned = ", ".join(BRAND_VOICE.banned_phrases)

    prompt = f"""Write a {platform.value} post about the article below.

Rules you must follow:
- Between {profile.min_length} and {profile.max_length} characters
- Between {profile.min_sentences} and {profile.max_sentences} sentences
- At most {profile.max_hashtags} hashtags
- At most {profile.max_emoji} emoji, and never at the end of the post.
  Only use one if it sits naturally inside a sentence and adds something.
  Most posts need none.
- Must include this link: {link}
- Never use these phrases: {banned}
- No more than one fully capitalised word in a row
- Write like a person, not a marketing department. Plain sentences.
  Say what the article is actually about in few words.

Article title: {post.title}

Article:
{post.content}

Return only the post text. No preamble, no quotes around it, no explanation."""

    if previous_errors:
        problems = "\n".join(f"- {e}" for e in previous_errors)
        prompt += f"\n\nYour previous attempt was rejected for these reasons:\n{problems}\nFix them."

    return prompt


def generate_with_ai(post: Post, platform: Platform) -> tuple[str, str]:
    if not settings.gemini_api_key:
        logger.warning("No Gemini API key set, using template for %s", platform.value)
        return template_generator.generate_variant(post, platform), "template"

    client = genai.Client(api_key=settings.gemini_api_key)
    errors: list[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=build_prompt(post, platform, errors),
            )
            text = (response.text or "").strip()
        except Exception as exc:
            logger.warning("Gemini call failed for %s: %s", platform.value, exc)
            return template_generator.generate_variant(post, platform), "template"

        result = validate_variant(text, platform)
        if result.valid:
            logger.info("Generated %s variant on attempt %s", platform.value, attempt)
            return text, "ai"

        logger.info(
            "Attempt %s for %s rejected: %s", attempt, platform.value, result.errors
        )
        errors = result.errors

    logger.warning(
        "All %s attempts failed for %s, using template", MAX_ATTEMPTS, platform.value
    )
    return template_generator.generate_variant(post, platform), "template"