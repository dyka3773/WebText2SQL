from sqlmodel import Session, select, text

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


def delete_user_connection_by_server_name(server_name: str, user_email: str, session: Session) -> UserConnection:
    """
    Delete a user connection by its server name and user email.

    Args:
        server_name (str): The name of the server to delete the connection for.
        user_email (str): The email of the user whose connection is to be deleted.
        session (Session): The SQLAlchemy session to use for the deletion. Defaults to None.

    Returns:
        UserConnection: The deleted UserConnection instance, or None if no connection was found.
    """
    user_connection: UserConnection = session.exec(
        select(UserConnection).where(
            UserConnection.server_name == server_name,
            UserConnection.user_email == user_email,
        ),
    ).one()

    if user_connection:
        user_id_query = text("SELECT id FROM \"user\" WHERE identifier = :identifier")
        user_id = session.exec(user_id_query, {"identifier": user_email}).one()
        thread_delete_statement = text("DELETE FROM thread WHERE \"userId\" = :user_id AND name LIKE :server_name")
        session.exec(thread_delete_statement, {"user_id": user_id, "server_name": f"%{server_name}%"})
        session.delete(user_connection)

    session.commit()

    return user_connection
