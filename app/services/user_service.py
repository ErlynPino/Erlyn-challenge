import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def create_user(session: Session, user_in: UserCreate) -> User:
    """Insert a new user row and return the persisted instance."""
    user = User(**user_in.model_dump())
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user(session: Session, user_id: uuid.UUID) -> Optional[User]:
    """Fetch a user by primary key; returns None if not found."""
    return session.get(User, user_id)


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    return session.exec(select(User).where(User.username == username)).first()


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def list_users(
    session: Session, skip: int = 0, limit: int = 10
) -> tuple[list[User], int]:
    """Return a page of users and the total count."""
    total: int = session.exec(select(func.count(User.id))).one()
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return list(users), total


def update_user(session: Session, user: User, user_in: UserUpdate) -> User:
    """Apply the provided fields to *user* and persist the change."""
    data = user_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user: User) -> None:
    """Permanently remove a user from the database."""
    session.delete(user)
    session.commit()
