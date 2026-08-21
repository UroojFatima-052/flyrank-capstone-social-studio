from dataclasses import dataclass, field
from app.models import Platform

BANNED_PHRASES = [
    "game-changer",
    "game changer",
    "dive into",
    "deep dive",
    "in today's fast-paced",
    "unlock the power",
    "revolutionize",
    "elevate your",
    "seamless",
    "leverage",
    "delve into",
    "tapestry",
    "testament to",
    "ever-evolving landscape",
    "look no further",
    "buckle up",
    "let's face it",
    "the bottom line is",
    "to the next level",
]


@dataclass(frozen=True)
class BrandVoice:
    banned_phrases: list[str] = field(default_factory=lambda: BANNED_PHRASES)
    max_consecutive_caps_words: int = 1
    must_mention_source: bool = True


@dataclass(frozen=True)
class ConstraintProfile:
    platform: Platform
    max_length: int
    min_length: int
    max_hashtags: int
    min_sentences: int
    max_sentences: int
    max_emoji: int


BRAND_VOICE = BrandVoice()

PROFILES: dict[Platform, ConstraintProfile] = {
    Platform.DISCORD: ConstraintProfile(
        platform=Platform.DISCORD,
        max_length=1000,
        min_length=40,
        max_hashtags=3,
        min_sentences=2,
        max_sentences=8,
        max_emoji=3,
    ),
    Platform.X: ConstraintProfile(
        platform=Platform.X,
        max_length=280,
        min_length=40,
        max_hashtags=3,
        min_sentences=1,
        max_sentences=3,
        max_emoji=1,
    ),
    Platform.LINKEDIN: ConstraintProfile(
        platform=Platform.LINKEDIN,
        max_length=1500,
        min_length=120,
        max_hashtags=3,
        min_sentences=3,
        max_sentences=8,
        max_emoji=1,
    ),
}


def get_profile(platform: Platform) -> ConstraintProfile:
    return PROFILES[platform]