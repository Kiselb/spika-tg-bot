import secrets
import string
import re
from config import EMAIL_PATTERN

def generate_password(length=10):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def is_valid_email(email):
    return bool(EMAIL_PATTERN.fullmatch(email))
