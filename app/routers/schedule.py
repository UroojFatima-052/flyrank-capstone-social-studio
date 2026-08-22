from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.schemas import ScheduleCreate, ScheduleSlotRead
from app.services import schedule as schedule_service
from app.services import variants as variant_service
from app.services.variants import VariantError

router = APIRouter(tags=["schedule"])


@router.post(
    "/variants/{variant_id}/schedule",
    response_model=ScheduleSlotRead,
    status_code=status.HTTP_201_CREATED,
)
def schedule_variant(
    variant_id: int,
    data: ScheduleCreate,
    session: Session = Depends(get_session),
):
    variant = variant_service.get_variant(session, variant_id)
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found.")

    result = schedule_service.schedule_variant(session, variant, data.scheduled_for)
    if isinstance(result, VariantError):
        raise HTTPException(status_code=409, detail={"reason": result.reason})
    return result


@router.get("/schedule", response_model=list[ScheduleSlotRead])
def list_slots(session: Session = Depends(get_session)):
    return schedule_service.list_slots(session)


@router.delete("/schedule/{slot_id}", response_model=ScheduleSlotRead)
def cancel_slot(slot_id: int, session: Session = Depends(get_session)):
    slot = schedule_service.cancel_slot(session, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found.")
    return slot