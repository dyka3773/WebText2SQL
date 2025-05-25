import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with a specific name and configuration.
    Note: This could also be used to modify an existing logger's configuration.

    Args:
        name (str): The name of the logger.
        level (int): The logging level. Default is logging.INFO.

    Returns:
        logging.Logger: The configured logger instance.
    """
    formatter = logging.Formatter(
        "%(asctime)s - %(threadName)s:%(thread)d - %(module)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not Path("logfiles").exists():
        Path("logfiles").mkdir(parents=True)

    handler = RotatingFileHandler(
        f"./logfiles/{name}.log",
        maxBytes=1 * 1024 * 1024,  # 1 MB
        backupCount=5,  # Keep 5 backup files
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)

    if logger.hasHandlers():
        handlers: list[logging.Handler] = logger.handlers
        # Remove all existing handlers
        (logger.removeHandler(handler) for handler in handlers)  # this tuple will be garbage collected immediately

    logger.setLevel(level)
    logger.addHandler(handler)

    logger.propagate = False  # Prevent propagation to the root logger
    logger.info(f"Logger {name} has been set up")

    return logger
