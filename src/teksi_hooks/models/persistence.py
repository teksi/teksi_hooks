from __future__ import annotations

from dataclasses import dataclass, field

from .canonical_object import (
    CanonicalObjectIdentity,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ChangePersistenceResult:
    """
    Result of persisting one accepted canonical change.
    """

    change_index: int = field(
        metadata={
            "doc": (
                "Zero-based index of the corresponding change in the "
                "accepted change sequence."
            )
        },
    )

    identity: CanonicalObjectIdentity = field(
        metadata={"doc": ("Canonical identity of the persisted object.")},
    )

    affected_rows: int = field(
        metadata={
            "doc": (
                "Number of physical database rows affected while persisting "
                "the canonical change."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceResult:
    """
    Result of atomically persisting accepted canonical changes.
    """

    change_results: tuple[
        ChangePersistenceResult,
        ...,
    ] = field(
        default_factory=tuple,
        metadata={"doc": ("Results for the canonical changes successfully persisted.")},
    )

    @property
    def affected_rows(
        self,
    ) -> int:
        """
        Return the total number of affected physical rows.
        """

        return sum(result.affected_rows for result in self.change_results)
