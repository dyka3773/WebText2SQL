import logging
from typing import TYPE_CHECKING

import chainlit as cl
import psycopg as sql

import db_controller

if TYPE_CHECKING:
    from chainlit.types import AskActionResponse

logger: logging.Logger = logging.getLogger("webtext2sql")


def get_user_connection_info() -> dict:
    """
    Retrieve the connection information for the current user.

    Returns:
        dict: Connection information including host, port, database, user, and password.
    """
    user = cl.user_session.get("user")
    if not user:
        logger.error("User not found in session.")
        return {}

    conn_info: dict = user.metadata["conn_info"]
    password: str = user.metadata["password"]

    if not conn_info or not password:
        logger.error("Connection info or password not found in session.")
        return {}

    conn_info["password"] = password
    return conn_info


def get_available_schemas_for_curr_user() -> list[str]:
    """
    Retrieve the names of all database schemas available to the current user.

    Returns:
        list: List of schema names.
    """
    conn_info = get_user_connection_info()
    if not conn_info:
        logger.error("No connection info found for the user.")
        return []

    connection = sql.connect(**conn_info)

    return db_controller.get_available_dbs(connection, conn_info["user"])


async def handle_schema_selection(schema_btns: list[cl.Action]) -> None:
    """
    Handle the schema selection by the user.

    Args:
        schema_btns (list[cl.Action]): List of schema buttons to be displayed to the user.
    """
    # Step 1: Send a blocking message to the user with the list of available schemas
    res: AskActionResponse | None = await cl.AskActionMessage(
        content="Please choose a database schema to work with before sending any messages:",
        actions=schema_btns,
    ).send()

    # Step 2: Get the selected schema name from the action payload
    schema_to_work_with = res.get("payload").get("value")
    if schema_to_work_with:
        # Step 3: Set the selected schema as a context variable for this user
        cl.user_session.set("db_schema", schema_to_work_with)

        # Step 4: Send a message to the user confirming the selection
        await cl.Message(
            content=f"You have selected the schema: \n**{schema_to_work_with}**\n\nNow you can ask me any question about this database, and I will provide you with the SQL query to get the answer.",
        ).send()
    else:
        await cl.Message(content="No database selected. Please choose a database to work with.").send()
