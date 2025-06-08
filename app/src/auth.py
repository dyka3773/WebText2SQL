import logging

import chainlit as cl
import psycopg as sql
from passlib.context import CryptContext

logger = logging.getLogger("webtext2sql")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password_given: str) -> str:
    """
    Hash a given password using bcrypt.

    Args:
        password_given (str): The password to be hashed.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password_given)


def verify_password(password_given: str, actual_encrypted_password: str) -> bool:
    """
    Verify a given password against an actual encrypted password.

    Args:
        password_given (str): The password to verify.
        actual_encrypted_password (str): The actual encrypted password to compare against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(password_given, actual_encrypted_password)
