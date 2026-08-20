from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from .effects import Effect
from .canonical_object import CanonicalObjectIdentity


class SnapshotState(StrEnum):
    CURRENT = "current"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(slots=True, frozen=True)
class SnapshotMetadata:
    """
    Metadata describing the creation context of a diff snapshot.
    """

    created_at: datetime = field(
        metadata={"doc": ("Timestamp when the snapshot was generated.")},
    )

    source_model: str = field(
        metadata={"doc": ("Source model from which the snapshot was generated.")},
    )

    source_class_id: str = field(
        metadata={"doc": ("Source class that initiated snapshot creation.")},
    )

    source_object_id: str = field(
        metadata={
            "doc": ("Source object identifier that initiated snapshot creation.")
        },
    )


@dataclass(slots=True, frozen=True)
class SnapshotObject:
    """
    Canonical object referenced by a diff snapshot.
    """

    identity: CanonicalObjectIdentity = field(
        metadata={"doc": ("Canonical identity of the referenced object.")},
    )

    last_modification: datetime = field(
        metadata={
            "doc": (
                "Object last_modification value recorded when the "
                "snapshot was generated."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class DiffSnapshot:
    """
    Immutable snapshot of semantic changes.

    A snapshot may be reviewed hours or days after generation.
    Stored object metadata allows detection of stale snapshots when
    underlying database objects have changed.
    """

    metadata: SnapshotMetadata = field(
        metadata={"doc": ("Snapshot creation metadata.")},
    )

    objects: tuple[SnapshotObject, ...] = field(
        default_factory=tuple,
        metadata={"doc": ("Canonical objects referenced by the snapshot.")},
    )

    effects: tuple[Effect, ...] = field(
        default_factory=tuple,
        metadata={"doc": ("Canonical effects captured in the snapshot.")},
    )


@dataclass(slots=True, frozen=True)
class SnapshotValidationFinding:
    identity: CanonicalObjectIdentity
    state: SnapshotState
