from typing import Callable, List, Tuple
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

def form_answer(results: List[Tuple], column_names: List[str], query: str) -> str:
    """
    Format the results before sending them back to the user.

    Args:
        results (List[Tuple]): List of tuples containing the fetched data.
        column_names (List[str]): List of column names.
        query (str): The SQL query that was executed.

    Returns:
        str: Formatted string representation of the results and the SQL query.
    """
    if not results:
        logger.warning("No results found for the SQL query.")
        results = "No results found."
    else:
        results = create_markdown_results_table(results, column_names)
        logger.debug(f"Formatted results: {results}")
        
    answer = f"Here is the SQL query the AI model generated:\n```sql\n{query}\n```\n\nAnd here are the results:\n{results}"
    
    logger.debug(f"Formatted answer: {answer}")
    
    return answer

def optimize_ddl_for_ai(ddl: str) -> str:
    """
    Optimize the DDL for AI model processing by removing unnecessary whitespace.

    Args:
        ddl (str): The DDL string to optimize.

    Returns:
        str: Optimized DDL string.
    """
    trimmed_ddl = " ".join(ddl.split())
    return trimmed_ddl

def create_markdown_results_table(results: List[Tuple], column_names: List[str]) -> str:
    """
    Create a markdown table from the results and column names.

    Args:
        results (List[Tuple]): List of tuples containing the fetched data.
        column_names (List[str]): List of column names.

    Returns:
        str: Markdown formatted table.
    """
    # Create header
    header = "| " + " | ".join(column_names) + " |"
    separator = "| " + " | ".join(["---"] * len(column_names)) + " |"
    
    # Create rows
    rows = []
    for row in results:
        rows.append("| " + " | ".join([str(item) for item in row]) + " |")
    
    # Combine header, separator, and rows
    markdown_table = "\n".join([header, separator] + rows)
    
    return markdown_table