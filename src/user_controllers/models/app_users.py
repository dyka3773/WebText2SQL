import datetime
import uuid

from sqlmodel import Field, SQLModel


class AppUser(SQLModel, table=True):
    """Model representing an application user."""

    __tablename__ = "APP_USERS"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: str = Field(default_factory=datetime.datetime.now, nullable=False)
    email: str = Field(default=None, nullable=False, index=True, unique=True)
    username: str = Field(default=None, nullable=False)
    hashed_password: str = Field(default=None, nullable=False)
    chat_context_allowed: bool = Field(default=True, nullable=False)
