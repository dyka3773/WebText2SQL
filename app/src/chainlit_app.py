import os

import chainlit as cl
import custom_logging
import mysql.connector
import psycopg
from chainlit.types import ThreadDict
from dotenv import load_dotenv
from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired
from sqlmodel import Session, create_engine

logger = custom_logging.setup_logger("webtext2sql")
custom_logging.setup_logger("chainlit")

import ai_controller
import chainlit_controller
import str_manipulation
from controllers import app_users
from db_controllers import mysql_controller, pg_controller
from main import COOKIE_NAME, serializer

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
    await chainlit_controller.new_connection_or_reconnect_to_schema()


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    """
    Handle incoming messages in each chat.
    This function is triggered whenever a message is sent in the chat.

    Args:
        message (cl.Message): The incoming message object.
    """
    logger.debug(f"Received message: {message.content}")

    # Step 1: Find Metadata from db according to the user
    conn_info = chainlit_controller.get_user_connection_info()
    # TODO #34 @dyka3773: Change this to support SSH tunnel connections if needed
    tcp_details = conn_info["tcp"].copy()
    tcp_details.pop("type_of_db", None)  # Remove the type_of_db key if it exists, as mysql.connector does not use it

    schema = cl.user_session.get("curr_db_schema")

    logger.debug("Fetching metadata from the database")

    metadata: list[str] = []

    if conn_info["tcp"].get("type_of_db") == "postgres":
        connection: psycopg.Connection = psycopg.connect(
            **tcp_details,
        )

        metadata = pg_controller.get_db_metadata(connection, schema, tcp_details["user"])

    elif conn_info["tcp"].get("type_of_db") == "mysql":
        connection: mysql.connector.MySQLConnection = mysql.connector.connect(
            **tcp_details,
        )

        metadata = mysql_controller.get_db_metadata(connection, schema)

    meta_str = "\n".join(metadata)

    template = f"""This is my db structure:
    {meta_str}

    Please answer only with the SQL query (without any text formatting) that answers the following question:
    {message.content}

    Keep in mind that the database is a {"PostgreSQL" if conn_info["tcp"].get("type_of_db") == "postgres" else "MySQL"} database and that the schema is {schema} and it should be used in the SQL query.
    Unless explicitly stated, please limit the number of rows returned to 30.
    """
    # Step 2: Send user's query to AI & get the response from AI in the form of an SQL query
    response = await ai_controller.get_ai_response(template)

    logger.debug(f"AI's response: {response}")

    # TODO @dyka3773: Wrap below until Step 4 in a function to make it cleaner
    sql_query = str_manipulation.extract_sql_only(response)
    logger.debug(f"Extracted SQL query: {sql_query}")
    if not sql_query:
        logger.error("The AI model did not return a valid SQL query.")
        await cl.Message(content="The AI model did not return a valid SQL query.").send()
        return

    results: tuple[tuple] = ()
    col_names: tuple[str] = ()

    # Step 3: Execute the SQL query against the database
    if conn_info["tcp"].get("type_of_db") == "postgres":
        results, col_names = pg_controller.fetch_data(sql_query, connection)
    elif conn_info["tcp"].get("type_of_db") == "mysql":
        # For MySQL, we need to use a different controller
        results, col_names = mysql_controller.fetch_data(sql_query, connection)

    # Step 4: Format the data into a user-friendly format before and sending it back to the user
    answer = str_manipulation.form_answer(results, col_names, sql_query)

    # Step 5: Send the response back to the user
    await cl.Message(content=answer).send()
