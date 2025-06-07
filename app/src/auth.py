import logging

import chainlit as cl
import psycopg as sql
from passlib.context import CryptContext

logger = logging.getLogger("webtext2sql")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# TODO @dyka3773: Replace this function with authentication against a database. To be used by FastAPI from now on.
def authenticate_user(username: str, password: str, connection_string: str) -> cl.User | None:
    """
    Authenticate a user with the given username and password.

    Args:
        username (str): The username of the user.
        password (str): The password of the user.
        connection_string (str): The connection string to the database.

    Returns:
        cl.User: An instance of the User class if authentication is successful, None otherwise.
    """
    try:
        # Check if the username and password are present
        if not username or not password:
            msg = "Username and password cannot be empty"
            raise ValueError(msg)

        connection = sql.connect(f"postgresql://{username}:{password}@{connection_string}")
        logger.debug(f"User {username} authenticated successfully")

        return cl.User(
            identifier=f"{username}",
            metadata={"conn_info": connection.info.get_parameters(), "password": connection.info.password},
        )
    except sql.Error as e:
        logger.warning(f"The following user failed to authenticate: {username}. Error: {e}")
        return None
    finally:
        if connection:
            connection.close()
            logger.debug(f"Connection closed for user {username}")


def hash_password(password_given: str) -> str:
    """
    Hash a given password using bcrypt.

    Args:
        password_given (str): The password to be hashed.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password_given)


def verify_password(password_given: str, actual_encrypted_password: str) -> bool:
    """
    Verify a given password against an actual encrypted password.

    Args:
        password_given (str): The password to verify.
        actual_encrypted_password (str): The actual encrypted password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(password_given, actual_encrypted_password)
