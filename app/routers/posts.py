from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.database import get_session
from app.schemas import PostCreate, PostRead
from app.services import posts as post_service

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, session: Session = Depends(get_session)):
    return post_service.create_post(session, data)


@router.get("", response_model=list[PostRead])
def list_posts(session: Session = Depends(get_session)):
    return post_service.list_posts(session)


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, session: Session = Depends(get_session)):
    post = post_service.get_post(session, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found.")
    return post