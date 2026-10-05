import re
from re import Pattern
from typing import ClassVar

import pytest

from teksi_hooks.exceptions import TeksiHookError
from teksi_hooks.models.oid import Oid, Standardoid


def test_standardoid_accepts_valid_value() -> None:
    oid = Standardoid(
        "ch000000geping01",
    )

    assert str(oid) == "ch000000geping01"
    assert oid.value == "ch000000geping01"


def test_standardoid_is_oid() -> None:
    oid = Standardoid(
        "ch000000geping01",
    )

    assert isinstance(
        oid,
        Oid,
    )


class DummyOid(Oid):
    _pattern: ClassVar[Pattern[str]] = re.compile(
        r"^DUMMY$",
    )


def test_oid_base_class_validates_pattern() -> None:
    oid = DummyOid(
        "DUMMY",
    )

    assert oid.value == "DUMMY"


def test_oid_base_class_rejects_invalid_pattern() -> None:
    with pytest.raises(TeksiHookError):
        DummyOid(
            "INVALID",
        )


@pytest.mark.parametrize(
    "value",
    [
        "",
        "too_short",
        "ch000000geping001",  # too long
        "ch000000-geping1",  # dash
        "ch000000gäping01",  # non-ASCII
    ],
)
def test_standardoid_rejects_invalid_value(
    value: str,
) -> None:
    with pytest.raises(TeksiHookError):
        Standardoid(value)
