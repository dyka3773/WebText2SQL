import logging

import chainlit as cl
import psycopg as sql

logger = logging.getLogger("webtext2sql")


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
