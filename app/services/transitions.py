from app.models import VariantStatus

ALLOWED_TRANSITIONS: dict[VariantStatus, set[VariantStatus]] = {
    VariantStatus.DRAFT: {VariantStatus.APPROVED, VariantStatus.REJECTED},
    VariantStatus.APPROVED: {VariantStatus.DRAFT, VariantStatus.PUBLISHED},
    VariantStatus.REJECTED: {VariantStatus.DRAFT},
    VariantStatus.PUBLISHED: set(),
}


def can_transition(current: VariantStatus, target: VariantStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition_error(current: VariantStatus, target: VariantStatus) -> str:
    allowed = ALLOWED_TRANSITIONS[current]
    if not allowed:
        return f"A {current.value} variant cannot change status."
    options = ", ".join(sorted(s.value for s in allowed))
    return (
        f"Cannot move a {current.value} variant to {target.value}. "
        f"Allowed from {current.value}: {options}."
    )