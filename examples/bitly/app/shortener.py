import re


BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
GENERATED_PREFIX = "g"
CUSTOM_ALIAS_RE = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")


def base62_encode(number: int) -> str:
    if number < 0:
        raise ValueError("number must be non-negative")
    if number == 0:
        return BASE62_ALPHABET[0]

    chars: list[str] = []
    base = len(BASE62_ALPHABET)
    while number:
        number, remainder = divmod(number, base)
        chars.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def base62_decode(value: str) -> int:
    number = 0
    base = len(BASE62_ALPHABET)
    for char in value:
        number = number * base + BASE62_ALPHABET.index(char)
    return number


def generated_code(counter_value: int, xor_secret: int) -> str:
    obfuscated = counter_value ^ xor_secret
    return f"{GENERATED_PREFIX}{base62_encode(obfuscated)}"


def generated_counter_value(short_code: str, xor_secret: int) -> int:
    if not short_code.startswith(GENERATED_PREFIX):
        raise ValueError("not a generated short code")
    return base62_decode(short_code[len(GENERATED_PREFIX) :]) ^ xor_secret


def validate_custom_alias(alias: str) -> None:
    if alias.startswith(GENERATED_PREFIX):
        raise ValueError(f"custom aliases cannot start with '{GENERATED_PREFIX}'")
    if not CUSTOM_ALIAS_RE.fullmatch(alias):
        raise ValueError("custom aliases must be 3-64 chars using letters, digits, _ or -")
