import sqlite3 as sql


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
        cursor.execute(query)
        results = cursor.fetchall()

        return results
    except sql.Error as e:
        print(f"An error occurred: {e}")
        # TODO: In case of an sql error, we should return it to the user instead of printing it.
    finally:
        cursor.close()


def get_db_metadata(connection) -> dict:
    """
    Retrieve the metadata of the database.
    
    Parameters:
        connection (sqlite3.Connection): SQLite connection object.

    Returns:
        dict: A dictionary where keys are table names and values are lists of column names.
    """
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    metadata = {}
    for table in tables:
        try:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            metadata[table_name] = [column[1] for column in columns]
        except sql.Error as e:
            print(f"An error occurred while fetching metadata for table {table_name}: {e}")
            continue
        finally:
            cursor.close()

    return metadata