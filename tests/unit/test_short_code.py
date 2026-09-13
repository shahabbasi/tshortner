import pytest
from pydantic import ValidationError

from tshortner.core.config import Settings
from tshortner.utils.short_code import ALPHABET, random_short_code


def test_random_short_code_uses_prefixes_length_and_alphabet() -> None:
    codes = [random_short_code(["a", "B"], 7) for _ in range(500)]

    assert {code[0] for code in codes} == {"a", "B"}
    assert all(len(code) == 7 and set(code) <= set(ALPHABET) for code in codes)
    assert len(set(codes)) == len(codes)


def test_prefixes_default_to_every_character(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHORT_CODE_PREFIXES", raising=False)

    assert Settings(_env_file=None).short_code_prefixes == list(ALPHABET)


def test_prefixes_parse_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHORT_CODE_PREFIXES", "a, b,c,A,B,C")

    assert Settings(_env_file=None).short_code_prefixes == ["a", "b", "c", "A", "B", "C"]


@pytest.mark.parametrize("value", ["", "ab", "a,a", "a,-"])
def test_invalid_prefixes_are_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("SHORT_CODE_PREFIXES", value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
