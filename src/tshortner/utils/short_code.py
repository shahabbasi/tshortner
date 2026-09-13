import secrets
from collections.abc import Sequence

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def random_short_code(prefixes: Sequence[str], length: int) -> str:
    """Random base62 code starting with one of this instance's prefixes, so instances never collide."""
    return secrets.choice(prefixes) + "".join(secrets.choice(ALPHABET) for _ in range(length - 1))
