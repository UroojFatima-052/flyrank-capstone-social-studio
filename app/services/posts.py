from sqlmodel import Session, select
from app.models import Post
from app.schemas import PostCreate
from app.services.fetcher import FetchError, fetch_page

def create_post(session: Session, data: PostCreate) -> Post:
    title = data.title
    content = data.content

    if not content:
        title, content = fetch_page(data.source_url)
        if data.title:
            title = data.title

    post = Post(
        title=title,
        content=content,
        source_url=data.source_url,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def list_posts(session: Session) -> list[Post]:
    return list(session.exec(select(Post)).all())


def get_post(session: Session, post_id: int) -> Post | None:
    return session.get(Post, post_id)