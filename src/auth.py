import chainlit as cl
import logging
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
    # TODO: Use the credentials of the db server they want to connect to. See #2
    if (username, password) == ("admin", "admin"):
        logger.debug(f"User {username} authenticated successfully") # TODO: Use user id instead of username for GDPR compliance
        
        try:
            connection = sql.connect(connection_string)
        except sql.Error as e:
            logger.error(f"Error connecting to the database: {e}")
            return None
        
        return cl.User(
            identifier="admin", metadata={"conn_info": connection.info.get_parameters(), "password": connection.info.password},
        )
    else:
        return None