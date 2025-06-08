import logging

import psycopg as sql
import str_manipulation
from cachetools.func import ttl_cache
from caching_configs import CACHE_MAX_SIZE, CACHE_TTL

logger = logging.getLogger("webtext2sql")


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def get_available_dbs(connection: sql.Connection, user: str) -> list[str]:
    """
    Retrieve the names of all databases available to the user.

    Args:
        connection (psycopg.Connection): psycopg connection object.
        user (str): The username for which to retrieve the databases.

    Returns:
        list: list of database names.
    """
    try:
        cursor = connection.cursor()

        logger.debug(f"Fetching database schemas for user: {user}")

        cursor.execute(f"""SELECT DISTINCT table_schema
                                FROM information_schema.role_table_grants
                                WHERE privilege_type = 'SELECT'
                                AND grantee = '{user}';""")
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
def fetch_data(query: str, connection: sql.Connection) -> tuple[tuple[tuple], tuple[str]]:
    """
    Fetch data from the database using the provided SQL query.

    Args:
        query (str): SQL query to execute.
        connection (psycopg.Connection): psycopg connection object.

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
def _get_db_tables_for_user(connection: sql.Connection, schema: str | None = None, user: str | None = None) -> list[tuple]:
    """
    Retrieve the names of all tables in the database.

    Args:
        connection (psycopg.Connection): psycopg connection object.
        schema (str): Schema name.
        user (str): The username for which to retrieve the tables.

    Returns:
        list: list of table names.
    """
    cursor = connection.cursor()
    cursor.execute(f"""SELECT DISTINCT table_name
                        FROM information_schema.role_table_grants
                        WHERE privilege_type = 'SELECT'
                        AND grantee = '{user}'
                        AND table_schema = '{schema}';
                   """)
    tables = cursor.fetchall()

    logger.debug(f"Tables found: {tables}")

    cursor.close()
    return tables


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def _get_table_metadata(table_name: str, connection: sql.Connection, schema: str | None = None) -> str:
    """
    Get DDL of the table.

    Args:
        table_name (str): Name of the table.
        connection (psycopg.Connection): psycopg connection object.
        schema (str): Schema name.

    Returns:
        str: DDL of the table.
    """
    ddl = f"CREATE TABLE {schema}.{table_name} (\n"

    with connection.cursor() as cur:
        try:
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

        except Exception:
            logger.exception(f"An error occurred while fetching metadata for table {table_name}")
            return None

    return ddl


@ttl_cache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
def get_db_metadata(connection: sql.Connection, schema: str | None = None, user: str | None = None) -> list[str]:
    """
    Retrieve the metadata of the database tables available to the user in a given schema.

    Args:
        connection (psycopg.Connection): psycopg connection object.
        schema (str): Schema name.
        user (str): The username for which to retrieve the metadata.

    Returns:
        list: list of table DDL strings.
    """
    logger.debug("Fetching all database tables available to the user")
    tables: list[tuple] = _get_db_tables_for_user(connection, schema=schema, user=user)

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
    tcp_details = connection_info["tcp"]
    try:
        # TODO #34 @dyka3773: Change this to support SSH tunnel connections if needed
        with sql.connect(**tcp_details) as _:
            logger.debug("Connection established successfully.")
            return True
    except sql.Error:
        logger.exception("Failed to establish a connection.")
        return False
