import logging
from copy import deepcopy
from typing import TYPE_CHECKING

from sshtunnel import SSHTunnelForwarder

from connection_factory import get_db_controller

if TYPE_CHECKING:
    from db_controllers.mysql_controller import MySQLController
    from db_controllers.pg_controller import PostgresController

logger: logging.Logger = logging.getLogger("webtext2sql")


def try_establish_connection(conn_info: dict) -> bool:
    """
    Attempt to establish a connection using the provided connection information.

    Args:
        conn_info (dict): A dictionary containing connection parameters.

    Returns:
        bool: True if the connection is established successfully, False otherwise.
    """
    db_controller_type: MySQLController | PostgresController = get_db_controller(
        db_type=conn_info["type_of_db"],
    )

    if conn_info["type"] == "ssh":
        # If SSH connection is selected, we need to establish the SSH tunnel first
        try:
            with SSHTunnelForwarder(
                ssh_address_or_host=(conn_info["ssh"]["ssh_host"], conn_info["ssh"]["ssh_port"]),
                ssh_username=conn_info["ssh"]["ssh_user"],
                ssh_password=conn_info["ssh"]["ssh_password"],
                remote_bind_address=(conn_info["tcp"]["host"], conn_info["tcp"]["port"]),
                local_bind_address=("127.0.0.1", 0),  # Let OS pick a free local port
                logger=logger,
            ) as tunnel:
                # Update the TCP connection info to use the local bind port
                conn_dict_info = deepcopy(conn_info)

                conn_dict_info["tcp"]["host"] = "127.0.0.1"
                conn_dict_info["tcp"]["port"] = tunnel.local_bind_port

                return db_controller_type.try_establish_connection(
                    tcp_details=conn_dict_info["tcp"],
                )

        except Exception:
            logger.exception("Failed to establish SSH tunnel:")
            return False

    return db_controller_type.try_establish_connection(
        tcp_details=conn_info["tcp"],
    )
