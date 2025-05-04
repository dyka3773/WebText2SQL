from typing import Callable
import logging

logger = logging.getLogger("webtext2sql")


def extract_sql_only(string: str) -> str:
    """
    Extract SQL query from the given string by applying a series of filters.
    
    Parameters:
        string (str): The string to process.
        
    Returns:
        str: The extracted SQL query.
    """
    # In case a new filter is added, it should be added to the list of filters.
    # The order of the filters is important, so be careful when adding new ones.
    list_of_filters: list[Callable] = [
        _remove_sql_tags,
        _remove_empty_lines,
    ]
    
    # Apply each filter function to the response string
    logger.debug(f"Applying filters to the string: {string}")
    logger.debug(f"Filters to be applied: {list_of_filters}")
    
    for filter_func in list_of_filters:
        logger.debug(f"Applying filter: {filter_func.__name__}")
        string = filter_func(string)
    
    return string

def _remove_sql_tags(string: str) -> str:
    """
    Remove SQL tags from the given string.
    
    Parameters:
        string (str): The string to process.
        
    Returns:
        str: The string without SQL tags.
    """
    logger.debug(f"Removing SQL tags ('```sql' and '```') from the string: {string}")
    string = string.replace("```sql", "").replace("```", "").strip()
    
    return string

def _remove_empty_lines(string: str) -> str:
    """
    Remove empty lines from the given string.
    
    Parameters:
        string (str): The string to process.
        
    Returns:
        str: The string without empty lines.
    """
    logger.debug(f"Filtering out empty lines from the string: {string}")
    lines = [line.strip() for line in string.split("\n")]
    lines = [line for line in lines if line]  # Remove empty lines
    
    return "\n".join(lines)
