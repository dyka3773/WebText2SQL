import datetime
import uuid

from sqlmodel import JSON, Column, Field, SQLModel


class UserConnection(SQLModel, table=True):
    """Model representing a connection to a database for a user."""

    __tablename__ = "USER_CONNECTIONS"

    id: str = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: str = Field(default_factory=datetime.datetime.now, nullable=False)
    user_email: str = Field(default=None, nullable=False, index=True, foreign_key="APP_USERS.email")
    server_name: str = Field(default=None, nullable=False, index=True)
    ssh_connection_info: dict = Field(default_factory=dict, sa_column=Column(JSON))
    tcp_connection_info: dict = Field(default_factory=dict, sa_column=Column(JSON))
    type_of_db: str = Field(default=None, nullable=False, index=True)
