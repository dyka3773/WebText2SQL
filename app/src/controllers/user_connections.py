from sqlmodel import Session, select

from .models import UserConnection


def get_user_connections_by_email(email: str, session: Session) -> list[UserConnection]:
    """
    Retrieve all user connections associated with a given email address.

    Args:
        email (str): The email address of the user.
        session (Session): The SQLAlchemy session to use for the query. Defaults to None.

    Returns:
        list[UserConnection]: A list of UserConnections related to the user given, or an empty list if no connections are found.
    """
    return session.exec(select(UserConnection).where(UserConnection.user_email == email)).all() or []


def insert_user_connection(user_connection: UserConnection, session: Session) -> UserConnection:
    """
    Insert a new user connection into the database.

    Args:
        user_connection (UserConnection): An instance of the UserConnection class to be inserted.
        session (Session): The SQLAlchemy session to use for the insertion. Defaults to None.

    Returns:
        UserConnection: The inserted UserConnection instance with its ID populated.
    """
    # Possible TODO: Check if the user connection already exists before inserting, if it does, continue as if it was inserted

    session.add(user_connection)
    session.commit()
    return user_connection  # This user_connection doesn't have an ID yet, but we don't need it
