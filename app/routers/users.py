import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.database import get_session
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="Return a paginated list of all users.",
)
def list_users(
    session: SessionDep,
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max records to return"),
) -> UserListResponse:
    users, total = user_service.list_users(session, skip=skip, limit=limit)
    logger.info("Listed %d users (skip=%d, limit=%d)", len(users), skip, limit)
    return UserListResponse(total=total, skip=skip, limit=limit, data=users)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user. `username` and `email` must be unique.",
)
def create_user(session: SessionDep, user_in: UserCreate) -> UserResponse:
    if user_service.get_user_by_username(session, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_in.username}' is already taken.",
        )
    if user_service.get_user_by_email(session, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_in.email}' is already registered.",
        )
    try:
        user = user_service.create_user(session, user_in)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists.",
        )
    logger.info("Created user id=%s username=%s", user.id, user.username)
    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a single user by their UUID.",
)
def get_user(user_id: uuid.UUID, session: SessionDep) -> UserResponse:
    user = user_service.get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Full update user",
    description="Replace all updatable fields of an existing user.",
)
def full_update_user(
    user_id: uuid.UUID, session: SessionDep, user_in: UserUpdate
) -> UserResponse:
    user = user_service.get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if user_in.username and user_in.username != user.username:
        if user_service.get_user_by_username(session, user_in.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken.",
            )
    if user_in.email and user_in.email != user.email:
        if user_service.get_user_by_email(session, user_in.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )
    try:
        updated = user_service.update_user(session, user, user_in)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists.",
        )
    logger.info("Updated (PUT) user id=%s", user_id)
    return updated


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Partial update user",
    description="Update only the provided fields of an existing user.",
)
def partial_update_user(
    user_id: uuid.UUID, session: SessionDep, user_in: UserUpdate
) -> UserResponse:
    user = user_service.get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if user_in.username and user_in.username != user.username:
        if user_service.get_user_by_username(session, user_in.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken.",
            )
    if user_in.email and user_in.email != user.email:
        if user_service.get_user_by_email(session, user_in.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered.",
            )
    try:
        updated = user_service.update_user(session, user, user_in)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists.",
        )
    logger.info("Updated (PATCH) user id=%s", user_id)
    return updated


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Permanently delete a user by their UUID.",
)
def delete_user(user_id: uuid.UUID, session: SessionDep) -> None:
    user = user_service.get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    user_service.delete_user(session, user)
    logger.info("Deleted user id=%s", user_id)
