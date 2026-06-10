from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self.db.scalar(statement)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def get_by_google_sub(self, google_sub: str) -> User | None:
        statement = select(User).where(User.google_sub == google_sub)
        return self.db.scalar(statement)

    def create(
        self,
        *,
        email: str,
        user_id: UUID | None = None,
        password_hash: str | None = None,
        google_sub: str | None = None,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        user_values = {
            "email": email,
            "password_hash": password_hash,
            "google_sub": google_sub,
            "full_name": full_name,
            "avatar_url": avatar_url,
        }
        if user_id is not None:
            user_values["id"] = user_id

        user = User(**user_values)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, values: dict[str, object]) -> User:
        for field, value in values.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)
        return user
