from sqlmodel import Session, select

from .models import AppUser


def get_app_user_by_email(email: str, session: Session = None) -> AppUser | None:
    """
    Retrieve an application user by their email address.

    Args:
        email (str): The email address of the user.
        session (Session, optional): The SQLAlchemy session to use for the query. Defaults to None.

    Returns:
        AppUser: An instance of the AppUser class if found, None otherwise.
    """
    return session.exec(select(AppUser).where(AppUser.email == email)).first()


def insert_app_user(user: AppUser, session: Session = None) -> AppUser:
    """
    Insert a new application user into the database.

    Args:
        user (AppUser): An instance of the AppUser class to be inserted.
        session (Session, optional): The SQLAlchemy session to use for the insertion. Defaults to None.

    Returns:
        AppUser: The inserted AppUser instance with its ID populated.
    """
    session.add(user)
    session.commit()
    return user  # This user doesn't have an ID yet, but we don't need it


def app_user_exists(email: str, session: Session = None) -> bool:
    """
    Check if an application user exists by their email address.

    Args:
        email (str): The email address of the user.
        session (Session, optional): The SQLAlchemy session to use for the query. Defaults to None.

    Returns:
        bool: True if the user exists, False otherwise.
    """
    return get_app_user_by_email(email, session) is not None


def is_user_allowed_to_use_chat_context(email: str, session: Session = None) -> bool:
    """
    Check if a user is allowed to use chat context.

    Args:
        email (str): The email address of the user.
        session (Session, optional): The SQLAlchemy session to use for the query. Defaults to None.

    Returns:
        bool: True if the user is allowed to use chat context, False otherwise.
    """
    user = get_app_user_by_email(email, session)
    return user.chat_context_allowed if user else False
