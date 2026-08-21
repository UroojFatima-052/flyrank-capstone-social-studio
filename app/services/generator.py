from app.models import Platform, Post


def summarise(text: str, max_chars: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars].rsplit(" ", 1)[0]
    return cut


def source_link(post: Post) -> str:
    return post.source_url or "https://example.com"


def build_discord(post: Post) -> str:
    body = summarise(post.content, 400)
    return (
        f"New post: {post.title}\n\n"
        f"{body}\n\n"
        f"Read more at {source_link(post)} #backend"
    )


def build_x(post: Post) -> str:
    body = summarise(post.content, 120)
    return f"{body} Read more at {source_link(post)} #backend"


def build_linkedin(post: Post) -> str:
    body = summarise(post.content, 900)
    return (
        f"{post.title}\n\n"
        f"{body}\n\n"
        f"I wrote this up in full. Read more at {source_link(post)} #backend"
    )


BUILDERS = {
    Platform.DISCORD: build_discord,
    Platform.X: build_x,
    Platform.LINKEDIN: build_linkedin,
}


def generate_variant(post: Post, platform: Platform) -> str:
    return BUILDERS[platform](post)