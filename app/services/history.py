from sqlmodel import Session, select

from app.models import PublishAttempt


def list_attempts(session: Session) -> list[PublishAttempt]:
    statement = select(PublishAttempt).order_by(PublishAttempt.attempted_at.desc())
    return list(session.exec(statement).all())


def list_attempts_for_variant(
    session: Session, variant_id: int
) -> list[PublishAttempt]:
    statement = (
        select(PublishAttempt)
        .where(PublishAttempt.variant_id == variant_id)
        .order_by(PublishAttempt.attempted_at.desc())
    )
    return list(session.exec(statement).all())