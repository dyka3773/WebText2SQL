import sqlite3 as sql
from dotenv import load_dotenv
import os

load_dotenv()

connection = sql.connect(os.getenv('DATABASE_URL'))

def fetch_data(query, connection) -> list:
    """
    Fetch data from the database using the provided SQL query.

    Parameters:
        query (str): SQL query to execute.
        connection (sqlite3.Connection): SQLite connection object.

    Raises:
        ValueError: If the query does not end with a semicolon.

    Returns:
        list: List of tuples containing the fetched data.
    """
    if not query.strip().endswith(';'):
        raise ValueError("SQL query must end with a semicolon.")

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        return results
    except sql.Error as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()