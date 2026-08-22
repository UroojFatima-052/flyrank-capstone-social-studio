from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.schemas import CampaignCreate, CampaignDetail, CampaignRead, GenerationReport
from app.services import campaigns as campaign_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(data: CampaignCreate, session: Session = Depends(get_session)):
    result = campaign_service.create_campaign(session, data)
    if isinstance(result, str):
        code = 404 if result == "Post not found." else 409
        raise HTTPException(status_code=code, detail=result)
    return result

@router.get("", response_model=list[CampaignRead])
def list_campaigns(session: Session = Depends(get_session)):
    return campaign_service.list_campaigns(session)


@router.get("/{campaign_id}", response_model=CampaignDetail)
def get_campaign(campaign_id: int, session: Session = Depends(get_session)):
    campaign = campaign_service.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    variants = campaign_service.get_campaign_variants(session, campaign_id)
    return CampaignDetail(
        id=campaign.id,
        post_id=campaign.post_id,
        name=campaign.name,
        status=campaign.status,
        created_at=campaign.created_at,
        variants=variants,
    )


@router.post("/{campaign_id}/variants", response_model=GenerationReport)
def generate_variants(campaign_id: int, session: Session = Depends(get_session)):
    result = campaign_service.generate_variants(session, campaign_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    created, skipped, failed = result
    return GenerationReport(
        campaign_id=campaign_id,
        created=created,
        skipped=skipped,
        failed=failed,
    )