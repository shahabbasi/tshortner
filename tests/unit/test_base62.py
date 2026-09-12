import pytest

from tshortner.utils import base62


@pytest.mark.parametrize("number", [0, 1, 61, 62, 63, 12345, 999999999])
def test_encode_decode_round_trip(number: int) -> None:
    assert base62.decode(base62.encode(number)) == number


def test_encode_is_deterministic() -> None:
    assert base62.encode(12345) == base62.encode(12345)


def test_encode_negative_raises() -> None:
    with pytest.raises(ValueError):
        base62.encode(-1)


def test_encode_zero() -> None:
    assert base62.encode(0) == "0"
