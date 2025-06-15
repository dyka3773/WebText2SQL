import logging
from typing import TYPE_CHECKING, override

import mysql.connector as sql
from cachetools.func import ttl_cache
from caching_configs import CACHE_MAX_SIZE, CACHE_TTL
from db_controllers.base_db_controller import BaseDBController

if TYPE_CHECKING:
    from mysql.connector.types import RowType

logger = logging.getLogger("webtext2sql")


class MySQLController(BaseDBController):
    """
    MySQL database controller that extends the BaseDBController.
    Provides methods to interact with MySQL databases, including fetching available databases and executing queries.
    """

    def __init__(self, tcp_details: dict | None = None) -> None:
        super().__init__(db_type="mysql", tcp_details=tcp_details if tcp_details else {})
        if tcp_details is not None:
            self._connection: sql.MySQLConnection = sql.connect(**tcp_details)

    @override
    @ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
    def get_available_dbs(self) -> list[str]:
        """
        Retrieve the names of all databases available to the user.

        Returns:
            list[str]: A list of database names available to the user.
        """
        try:
            logger.debug(f"Fetching database schemas for user: {self._user}")

            with self.connection.cursor() as cursor:
                cursor.execute("""SELECT DISTINCT schema_name
                                    FROM information_schema.schemata
                                    WHERE schema_name NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                                    AND schema_name NOT LIKE 'mysql_%';""")
                dbs: list[RowType] = cursor.fetchall()

            if not dbs:
                logger.error(f"No database schemas found for user: {self._user}")
                return []

            dbs: list[str] = [db[0] for db in dbs]
            logger.debug(f"Schemas found: {dbs}")

        except sql.Error:
            logger.exception("An error occurred")
            return []
        else:
            return dbs

    @override
    @ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
    def _get_db_tables_for_user(self, schema: str | None = None) -> list[str]:
        """
        Retrieve the names of all tables in the database.

        Args:
            schema (str): Schema name to filter tables.

        Returns:
            list: list of table names in the specified schema.
        """
        with self.connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = '{schema}'
                AND table_name NOT LIKE 'mysql_%'
                AND table_name NOT LIKE 'sys_%'
                AND table_name NOT LIKE 'performance_schema_%';
            """)
            tables: list[RowType] = cursor.fetchall()

        if not tables:
            logger.warning(f"No selectable tables found for user: {self._user} in schema: {schema}")
            return []

        table_names: list[str] = [table[0] for table in tables]  # Extract table names from the Row objects

        logger.debug(f"Tables found: {table_names}")
        return table_names

    @override
    @ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
    def _get_table_ddl(self, table_name: str, schema: str | None = None) -> str:
        """
        Retrieve the DDL (Data Definition Language) statement for a specific table.

        Args:
            schema (str): Schema name where the table is located.
            table_name (str): Name of the table to retrieve the DDL for.

        Returns:
            str: The DDL statement for the specified table.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"""SHOW CREATE TABLE `{schema}`.`{table_name}`;""")
                result: RowType = cursor.fetchone()

        except sql.Error:
            logger.exception(f"An error occurred while fetching DDL for table: {table_name}")
            return None

        if not result:
            logger.error(f"Failed to retrieve DDL for table: {table_name}")
            return None

        return result[1]

    @override
    @staticmethod
    def try_establish_connection(tcp_details: dict) -> bool:
        """
        Attempt to establish a connection to the database using the provided connection info.

        Args:
            tcp_details (dict): A dictionary containing connection parameters such as host, port, user and password.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            with sql.connect(**tcp_details) as _:
                logger.debug("Connection established successfully.")
                return True
        except sql.Error:
            logger.exception("Failed to establish a connection.")
            return False
