_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_BASE = len(_ALPHABET)


def encode(number: int) -> str:
    if number < 0:
        raise ValueError("cannot base62-encode a negative number")
    if number == 0:
        return _ALPHABET[0]

    digits = []
    while number > 0:
        number, remainder = divmod(number, _BASE)
        digits.append(_ALPHABET[remainder])
    return "".join(reversed(digits))


def decode(code: str) -> int:
    number = 0
    for char in code:
        number = number * _BASE + _ALPHABET.index(char)
    return number
