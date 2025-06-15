from db_controllers.base_db_controller import BaseDBController
from db_controllers.mysql_controller import MySQLController
from db_controllers.pg_controller import PostgresController


def get_db_controller(db_type: str, tcp_details: dict | None = None) -> BaseDBController:
    """
    Get the appropriate database controller based on the specified type.

    Args:
        db_type (str): The type of database ('mysql' or 'postgres').
        tcp_details (dict): Additional keyword arguments for connection parameters.

    Returns:
        BaseDBController: An instance of the appropriate database controller.
    """
    if db_type == "mysql":
        return MySQLController(tcp_details)
    if db_type == "postgres":
        return PostgresController(tcp_details)

    msg = f"Unsupported database type: {db_type}"
    raise ValueError(msg)


def get_db_controller_type(db_type: str) -> type[BaseDBController]:
    """
    Get the class of the appropriate database controller based on the specified type.

    Args:
        db_type (str): The type of database ('mysql' or 'postgres').

    Returns:
        type[BaseDBController]: The class of the appropriate database controller.
    """
    if db_type == "mysql":
        return MySQLController
    if db_type == "postgres":
        return PostgresController

    msg = f"Unsupported database type: {db_type}"
    raise ValueError(msg)
