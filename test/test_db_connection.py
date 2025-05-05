import psycopg as sql
import pytest
from dotenv import load_dotenv
import os

from custom_logging import setup_logger
logger = setup_logger("test_webtext2sql")

from db_controller import _get_db_tables_for_user, _get_table_metadata

# Load environment variables from a .env file
load_dotenv()

@pytest.fixture
def db_config():
    return {
        "db_url": os.getenv("TARGET_DATABASE_URL"),
        "chainlit_db_url": os.getenv("DATABASE_URL"),
    }

def test_pgsql_connection(db_config):
    try:
        logger.info("Attempting to connect to the database...")
        
        connection = sql.connect(db_config["db_url"])
        assert connection is not None, "Failed to establish a connection to the database."
        
        logger.info("Database connection established successfully.")
    except Exception as e:
        pytest.fail(f"Database connection test failed with error: {e}")
    finally:
        # Ensure the connection is closed after the test
        if 'connection' in locals() and connection:
            connection.close()
            
def test_get_db_tables_for_user(db_config):
    try:
        connection = sql.connect(db_config["db_url"])
        cursor = connection.cursor()
        
        cursor.execute("""SELECT DISTINCT table_name
                          FROM information_schema.role_table_grants 
                          WHERE privilege_type = 'SELECT' 
                          AND grantee = 'test_user'
                          AND table_schema = 'northwind';""")
        expected_tables = cursor.fetchall()
        
        actual_tables = _get_db_tables_for_user(connection)
        assert expected_tables is not None, "Failed to retrieve tables for the user."
        assert actual_tables == expected_tables, "The retrieved tables do not match the expected tables."
        
        logger.info(f"Tables found: {actual_tables}")
    except Exception as e:
        pytest.fail(f"Failed to retrieve tables with error: {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection:
            connection.close()
           
 
def test_get_table_metadata(db_config):
    connection = sql.connect(db_config["db_url"])
    
    expected_categories_table_ddl = """CREATE TABLE northwind.categories (
        "category_id" smallint NOT NULL,
        "category_name" character varying(15) NOT NULL,
        "description" text,
        "picture" bytea,
        PRIMARY KEY ("category_id")
    );
    """

    actual_ddl = _get_table_metadata('categories', connection=connection)
    
    assert actual_ddl is not None, "Failed to retrieve table metadata."
    
    # Normalize the DDL for comparison
    actual_ddl = " ".join(actual_ddl.split())
    expected_categories_table_ddl = " ".join(expected_categories_table_ddl.split())
    
    assert actual_ddl == expected_categories_table_ddl, "The retrieved DDL does not match the expected DDL."
    
    logger.info(f"DDL for categories table: {actual_ddl}")
    connection.close()
