import psycopg as sql
import logging

logger = logging.getLogger("webtext2sql")


def fetch_data(query, connection) -> list:
    """
    Fetch data from the database using the provided SQL query.

    Parameters:
        query (str): SQL query to execute.
        connection (sqlite3.Connection): SQLite connection object.

    Returns:
        list: List of tuples containing the fetched data.
    """
    try:
        cursor = connection.cursor()
        
        logger.debug(f"Executing query: {query}")
        
        cursor.execute(query)
        results = cursor.fetchall()

        return results
    except sql.Error as e:
        logger.error(f"An error occurred: {e}")
        # TODO: In case of an sql error, we should return it to the user instead of printing it.
    finally:
        cursor.close()


def _get_db_tables_for_user(connection, schema='northwind', user='test_user') -> list[str]:
    """
    Retrieve the names of all tables in the database.

    Parameters:
        connection (psycopg2.Connection): psycopg2 connection object.
    Returns:
        list: List of table names.
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

def _get_table_metadata(table_name, connection, schema='northwind') -> str:
    """Get DDL of the table.

    Args:
        table_name (str): Name of the table.
        connection (psycopg2.Connection): psycopg2 connection object.
        schema (str): Schema name. Default is 'northwind'.

    Returns:
        str: DDL of the table.
    """
    ddl = f'CREATE TABLE {schema}.{table_name} (\n'
    
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
            col_lines = [] # List to hold column definitions
            
            for col in columns:
                col_def = f'    "{col[0]}" {col[1]}'
                if col[3]:
                    col_def += f' DEFAULT {col[3]}'
                if col[2]:
                    col_def += ' NOT NULL'
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
                col_lines.append(f'    PRIMARY KEY ({", ".join(pk_cols)})')

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

        except Exception as e:
            logger.info("Error:", e)
            return None

    return ddl


def get_db_metadata(connection, schema='northwind', user='test_user') -> dict:
    """
    Retrieve the metadata of the database.
    
    Parameters:
        connection (psycopg2.Connection): psycopg2 connection object.

    Returns:
        dict: A dictionary where keys are table names and values are lists of column names.
    """
    logger.debug("Fetching all database tables available to the user")
    tables = _get_db_tables_for_user(connection, schema=schema, user=user)

    metadata = {}
    
    logger.debug("Fetching metadata for these tables")
    for table in tables:
        try:
            table_name = table[0]
            
            logger.debug(f"Fetching metadata & DDL for table: {table_name}")
            
            table_ddl = _get_table_metadata(table_name, connection=connection, schema=schema)
            
            if table_ddl is None:
                logger.error(f"Failed to retrieve metadata for table: {table_name}")
                continue
            
            # Optimize the DDL string by removing extra spaces and newlines to use less tokens
            trimmed_ddl = " ".join(table_ddl.split())
            
            metadata[table_name] = trimmed_ddl
            
        except sql.Error as e:
            logger.error(f"An error occurred while fetching metadata for table {table_name}: {e}")
            continue

    return metadata