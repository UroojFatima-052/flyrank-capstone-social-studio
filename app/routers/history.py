from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.schemas import PublishAttemptRead
from app.services import history as history_service

router = APIRouter(prefix="/publish-history", tags=["history"])


@router.get("", response_model=list[PublishAttemptRead])
def list_history(session: Session = Depends(get_session)):
    return history_service.list_attempts(session)


@router.get("/{variant_id}", response_model=list[PublishAttemptRead])
def list_history_for_variant(
    variant_id: int, session: Session = Depends(get_session)
):
    return history_service.list_attempts_for_variant(session, variant_id)