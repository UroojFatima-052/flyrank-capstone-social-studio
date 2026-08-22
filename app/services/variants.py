from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import Platform, Variant, VariantStatus, utcnow
from app.services.transitions import can_transition, transition_error
from app.services.validator import validate_variant


@dataclass
class VariantError:
    reason: str
    details: list[str] | None = None


def get_variant(session: Session, variant_id: int) -> Variant | None:
    return session.get(Variant, variant_id)


def list_variants(
    session: Session,
    status: VariantStatus | None = None,
    platform: Platform | None = None,
) -> list[Variant]:
    statement = select(Variant)
    if status is not None:
        statement = statement.where(Variant.status == status)
    if platform is not None:
        statement = statement.where(Variant.platform == platform)
    return list(session.exec(statement).all())


def set_status(
    session: Session, variant: Variant, target: VariantStatus
) -> Variant | VariantError:
    if not can_transition(variant.status, target):
        return VariantError(reason=transition_error(variant.status, target))

    variant.status = target
    variant.updated_at = utcnow()
    session.add(variant)
    session.commit()
    session.refresh(variant)
    return variant


def approve(session: Session, variant: Variant) -> Variant | VariantError:
    return set_status(session, variant, VariantStatus.APPROVED)


def reject(session: Session, variant: Variant) -> Variant | VariantError:
    return set_status(session, variant, VariantStatus.REJECTED)


def edit_content(
    session: Session, variant: Variant, content: str
) -> Variant | VariantError:
    if variant.status == VariantStatus.PUBLISHED:
        return VariantError(reason="A published variant cannot be edited.")

    result = validate_variant(content, variant.platform)
    if not result.valid:
        return VariantError(
            reason="Edited content breaks the platform's constraint profile.",
            details=result.errors,
        )

    variant.content = content
    variant.status = VariantStatus.DRAFT
    variant.updated_at = utcnow()
    session.add(variant)
    session.commit()
    session.refresh(variant)
    return variant