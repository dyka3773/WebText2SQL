import logging
import os
from copy import deepcopy
from typing import TYPE_CHECKING

import chainlit as cl
import chainlit.data as cl_data
from sqlmodel import Session, create_engine
from sshtunnel import SSHTunnelForwarder

import ai_controller
import connection_controller
import str_manipulation
from connection_factory import get_db_controller
from db_controllers.base_db_controller import BaseDBController
from user_controllers import user_connections
from user_controllers.user_connections import UserConnection

if TYPE_CHECKING:
    from chainlit.step import StepDict
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

    available_dbs = []

    conn_details = deepcopy(conn_info)

    if conn_info.get("type") == "ssh":
        tunnel = SSHTunnelForwarder(
            ssh_address_or_host=(conn_info["ssh"]["ssh_host"], conn_info["ssh"]["ssh_port"]),
            ssh_username=conn_info["ssh"]["ssh_user"],
            ssh_password=conn_info["ssh"]["ssh_password"],
            remote_bind_address=(conn_info["tcp"]["host"], conn_info["tcp"]["port"]),
            local_bind_address=("127.0.0.1", 0),  # Let OS pick a free local port
            logger=logger,
        )
        tunnel.start()

        conn_details["tcp"]["host"] = "127.0.0.1"
        conn_details["tcp"]["port"] = tunnel.local_bind_port

    # Get the database controller for the current connection type
    db_controller = get_db_controller(
        db_type=conn_info["type_of_db"],
        tcp_details=conn_details["tcp"],
    )
    # Get the available schemas from the database controller
    available_dbs = db_controller.get_available_dbs()

    if conn_info.get("type") == "ssh":
        tunnel.stop()

    return available_dbs


async def new_connection_reconnect_or_delete_connection() -> None:
    """Create a new database connection, reconnect to a previously connected one, or delete an existing connection."""
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
        cl.Action(
            name="delete_connection",
            payload={"value": "delete_connection"},
            label="Delete an existing connection",
        ),
    ]
    res: AskActionResponse | None = await cl.AskActionMessage(
        content="Do you want to connect to a new database or reconnect to a previously connected schema?",
        actions=choice_btns,
        timeout=31_536_000,
    ).send()

    action = res.get("payload").get("value")

    if action == "new_connection":
        await handle_new_connection()
    elif action == "reconnect":
        await handle_db_selection()
    elif action == "delete_connection":
        await handle_delete_connection()


async def handle_delete_connection() -> None:
    """Handle the deletion of a previously connected database."""
    db_btns = await _get_db_buttons_of_user_connections()

    if not db_btns:
        await cl.Message(
            content="You have no previously connected databases to delete. Please connect to a new database.",
        ).send()
        await handle_new_connection()
        return

    # Step 1: Send a blocking message to the user with the list of available databases
    res: AskActionResponse | None = await cl.AskActionMessage(
        content="Please choose a previously connected database to delete:",
        actions=db_btns,
        timeout=31_536_000,
    ).send()

    # Step 2: Get the selected database connection ID from the action payload
    selected_conn: str = res.get("payload").get("value")
    if selected_conn:
        # Step 3: Delete the selected connection from the database
        db_engine = create_engine(os.getenv("DATABASE_URL"))
        with Session(db_engine) as session:
            user_connections.delete_user_connection_by_server_name(
                session=session,
                user_email=cl.user_session.get("user").identifier,
                server_name=selected_conn.get("server_name"),
            )

        await cl.Message(content="Connection deleted successfully!").send()

    # Step 4: Ask the user if they want to reconnect or create a new connection
    await new_connection_reconnect_or_delete_connection()


async def handle_db_selection() -> None:
    """Present the user with a list of previously connected databases and allow them to select one."""
    db_btns = await _get_db_buttons_of_user_connections()

    if not db_btns:
        await cl.Message(
            content="You have no previously connected databases. Please connect to a new database.",
        ).send()
        await handle_new_connection()
        return

    # Step 1: Send a blocking message to the user with the list of available databases
    res: AskActionResponse | None = await cl.AskActionMessage(
        content="Please choose a previously connected database to work with:",
        actions=db_btns,
        timeout=31_536_000,
    ).send()

    # Step 2: Get the selected database connection info from the action payload
    selected_conn_info: dict = res.get("payload").get("value")
    if selected_conn_info:
        server_name: str = selected_conn_info.pop("server_name")

        # Step 3: Set the selected connection info as a context variable for this user
        cl.user_session.set("curr_conn_info", selected_conn_info)

        # Change the current thread name to reflect the current connection
        thread_name = f"{server_name} - {selected_conn_info['tcp'].get('user', 'unknown_user')}"
        await change_thread_name(thread_name)

        await handle_schema_selection()


async def _get_db_buttons_of_user_connections() -> list[cl.Action]:
    db_engine = create_engine(os.getenv("DATABASE_URL"))

    with Session(db_engine) as session:
        user_connections_list: list[UserConnection] = user_connections.get_user_connections_by_email(
            email=cl.user_session.get("user").identifier,
            session=session,
        )

    # Create action buttons for each previously connected database
    db_btns: list[cl.Action] = [
        cl.Action(
            name=f"{conn.server_name}",
            payload={
                "value": {
                    "type": "ssh" if conn.ssh_connection_info else "tcp",
                    "ssh": conn.ssh_connection_info,
                    "tcp": conn.tcp_connection_info,
                    "type_of_db": conn.type_of_db,
                    "server_name": conn.server_name,
                },
            },
            label=f"{conn.server_name}",
        )
        for conn in user_connections_list
    ]

    return db_btns


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

    res: AskActionResponse | None = await cl.AskActionMessage(
        content="Do you want to connect to the database using a TCP/IP connection or an SSH tunnel?",
        actions=connection_type_btns,
        timeout=31_536_000,
    ).send()

    connection_type = res.get("payload").get("value")

    connection_established: bool = False
    while not connection_established:
        # Ask for the connection details and store them
        connection_established = await ask_and_store_connection_details(connection_type)

    await handle_schema_selection()


async def ask_and_store_connection_details(connection_type: str) -> bool:
    """
    Handle the connection to the database by asking for the necessary information and then storing it.

    Args:
        connection_type (str): The type of connection to establish, either "tcp" or "ssh".

    Returns:
        bool: True if the connection was established successfully, False otherwise.
    """
    if connection_type not in ["tcp", "ssh"]:
        await cl.Message(content="Invalid connection type selected. Please try again.").send()
        return False

    conn_info: dict = {}
    conn_info["type"] = connection_type

    connection_name: str = ""

    if connection_type == "ssh":
        # Ask for SSH and TCP connection details
        # Note: The SSH connection info will be used to create a tunnel to the database server
        conn_info["ssh"] = await ask_for_the_ssh_connection_info()
        conn_info["tcp"], conn_info["type_of_db"], connection_name = await ask_for_the_tcp_connection_info()
    elif connection_type == "tcp":
        conn_info["tcp"], conn_info["type_of_db"], connection_name = await ask_for_the_tcp_connection_info()

    can_establish_connection: bool = connection_controller.try_establish_connection(conn_info)

    if not can_establish_connection:
        await cl.Message(content="Failed to establish a connection with the provided information. Please try again.").send()
        return False

    # Save the connection info in the user session
    cl.user_session.set("curr_conn_info", conn_info)

    # Change the current thread name to reflect the current connection
    server_name = connection_name if connection_name else conn_info["tcp"].get("host")
    db_user = conn_info["tcp"].get("user")

    thread_name = f"{server_name} - {db_user}"
    await change_thread_name(thread_name)

    # Save the connection info in the database
    db_engine = create_engine(os.getenv("DATABASE_URL"))

    with Session(db_engine) as session:
        user_connections.insert_user_connection(
            user_connection=UserConnection(
                user_email=cl.user_session.get("user").identifier,
                server_name=server_name,
                ssh_connection_info=conn_info["ssh"] if connection_type == "ssh" else {},
                tcp_connection_info=conn_info["tcp"],
                type_of_db=conn_info["type_of_db"],
            ),
            session=session,
        )

    await cl.Message(content="Connection established successfully!").send()
    return True


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
    res: AskActionResponse | None = await cl.AskActionMessage(
        content="Please choose a database schema to work with before sending any messages:",
        actions=schema_btns,
        timeout=31_536_000,
    ).send()

    # Step 2: Get the selected schema name from the action payload
    schema_to_work_with = res.get("payload").get("value")
    if schema_to_work_with:
        # Step 3: Set the selected schema as a context variable for this user
        cl.user_session.set("curr_db_schema", schema_to_work_with)

        # Change the current thread name to reflect the current schema
        await append_schema_to_thread_name(schema_to_work_with)

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
        timeout=31_536_000,
    ).send()

    ssh_port = await cl.AskUserMessage(
        content="Please enter the SSH port (e.g., `22`):",
        timeout=31_536_000,
    ).send()

    ssh_user = await cl.AskUserMessage(
        content="Please enter the SSH username:",
        timeout=31_536_000,
    ).send()

    ssh_password = await cl.AskUserMessage(
        content="Please enter the SSH password:",
        timeout=31_536_000,
    ).send()

    ssh_info["ssh_host"] = ssh_host.get("output")
    ssh_info["ssh_port"] = int(ssh_port.get("output"))
    ssh_info["ssh_user"] = ssh_user.get("output")
    ssh_info["ssh_password"] = ssh_password.get("output")

    return ssh_info


async def ask_for_the_tcp_connection_info() -> tuple[dict, str, str]:
    """
    Ask the user for TCP connection details and return them as a dictionary.

    Returns:
        dict: A dictionary containing the TCP connection details.
        str: The type of database (e.g., "postgres" or "mysql").
        str: The name of the connection.
    """
    tcp_info: dict = {}

    host: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database host or IP address (e.g., `db.example.com` or `127.0.0.1`):",
        timeout=31_536_000,
    ).send()

    port: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database port (e.g., `5432` or `3306`):",
        timeout=31_536_000,
    ).send()

    type_of_db: AskActionResponse | None = await cl.AskActionMessage(
        content="Please select the type of database you are connecting to:",
        actions=[
            cl.Action(name="postgres", payload={"value": "postgres"}, label="PostgreSQL"),
            cl.Action(name="mysql", payload={"value": "mysql"}, label="MySQL"),
        ],
        timeout=31_536_000,
    ).send()

    # PostgreSQL has an additional layer of abstraction in a database server. It distinguishes between databases and schemas while MySQL does not.
    if type_of_db.get("payload").get("value") == "postgres":
        dbname = await cl.AskUserMessage(
            content="Please enter the database name:",
            timeout=31_536_000,
        ).send()

        tcp_info["dbname"] = dbname.get("output")

    user: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database username:",
        timeout=31_536_000,
    ).send()

    password: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database password:",
        timeout=31_536_000,
    ).send()

    connection_name: StepDict | None = await cl.AskUserMessage(
        content="Please enter a name for this connection (e.g., `my_db_connection`):",
        timeout=31_536_000,
    ).send()

    tcp_info["host"] = host.get("output")
    tcp_info["port"] = int(port.get("output"))
    tcp_info["user"] = user.get("output")
    tcp_info["password"] = password.get("output")
    connection_name = connection_name.get("output")
    type_of_db = type_of_db.get("payload").get("value")

    return tcp_info, type_of_db, connection_name


async def change_thread_name(thread_name: str) -> None:
    """
    Change the name of the current thread to reflect the current connection.

    Args:
        thread_name (str): The new name for the thread.
    """
    logger.debug(f"Changing thread name to: {thread_name}")

    # This is a hacky way to set the thread name in Chainlit.
    # It uses the emitter to emit that the thread name has been initialized.
    await cl.context.emitter.init_thread(thread_name)


async def append_schema_to_thread_name(schema_name: str) -> None:
    """
    Append the schema name to the current thread name.

    Args:
        schema_name (str): The name of the schema to append.
    """
    current_thread = await cl_data.get_data_layer().get_thread(cl.context.session.thread_id)
    current_thread_name = current_thread.get("name")

    new_thread_name = f"{current_thread_name} - {schema_name}"
    await change_thread_name(new_thread_name)


async def get_ai_sql_query(message: cl.Message, conn_info: dict, metadata: list[str], schema: str, context: list[dict]) -> str:
    """
    Get the SQL query from the AI model.

    Args:
        message (cl.Message): The user's message.
        conn_info (dict): The connection information.
        metadata (list[str]): The database metadata.
        schema (str): The database schema.
        context (list[dict]): The chat context.

    Returns:
        str: The SQL query generated by the AI model.
    """
    meta_str = "\n".join(metadata)
    meta_str = f"This is my db structure:\n{meta_str}" if meta_str else ""

    context_str = "\n".join([f"{' - ' + c['role'] + ': ' + c['content']}" for c in context]) if context else ""
    context_str = f"\n\nPrevious Chat context:\n{context_str}" if context_str else ""

    template = f"""{meta_str}

    Please answer only with the SQL query (without any text formatting) that answers the following question:
    {message.content}

    Keep in mind that the database is a {conn_info["type_of_db"]} database and that the schema is {schema} and it should be used in the SQL query.
    {"Add quotes around the table and column names to avoid SQL syntax errors." if conn_info["type_of_db"] == "postgres" else ""}
    Unless explicitly stated, please do not limit the number of rows returned.
    {context_str}
    """
    logger.debug(f"Sending the following template to the AI model:\n{template}")

    response = await ai_controller.get_ai_response(template)
    logger.debug(f"AI's response: {response}")
    return str_manipulation.extract_sql_only(response)


def get_db_controller_and_metadata(
    conn_info: dict,
    schema: str,
) -> tuple[BaseDBController, list[str], SSHTunnelForwarder | None]:
    """
    Get the database controller and metadata.

    Args:
        conn_info (dict): The connection information.
        schema (str): The database schema.

    Returns:
        tuple[BaseDBController, list[str], SSHTunnelForwarder | None]: The database controller, metadata, and SSH tunnel.
    """
    conn_details = deepcopy(conn_info)
    tunnel = None
    if conn_info.get("ssh"):
        logger.debug("Using SSH tunnel for database connection")
        tunnel = SSHTunnelForwarder(
            ssh_address_or_host=(conn_info["ssh"]["ssh_host"], conn_info["ssh"]["ssh_port"]),
            ssh_username=conn_info["ssh"]["ssh_user"],
            ssh_password=conn_info["ssh"]["ssh_password"],
            remote_bind_address=(conn_info["tcp"]["host"], conn_info["tcp"]["port"]),
            local_bind_address=("127.0.0.1", 0),
            logger=logger,
        )
        tunnel.start()
        conn_details["tcp"]["host"] = "127.0.0.1"
        conn_details["tcp"]["port"] = tunnel.local_bind_port

    db_controller: connection_controller.MySQLController | connection_controller.PostgresController = get_db_controller(
        db_type=conn_info["type_of_db"],
        tcp_details=conn_details["tcp"],
    )
    metadata = db_controller.get_db_metadata(schema=schema)
    return db_controller, metadata, tunnel
