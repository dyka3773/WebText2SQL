import logging

import mysql.connector as sql
import str_manipulation
from cachetools.func import ttl_cache
from caching_configs import CACHE_MAX_SIZE, CACHE_TTL

logger = logging.getLogger("webtext2sql")


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def get_available_dbs(connection: sql.MySQLConnection, user: str) -> list[str]:
    """
    Retrieve the names of all databases available to the user.

    Args:
        connection (mysql.connector.MySQLConnection): mysql.connector connection object.
        user (str): The username for which to retrieve the databases.

    Returns:
        list: list of database names.
    """
    try:
        cursor = connection.cursor()

        logger.debug(f"Fetching database schemas for user: {user}")

        cursor.execute("""SELECT DISTINCT schema_name
                            FROM information_schema.schemata
                            WHERE schema_name NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
                            AND schema_name NOT LIKE 'mysql_%';""")
        dbs = cursor.fetchall()

        if not dbs:
            logger.error(f"No database schemas found for user: {user}")
            return []

        dbs = [db[0] for db in dbs]
        logger.debug(f"Schemas found: {dbs}")

    except sql.Error:
        logger.exception("An error occurred")
        return []
    else:
        return dbs
    finally:
        cursor.close()


@ttl_cache(maxsize=1024, ttl=10)
def fetch_data(query: str, connection: sql.MySQLConnection) -> tuple[tuple[tuple], tuple[str]]:
    """
    Fetch data from the database using the provided SQL query.

    Args:
        query (str): SQL query to execute.
        connection (mysql.connector.MySQLConnection): mysql.connector connection object.

    Returns:
        tuple: A tuple containing the results and column names.
    """
    try:
        cursor = connection.cursor()

        logger.debug(f"Executing query: {query}")

        cursor.execute(query)
        results: list[tuple] = cursor.fetchall()

        column_names = (desc[0] for desc in cursor.description)  # This will use the aliases if they are set in the query

        return tuple(results), column_names
    except sql.Error:
        logger.exception("An error occurred")
        # TODO @dyka3773: In case of an sql error, we should return it to the user instead of just logging it.
    finally:
        cursor.close()


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def _get_db_tables_for_user(connection: sql.MySQLConnection, schema: str | None = None) -> list[tuple]:
    """
    Retrieve the names of all tables or views in the database.

    Args:
        connection (mysql.connector.MySQLConnection): mysql.connector connection object.
        schema (str): Schema name.

    Returns:
        list: list of table or views names.
    """
    cursor = connection.cursor()

    cursor.execute(f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = '{schema}'
        AND table_name NOT LIKE 'mysql_%'
        AND table_name NOT LIKE 'sys_%'
        AND table_name NOT LIKE 'performance_schema_%';
    """)

    tables = cursor.fetchall()

    logger.debug(f"Tables found: {tables}")

    cursor.close()
    return tables


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def _get_table_metadata(table_name: str, connection: sql.MySQLConnection, schema: str | None = None) -> str:
    """
    Get DDL of the table.

    Args:
        table_name (str): Name of the table.
        connection (mysql.connector.MySQLConnection): mysql.connector connection object.
        schema (str): Schema name.

    Returns:
        str: DDL of the table.
    """
    with connection.cursor() as cur:
        try:
            cur.execute(f"""SHOW CREATE TABLE `{schema}`.`{table_name}`;""")
            result = cur.fetchone()
        except sql.Error:
            logger.exception(f"An error occurred while fetching DDL for table: {table_name}")
            return None

    if not result:
        logger.error(f"Failed to retrieve DDL for table: {table_name}")
        return None

    return result[1]


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def get_db_metadata(connection: sql.MySQLConnection, schema: str | None = None) -> list[str]:
    """
    Retrieve the metadata of the database tables available to the user in a given schema.

    Args:
        connection (mysql.connector.MySQLConnection): mysql.connector connection object.
        schema (str): Schema name.
        user (str): The username for which to retrieve the metadata.

    Returns:
        list: list of table DDL strings.
    """
    logger.debug("Fetching all database tables available to the user")
    tables: list[tuple] = _get_db_tables_for_user(connection, schema=schema)

    metadata = []

    for table in tables:
        try:
            table_name: str = table[0]

            logger.debug(f"Fetching metadata & DDL for table: {table_name}")

            table_ddl = _get_table_metadata(table_name, connection=connection, schema=schema)

            logger.debug(f"DDL for table {table_name}:\n{table_ddl}")

            if table_ddl is None:
                logger.error(f"Failed to retrieve metadata for table: {table_name}")
                continue

            # Optimize the DDL string to use less tokens
            trimmed_ddl = str_manipulation.optimize_ddl_for_ai(table_ddl)

            metadata.append(trimmed_ddl)

        except sql.Error:
            logger.exception(f"An error occurred while fetching metadata for table {table_name}")
            continue

    return metadata


def try_establish_connection(connection_info: dict) -> bool:
    """
    Attempt to establish a connection to the database using the provided connection info.

    Args:
        connection_info (dict): A dictionary containing connection parameters such as host, port, user, password, and database.

    Returns:
        bool: True if the connection was successful, False otherwise.
    """
    tcp_details = connection_info["tcp"].copy()
    tcp_details.pop("type_of_db", None)  # Remove the type_of_db key if it exists, as mysql.connector does not use it
    try:
        # TODO #34 @dyka3773: Change this to support SSH tunnel connections if needed
        with sql.connect(**tcp_details) as _:
            logger.debug("Connection established successfully.")
            return True
    except sql.Error:
        logger.exception("Failed to establish a connection.")
        return False
