from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models import Platform, VariantStatus
from app.schemas import VariantRead, VariantUpdate
from app.services import variants as variant_service
from app.services.variants import VariantError

router = APIRouter(prefix="/variants", tags=["variants"])


def _load(session: Session, variant_id: int):
    variant = variant_service.get_variant(session, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found.")
    return variant


def _unwrap(result):
    if isinstance(result, VariantError):
        detail = {"reason": result.reason}
        if result.details:
            detail["errors"] = result.details
        raise HTTPException(status_code=409, detail=detail)
    return result


@router.get("", response_model=list[VariantRead])
def list_variants(
    status: VariantStatus | None = None,
    platform: Platform | None = None,
    session: Session = Depends(get_session),
):
    return variant_service.list_variants(session, status=status, platform=platform)


@router.get("/{variant_id}", response_model=VariantRead)
def get_variant(variant_id: int, session: Session = Depends(get_session)):
    return _load(session, variant_id)


@router.patch("/{variant_id}", response_model=VariantRead)
def edit_variant(
    variant_id: int,
    data: VariantUpdate,
    session: Session = Depends(get_session),
):
    variant = _load(session, variant_id)
    return _unwrap(variant_service.edit_content(session, variant, data.content))


@router.post("/{variant_id}/approve", response_model=VariantRead)
def approve_variant(variant_id: int, session: Session = Depends(get_session)):
    variant = _load(session, variant_id)
    return _unwrap(variant_service.approve(session, variant))


@router.post("/{variant_id}/reject", response_model=VariantRead)
def reject_variant(variant_id: int, session: Session = Depends(get_session)):
    variant = _load(session, variant_id)
    return _unwrap(variant_service.reject(session, variant))