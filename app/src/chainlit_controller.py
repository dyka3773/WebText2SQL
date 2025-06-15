import logging
import os
from typing import TYPE_CHECKING

import chainlit as cl
import chainlit.data as cl_data
from connection_factory import get_db_controller, get_db_controller_type
from sqlmodel import Session, create_engine
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

    return get_db_controller(conn_info["type_of_db"], conn_info["tcp"]).get_available_dbs()


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
                    "type_of_db": conn.type_of_db,
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

    if connection_type == "ssh":
        # Ask for SSH and TCP connection details
        # Note: The SSH connection info will be used to create a tunnel to the database server
        conn_info["ssh"] = await ask_for_the_ssh_connection_info()
        conn_info["tcp"], conn_info["type_of_db"] = await ask_for_the_tcp_connection_info()
    elif connection_type == "tcp":
        conn_info["tcp"], conn_info["type_of_db"] = await ask_for_the_tcp_connection_info()

    conn_info["type"] = connection_type

    # TODO #34 @dyka3773: Change this to support SSH tunnel connections if needed
    can_establish_connection: bool = get_db_controller_type(conn_info["type_of_db"]).try_establish_connection(conn_info["tcp"])

    if not can_establish_connection:
        await cl.Message(content="Failed to establish a connection with the provided information. Please try again.").send()
        return False

    # Save the connection info in the user session
    cl.user_session.set("curr_conn_info", conn_info)

    # Change the current thread name to reflect the current connection
    server_name = conn_info["tcp"].get("host", "unknown_server")
    await change_thread_name(server_name)

    # Save the connection info in the database
    db_engine = create_engine(os.getenv("DATABASE_URL"))

    with Session(db_engine) as session:
        user_connections.insert_user_connection(
            user_connection=UserConnection(
                user_email=cl.user_session.get("user").identifier,
                server_name=server_name,
                ssh_connection_info=conn_info["ssh"] if connection_type == "ssh" else {},
                tcp_connection_info=conn_info["tcp"] if connection_type == "tcp" else {},
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

    host: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database host or IP address (e.g., `db.example.com` or `127.0.0.1`):",
    ).send()

    port: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database port (e.g., `5432` or `3306`):",
    ).send()

    type_of_db: AskActionResponse | None = await cl.AskActionMessage(
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

    user: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database username:",
    ).send()

    password: StepDict | None = await cl.AskUserMessage(
        content="Please enter the database password:",
    ).send()

    tcp_info["host"] = host.get("output")
    tcp_info["port"] = int(port.get("output"))
    tcp_info["user"] = user.get("output")
    tcp_info["password"] = password.get("output")
    type_of_db = type_of_db.get("payload").get("value")

    return tcp_info, type_of_db


async def change_thread_name(thread_name: str) -> None:
    """
    Change the name of the current thread to reflect the current connection.

    Args:
        thread_name (str): The new name for the thread.
    """
    logger.info(f"Changing thread name to: {thread_name}")

    # TODO @dyka3773: This is a temporary solution to change the thread name (it is visible only when refreshing the page).
    await cl_data.get_data_layer().update_thread(
        cl.context.session.thread_id,
        name=thread_name,
    )
    # This is a hacky way to set the thread name in Chainlit.
    # It uses the emitter to emit that a new interaction has started again after the thread name has already been set.
    # BUG: It doesn't seem to work properly, so it is commented out for now.
    # await cl.context.emitter.emit(
    #     "first_interaction",
    #     {
    #         "interaction": thread_name,
    #         "thread_id": cl.context.session.thread_id,
    #     },
    # )


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
