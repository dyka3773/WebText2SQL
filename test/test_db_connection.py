import psycopg2
import pytest
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

@pytest.fixture
def db_config():
    return {
        "db_url": os.getenv("DATABASE_URL")
    }

def test_pgsql_connection(db_config):
    try:
        print("Attempting to connect to the database...")
        
        connection = psycopg2.connect(db_config["db_url"])
        assert connection is not None, "Failed to establish a connection to the database."
        
        print("Database connection established successfully.")
    except Exception as e:
        pytest.fail(f"Database connection test failed with error: {e}")
    finally:
        # Ensure the connection is closed after the test
        if 'connection' in locals() and connection:
            connection.close()