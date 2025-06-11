import logging
import os
from typing import TYPE_CHECKING

import chainlit as cl
import mysql.connector
import psycopg
from controllers import user_connections
from controllers.user_connections import UserConnection
from db_controllers import mysql_controller, pg_controller
from sqlmodel import Session, create_engine

if TYPE_CHECKING:
    from chainlit.types import AskActionResponse

logger: logging.Logger = logging.getLogger("webtext2sql")


def get_user_connection_info() -> dict:
    """
    Retrieve the connection information for the current user.

    Returns:
        dict: Connection information including host, port, database, user, and password.
    """
    conn_info: dict = cl.user_session.get("curr_conn_info")
    if not conn_info:
        logger.error("No connection info found for the user.")
        return {}

    return conn_info


def get_available_schemas_for_curr_server() -> list[str]:
    """
    Retrieve the names of all database schemas available to the current user.

    Returns:
        list: List of schema names.
    """
    conn_info = get_user_connection_info()
    if not conn_info:
        logger.error("No connection info found for the user.")
        return []

    # TODO #34 @dyka3773: Change this to support SSH tunnel connections if needed
    tcp_info = conn_info["tcp"].copy()
    type_of_db = tcp_info.pop("type_of_db")

    if type_of_db == "postgres":
        connection: psycopg.Connection = psycopg.connect(**tcp_info)
        # For PostgreSQL, get the list of available schemas
        return pg_controller.get_available_dbs(connection, conn_info["tcp"]["user"])

    if type_of_db == "mysql":
        connection: mysql.connector.MySQLConnection = mysql.connector.connect(**tcp_info)
        return mysql_controller.get_available_dbs(connection, conn_info["tcp"]["user"])

    return []  # Return an empty list if the database type is not recognized


async def new_connection_or_reconnect_to_schema() -> None:
    """Create a new database connection or reconnect to a previously connected schema."""
    choice_btns: list[cl.Action] = [
        cl.Action(
            name="new_connection",
            payload={"value": "new_connection"},
            label="Connect to a new database",
        ),
        cl.Action(
            name="reconnect",
            payload={"value": "reconnect"},
            label="Reconnect to a previously connected schema",
        ),
    ]
    res: AskActionResponse | None = None
    while not res:  # This is needed because sometimes the response is time-ing out and we get None
        res = await cl.AskActionMessage(
            content="Do you want to connect to a new database or reconnect to a previously connected schema?",
            actions=choice_btns,
        ).send()

    action = res.get("payload").get("value")

    if action == "new_connection":
        await handle_new_connection()
    elif action == "reconnect":
        await handle_db_selection()


async def handle_db_selection() -> None:
    """Present the user with a list of previously connected databases and allow them to select one."""
    db_engine = create_engine(os.getenv("DATABASE_URL"))
    with Session(db_engine) as session:
        user_connections_list: list[UserConnection] = user_connections.get_user_connections_by_email(
            email=cl.user_session.get("user").identifier,
            session=session,
        )
        if not user_connections_list:
            await cl.Message(
                content="You have no previously connected databases. Please connect to a new database.",
            ).send()
            await handle_new_connection()
            return

    # Create action buttons for each previously connected database
    db_btns: list[cl.Action] = [
        cl.Action(
            name=f"{conn.server_name} Queries",
            payload={
                "value": {
                    "type": "ssh" if conn.ssh_connection_info else "tcp",
                    "ssh": conn.ssh_connection_info,
                    "tcp": conn.tcp_connection_info,
                }
            },
            label=f"{conn.server_name}",
        )
        for conn in user_connections_list
    ]

    # Step 1: Send a blocking message to the user with the list of available databases
    res: AskActionResponse | None = None
    while not res:  # This is needed because sometimes the response is time-ing out and we get None
        res = await cl.AskActionMessage(
            content="Please choose a previously connected database to work with:",
            actions=db_btns,
        ).send()

    # Step 2: Get the selected database connection info from the action payload
    selected_conn_info = res.get("payload").get("value")
    if selected_conn_info:
        # Step 3: Set the selected connection info as a context variable for this user
        cl.user_session.set("curr_conn_info", selected_conn_info)

        # TODO #36 @dyka3773: If we're working with MySQL there are no schemas
        await handle_schema_selection()


async def handle_new_connection() -> None:
    """Handle the creation of a new database connection."""
    # Ask the user if they want TCP/IP or SSH connection
    connection_type_btns: list[cl.Action] = [
        cl.Action(
            name="tcp",
            payload={"value": "tcp"},
            label="TCP/IP Connection",
        ),
        cl.Action(
            name="ssh",
            payload={"value": "ssh"},
            label="SSH Tunnel Connection",
        ),
    ]

    res: AskActionResponse | None = None
    while not res:  # This is needed because sometimes the response is time-ing out and we get None
        res = await cl.AskActionMessage(
            content="Do you want to connect to the database using a TCP/IP connection or an SSH tunnel?",
            actions=connection_type_btns,
        ).send()

    connection_type = res.get("payload").get("value")

    await ask_and_store_connection_details(connection_type)

    # TODO: check here if the connection was successful and if not, ask the user to try again

    await handle_schema_selection()


async def ask_and_store_connection_details(connection_type: str) -> None:
    """Handle the connection to the database by asking for the necessary information and then storing it."""
    if connection_type not in ["tcp", "ssh"]:
        await cl.Message(content="Invalid connection type selected. Please try again.").send()
        return

    conn_info: dict = {}

    if connection_type == "ssh":
        # Ask for SSH and TCP connection details
        # Note: The SSH connection info will be used to create a tunnel to the database server
        conn_info["ssh"] = await ask_for_the_ssh_connection_info()
        conn_info["tcp"] = await ask_for_the_tcp_connection_info()
    elif connection_type == "tcp":
        conn_info["tcp"] = await ask_for_the_tcp_connection_info()

    conn_info["type"] = connection_type

    can_establish_connection: bool = False

    if conn_info["tcp"].get("type_of_db") == "postgres":
        can_establish_connection = pg_controller.try_establish_connection(conn_info)
    elif conn_info["tcp"].get("type_of_db") == "mysql":
        can_establish_connection = mysql_controller.try_establish_connection(conn_info)

    if not can_establish_connection:
        await cl.Message(content="Failed to establish a connection with the provided information. Please try again.").send()
        return

    # Save the connection info in the user session
    cl.user_session.set("curr_conn_info", conn_info)

    # Save the connection info in the database
    db_engine = create_engine(os.getenv("DATABASE_URL"))

    with Session(db_engine) as session:
        user_connections.insert_user_connection(
            user_connection=UserConnection(
                user_email=cl.user_session.get("user").identifier,
                server_name=conn_info["tcp"].get("host", "unknown_server"),
                ssh_connection_info=conn_info["ssh"] if connection_type == "ssh" else {},
                tcp_connection_info=conn_info["tcp"] if connection_type == "tcp" else {},
            ),
            session=session,
        )


async def handle_schema_selection() -> None:
    """Handle the schema selection by the user."""
    # Get the list of available database schemas from the database controller
    db_list = get_available_schemas_for_curr_server()
    if not db_list:
        logger.error(f"No database schemas found for the user: {cl.user_session.get('curr_conn_info').get('tcp', {}).get('user')}")
        await cl.Message(content="No database schemas found for you on this database server. Please try again.").send()
        return

    # Create action buttons for each schema
    schema_btns: list[cl.Action] = [
        cl.Action(
            name=f"{db_name} Queries",
            payload={"value": db_name},
            label=f"{db_name}",
        )
        for db_name in db_list
    ]

    # Step 1: Send a blocking message to the user with the list of available schemas
    res: AskActionResponse | None = None
    while not res:  # This is needed because sometimes the response is time-ing out and we get None
        res = await cl.AskActionMessage(
            content="Please choose a database schema to work with before sending any messages:",
            actions=schema_btns,
        ).send()

    # Step 2: Get the selected schema name from the action payload
    schema_to_work_with = res.get("payload").get("value")
    if schema_to_work_with:
        # Step 3: Set the selected schema as a context variable for this user
        cl.user_session.set("curr_db_schema", schema_to_work_with)

        # Step 4: Send a message to the user confirming the selection
        await cl.Message(
            content=f"You have selected the schema: \n**{schema_to_work_with}**\n\nNow you can ask me any question about this database, and I will provide you with the SQL query to get the answer.",
        ).send()
    else:
        await cl.Message(content="No database selected. Please choose a database to work with.").send()


async def ask_for_the_ssh_connection_info() -> dict:
    """
    Ask the user for SSH connection details and return them as a dictionary.

    Returns:
        dict: A dictionary containing the SSH connection details.
    """
    ssh_info: dict = {}

    ssh_host = await cl.AskUserMessage(
        content="Please enter the SSH host (e.g., `ssh.example.com`):",
    ).send()

    ssh_port = await cl.AskUserMessage(
        content="Please enter the SSH port (e.g., `22`):",
    ).send()

    ssh_user = await cl.AskUserMessage(
        content="Please enter the SSH username:",
    ).send()

    ssh_password = await cl.AskUserMessage(
        content="Please enter the SSH password:",
    ).send()

    ssh_info["ssh_host"] = ssh_host.get("output")
    ssh_info["ssh_port"] = int(ssh_port.get("output"))
    ssh_info["ssh_user"] = ssh_user.get("output")
    ssh_info["ssh_password"] = ssh_password.get("output")

    return ssh_info


async def ask_for_the_tcp_connection_info() -> dict:
    """
    Ask the user for TCP connection details and return them as a dictionary.

    Returns:
        dict: A dictionary containing the TCP connection details.
    """
    tcp_info: dict = {}

    host = await cl.AskUserMessage(
        content="Please enter the database host or IP address (e.g., `db.example.com` or `127.0.0.1`):",
    ).send()

    port = await cl.AskUserMessage(
        content="Please enter the database port (e.g., `5432` or `3306`):",
    ).send()

    type_of_db = await cl.AskActionMessage(
        content="Please select the type of database you are connecting to:",
        actions=[
            cl.Action(name="postgres", payload={"value": "postgres"}, label="PostgreSQL"),
            cl.Action(name="mysql", payload={"value": "mysql"}, label="MySQL"),
        ],
    ).send()

    # PostgreSQL has an additional layer of abstraction in a database server. It distinguishes between databases and schemas while MySQL does not.
    if type_of_db.get("payload").get("value") == "postgres":
        dbname = await cl.AskUserMessage(
            content="Please enter the database name:",
        ).send()

        tcp_info["dbname"] = dbname.get("output")

    user = await cl.AskUserMessage(
        content="Please enter the database username:",
    ).send()

    password = await cl.AskUserMessage(
        content="Please enter the database password:",
    ).send()

    tcp_info["host"] = host.get("output")
    tcp_info["port"] = int(port.get("output"))
    tcp_info["user"] = user.get("output")
    tcp_info["password"] = password.get("output")
    tcp_info["type_of_db"] = type_of_db.get("payload").get("value")

    return tcp_info
