import logging

from sshtunnel import SSHTunnelForwarder

from connection_factory import get_db_controller

logger: logging.Logger = logging.getLogger("webtext2sql")


def try_establish_connection(conn_info: dict) -> bool:
    """
    Attempt to establish a connection using the provided connection information.

    Args:
        conn_info (dict): A dictionary containing connection parameters.

    Returns:
        bool: True if the connection is established successfully, False otherwise.
    """
    logger.debug(f"Attempting to establish connection with info: {conn_info}")
    return wrap_db_func_with_ssh_if_needed(
        get_db_controller(conn_info["type_of_db"]).try_establish_connection,
        conn_info,
        conn_info["tcp"],
    )()


def wrap_db_func_with_ssh_if_needed(db_func: callable, conn_info: dict, *args: tuple, **kwargs: dict) -> callable:
    """
    Compose a database function with SSH tunneling if needed.

    Args:
        db_func (callable): The database function to be executed.
        conn_info (dict): A dictionary containing the connection information.
        *args: Positional arguments for the database function.
        **kwargs: Keyword arguments for the database function.

    Returns:
        callable: A function that executes the database function with SSH tunneling if needed.
    """
    ssh_info = conn_info.get("ssh")
    tcp_info = conn_info.get("tcp")
    if ssh_info is not None:
        # If SSH info is provided, we assume the connection is established via SSH tunnel
        with SSHTunnelForwarder(
            ssh_address_or_host=ssh_info["ssh_host"],
            ssh_username=ssh_info["ssh_user"],
            ssh_password=ssh_info["ssh_password"],
            remote_bind_address=(tcp_info["host"], tcp_info["port"]),
        ):
            return lambda: db_func(*args, **kwargs)
    # If no SSH info is provided, we connect directly to the database
    return lambda: db_func(*args, **kwargs)
    return lambda: db_func(*args, **kwargs)
