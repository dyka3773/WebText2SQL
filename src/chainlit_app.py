import os

import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv
from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired
from sqlmodel import Session, create_engine

import custom_logging

logger = custom_logging.setup_logger("webtext2sql")
custom_logging.setup_logger("chainlit")



import chainlit_controller
import str_manipulation
from main import COOKIE_NAME, serializer
from user_controllers import app_users

load_dotenv()

cl.instrument_openai()


@cl.header_auth_callback
def auth_from_header(headers: dict) -> None | cl.User:
    """
    Authenticate a user based on the session cookie in the request headers.

    Args:
        headers (dict): The request headers containing the session cookie.

    Returns:
        None | cl.User: Returns a User object if authentication is successful, None otherwise.
    """
    cookie = headers.get("cookie")
    if not cookie or COOKIE_NAME not in cookie:
        return None

    try:
        # Parse cookie manually
        cookies = dict(pair.split("=", 1) for pair in cookie.split("; "))
        token = cookies.get(COOKIE_NAME)
        email = serializer.loads(token, max_age=60 * 60 * 24)

        if not email:  # I think this is redundant (due to the exception handling), but just in case
            logger.warning("Session cookie is invalid or expired.")
            return None

        db_engine = create_engine(os.getenv("DATABASE_URL"))

        with Session(db_engine) as session:
            user: app_users.AppUser | None = app_users.get_app_user_by_email(email, session)

            if not user:
                logger.warning(f"User {email} not found in the database.")
                return None

            return cl.User(
                identifier=email,
                metadata={
                    "token": token,
                    "curr_conn_info": None,
                },
            )

    except (BadSignature, SignatureExpired):
        logger.exception("Invalid or expired session cookie.")
        return None


@cl.on_logout
def logout(_: Request, response: Response) -> None:
    """
    Clear the user's session cookie when they log out.
    This function is triggered when a user logs out of the application.

    Args:
        request (Request): The request object containing the user's session data.
        response (Response): The response object to modify the user's session cookie.
    """
    response.delete_cookie(COOKIE_NAME)


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """
    Handle the event when a chat is resumed.
    This function is triggered when a user resumes a chat session.

    Args:
        thread: The thread object representing the chat session.
    """
    logger.debug(f"Chat resumed: {thread['id']} by User: {thread['userId']}")


@cl.on_chat_start
async def new_thread_opened() -> None:
    """
    Create a new database connection or connect to a previously connected schema.
    This function is triggered when a new chat session begins.

    Args:
        thread: The thread object representing the chat session.
    """
    logger.debug(f"Chat started by User: {cl.user_session.get('user').identifier}")
    await chainlit_controller.new_connection_reconnect_or_delete_connection()


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """
    Handle incoming messages in each chat.
    This function is triggered whenever a message is sent in the chat.

    Args:
        message (cl.Message): The incoming message object.
    """
    logger.debug(f"Received message: {message.content}")

    conn_info = chainlit_controller.get_user_connection_info()
    schema = cl.user_session.get("curr_db_schema")

    db_controller, metadata, tunnel = chainlit_controller.get_db_controller_and_metadata(conn_info, schema)
    sql_query = await chainlit_controller.get_ai_sql_query(message, conn_info, metadata, schema)

    if not sql_query:
        logger.error("The AI model did not return a valid SQL query.")
        await cl.Message(content="The AI model did not return a valid SQL query.").send()
        return

    results, col_names = db_controller.execute_query(sql_query)

    if tunnel:
        tunnel.stop()
        logger.debug("SSH tunnel closed")

    answer = str_manipulation.form_answer(results, col_names, sql_query)
    await cl.Message(content=answer).send()
