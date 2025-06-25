import logging
from typing import TYPE_CHECKING, override

import psycopg as sql
from cachetools.func import ttl_cache

from caching_configs import CACHE_MAX_SIZE, CACHE_TTL
from db_controllers.base_db_controller import BaseDBController

if TYPE_CHECKING:
    from psycopg.rows import Row

logger = logging.getLogger("webtext2sql")


class PostgresController(BaseDBController):
    """
    Controller for managing PostgreSQL database connections and operations.
    Inherits from BaseDBController to provide common functionality.
    """

    def __init__(self, tcp_details: dict | None = None) -> None:
        super().__init__(db_type="postgres", tcp_details=tcp_details if tcp_details else {})
        if tcp_details is not None:
            self._connection: sql.Connection = sql.connect(**tcp_details)

    @override
    @ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
    def get_available_dbs(self) -> list[str]:
        """
        Retrieve the names of all database schemas available to the user.

        Returns:
            list[str]: A list of database schema names available to the user.
        """
        try:
            logger.debug(f"Fetching database schemas for user: {self._user}")

            with self.connection.cursor() as cursor:
                cursor.execute("""SELECT DISTINCT table_schema
                                        FROM information_schema.role_table_grants
                                        WHERE privilege_type = 'SELECT';""")
                dbs = cursor.fetchall()

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
            cursor.execute(f"""SELECT DISTINCT table_name
                        FROM information_schema.role_table_grants
                        WHERE privilege_type = 'SELECT'
                        AND grantee = '{self._user}'
                        AND table_schema = '{schema}';
                   """)
            tables: list[Row] = cursor.fetchall()

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
        ddl = f"CREATE TABLE {schema}.{table_name} (\n"

        try:
            with self.connection.cursor() as cur:
                # Get column definitions
                cur.execute(f"""
                    SELECT
                        a.attname AS column_name,
                        pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                        a.attnotnull AS not_null,
                        pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
                        d.description AS column_comment
                    FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
                    LEFT JOIN pg_description d ON d.objoid = a.attrelid AND d.objsubid = a.attnum
                    WHERE c.relname = '{table_name}'
                    AND n.nspname = '{schema}'
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                    ORDER BY a.attnum
                """)

                columns = cur.fetchall()
                col_lines = []  # list to hold column definitions

                for col in columns:
                    col_def = f'    "{col[0]}" {col[1]}'
                    if col[3]:
                        col_def += f" DEFAULT {col[3]}"
                    if col[2]:
                        col_def += " NOT NULL"
                    col_lines.append(col_def)

                # Get primary key
                cur.execute(f"""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.constraint_schema = kcu.constraint_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_name = '{table_name}'
                    AND tc.table_schema = '{schema}'
                    ORDER BY kcu.ordinal_position
                """)

                pk_cols = [f'"{row[0]}"' for row in cur.fetchall()]
                if pk_cols:
                    col_lines.append(f"    PRIMARY KEY ({', '.join(pk_cols)})")

                # Get foreign keys
                cur.execute(f"""
                    SELECT
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_schema AS foreign_table_schema,
                        ccu.table_name AS foreign_table,
                        ccu.column_name AS foreign_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.constraint_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_name = '{table_name}'
                    AND tc.table_schema = '{schema}'
                """)

                fk_constraints = cur.fetchall()
                for fk in fk_constraints:
                    fk_def = f'    CONSTRAINT "{fk[0]}" FOREIGN KEY ("{fk[1]}") REFERENCES {fk[2]}.{fk[3]}("{fk[4]}")'
                    col_lines.append(fk_def)

                ddl += ",\n".join(col_lines) + "\n);\n"

                # Add table comment
                cur.execute(f"""
                    SELECT d.description
                    FROM pg_description d
                    JOIN pg_class c ON d.objoid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE c.relname = '{table_name}'
                    AND n.nspname = '{schema}'
                    AND d.objsubid = 0
                """)
                table_comment = cur.fetchone()
                if table_comment and table_comment[0]:
                    ddl += f"\nCOMMENT ON TABLE {schema}.{table_name} IS '{table_comment[0]}';"

                # Add column comments
                for col in columns:
                    if col[4]:
                        ddl += f"\nCOMMENT ON COLUMN {schema}.{table_name}.\"{col[0]}\" IS '{col[4]}';"

        except (sql.Error, Exception):
            logger.exception(f"An error occurred while fetching metadata for table {table_name}")
            return None

        return ddl

    @override
    @staticmethod
    def try_establish_connection(tcp_details: dict) -> bool:
        """
        Attempt to establish a connection to the database using the provided connection info.

        Args:
            tcp_details (dict): A dictionary containing connection parameters such as host, port, user, password, and database.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            logger.debug(f"Attempting to establish connection with info: {tcp_details}")

            with sql.connect(**tcp_details):
                logger.info("Connection established successfully.")
                return True
        except sql.Error:
            logger.exception("Failed to establish a connection.")
            return False
