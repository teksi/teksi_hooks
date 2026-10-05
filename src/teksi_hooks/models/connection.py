from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class PostgreSQLConnectionConfig:
    parameters: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "PostgreSQL connection parameters used to create database "
                "connections and configure external database processes."
            )
        },
    )
