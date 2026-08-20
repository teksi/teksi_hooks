import re

from abc import ABC
from dataclasses import dataclass, field
from typing import ClassVar
from re import Pattern

from ..exceptions import ValidationError


@dataclass(slots=True, frozen=True)
class Oid(ABC):
    """
    Validated INTERLIS OID value.

    Concrete subclasses define the validation pattern used for the
    underlying identifier format.
    """

    _pattern: ClassVar[Pattern[str]]

    value: str = field(
        metadata={
            "doc": (
                "Raw OID value. Must match the validation pattern "
                "defined by the concrete OID type."
            ),
        },
    )

    def __post_init__(
        self,
    ) -> None:
        if not self._pattern.fullmatch(
            self.value,
        ):
            raise ValidationError.from_message(
                f"'{self.value}' is not a valid {self.__class__.__name__}."
            )

    def __str__(
        self,
    ) -> str:
        return self.value


@dataclass(slots=True, frozen=True)
class Standardoid(Oid):
    """
    Validated INTERLIS standard OID value.

    A Standardoid is represented as a 16-character word string. It is used
    as a stable identifier for TEKSI / INTERLIS objects, organizations and
    data owners.
    """

    _pattern: ClassVar[Pattern[str]] = re.compile(
        r"^[A-Za-z0-9]{16}$",
    )
