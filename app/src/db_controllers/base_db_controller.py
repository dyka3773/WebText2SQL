import logging
from abc import ABC, abstractmethod

import mysql.connector
import psycopg
import str_manipulation
from cachetools.func import ttl_cache
from caching_configs import CACHE_MAX_SIZE, CACHE_TTL
from mysql.connector.types import RowType
from psycopg.rows import Row

logger = logging.getLogger("webtext2sql")


class BaseDBController(ABC):
    """
    Base class for database controllers.
    Provides common functionality for managing database connections and executing queries.
    """

    _connection: psycopg.Connection | mysql.connector.MySQLConnection

    def __init__(self, db_type: str, tcp_details: dict) -> None:
        self.db_type = db_type
        self.tcp_details = tcp_details
        self._user = tcp_details.get("user")

    @property
    def connection(self) -> psycopg.Connection | mysql.connector.MySQLConnection:
        """
        Property to get the current database connection.
        If the connection is not established, it raises an error.

        Returns:
            psycopg.Connection | mysql.connector.MySQLConnection: The current database connection.

        Raises:
            ValueError: If the database connection is not established.
        """
        if self._connection is None:
            msg = "Database connection is not established."
            raise ValueError(msg)
        return self._connection

    @abstractmethod
    def get_available_dbs(self) -> list[str]:
        """
        Retrieve the names of all databases available to the user.

        Returns:
            list[str]: A list of database names available to the user.
        """
        msg = "This method should be implemented by subclasses."
        raise NotImplementedError(msg)

    @ttl_cache(maxsize=1024, ttl=10)
    def execute_query(self, query: str) -> tuple[tuple[Row | RowType], tuple[str]]:
        """
        Execute a SQL query and return the results.

        Args:
            query (str): The SQL query to execute.

        Returns:
            tuple: A tuple containing the results as a list of tuples and the column names.
            If an error occurs, returns an empty list.
        """
        try:
            logger.debug(f"Executing query: {query}")

            with self.connection.cursor() as cursor:
                cursor.execute(query)
                results: list[tuple] = cursor.fetchall()

                column_names = (desc[0] for desc in cursor.description)  # This will use the aliases if they are set in the query

            return tuple(results), column_names
        except Exception:
            logger.exception("An error occurred")
            # TODO @dyka3773: In case of an sql error, we should return it to the user instead of just logging it.
            return (), ()

    @abstractmethod
    def _get_db_tables_for_user(self, schema: str) -> list[str]:
        """
        Retrieve the names of all tables in the database.

        Args:
            schema (str): Schema name to filter tables.

        Returns:
            list: list of table names in the specified schema.
        """
        msg = "This method should be implemented by subclasses."
        raise NotImplementedError(msg)

    @abstractmethod
    def _get_table_ddl(self, schema: str, table_name: str) -> str:
        """
        Retrieve the DDL (Data Definition Language) statement for a specific table.

        Args:
            schema (str): Schema name where the table is located.
            table_name (str): Name of the table to retrieve the DDL for.

        Returns:
            str: The DDL statement for the specified table.
        """
        msg = "This method should be implemented by subclasses."
        raise NotImplementedError(msg)

    @ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
    def get_db_metadata(self, schema: str | None = None) -> list[str]:
        """
        Retrieve the metadata of the database tables available to the user in a given schema.

        Args:
            schema (str | None): Schema name to filter tables. If None, all schemas are considered.

        Returns:
            list[str]: A list of table DDL strings.
        """
        logger.debug("Fetching all database tables available to the user")
        tables: list[str] = self._get_db_tables_for_user(schema=schema)

        metadata: list[str] = []

        for table_name in tables:
            try:
                logger.debug(f"Fetching metadata & DDL for table: {table_name}")

                table_ddl = self._get_table_ddl(table_name=table_name, schema=schema)

                logger.debug(f"DDL for table {table_name}:\n{table_ddl}")

                if table_ddl is None:
                    logger.error(f"Failed to retrieve metadata for table: {table_name}")
                    continue

                # Optimize the DDL string to use less tokens
                trimmed_ddl = str_manipulation.optimize_ddl_for_ai(table_ddl)

                metadata.append(trimmed_ddl)

            except Exception:
                logger.exception(f"An error occurred while fetching metadata for table {table_name}")
                continue

        return metadata

    @staticmethod
    @abstractmethod
    def try_establish_connection(tcp_details: dict) -> bool:
        """
        Attempt to establish a database connection.
        This method should be implemented by subclasses to handle specific connection logic.

        Args:
            tcp_details (dict): A dictionary containing connection parameters such as host, user, password, etc.

        Returns:
            bool: True if the connection was established successfully, False otherwise.
        """
        msg = "This method should be implemented by subclasses."
        raise NotImplementedError(msg)

    def close_connection(self) -> None:
        """Close the database connection if it is established."""
        if self._connection:
            logger.debug("Closing database connection.")
            self._connection.close()
            self._connection = None
        else:
            logger.debug("No database connection to close.")

    def __del__(self) -> None:
        """Destructor to ensure the database connection is closed when the object is deleted."""
        self.close_connection()
        logger.debug("BaseDBController instance deleted and connection closed.")
