from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from .canonical_object import (
    CanonicalObjectIdentity,
)
from .validation import (
    Change,
)


class DiffJobMode(StrEnum):
    """
    Defines how an existing diff job is handled.
    """

    CREATE = "create"
    REPLACE = "replace"
    REFRESH = "refresh"


@dataclass(
    frozen=True,
    slots=True,
)
class AttributePersistenceDecision:
    """
    Persistence decision for one changed canonical attribute.

    This model records the authorization result only. It does not prescribe
    how an unpermitted attribute is represented or handled by a persistence
    adapter.

    A model-specific persistence implementation may, for example:

    - remove the corresponding source value;
    - replace it with NULL;
    - restore a mandatory value from live data;
    - construct a canonical update directly;
    - apply another model-specific strategy.
    """

    class_id: str = field(
        metadata={
            "doc": (
                "Canonical identifier of the changed attribute's class "
                "to which this persistence decision applies."
            )
        },
    )

    attribute_id: str = field(
        metadata={
            "doc": (
                "Canonical identifier of the changed attribute to which "
                "this persistence decision applies."
            )
        },
    )

    permitted: bool = field(
        metadata={
            "doc": (
                "Whether the provider is permitted to persist the changed "
                "canonical attribute."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional model-specific metadata required to implement the "
                "persistence decision. This may include source-model "
                "provenance, source relation and attribute identifiers, "
                "mandatory-value information, mapping references or "
                "diagnostic context. Generic persistence logic must not "
                "assign semantics to these values."
            )
        },
    )

    def key(
        self,
    ) -> tuple[
        str,
        str,
    ]:
        """
        Return the decision key within its parent change decision.
        """

        return (
            self.class_id,
            self.attribute_id,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ChangePersistenceDecision:
    """
    Persistence decision for one object-level canonical change.

    A Change describes one inserted, updated or deleted canonical object.
    Attribute-level changes are derived from its old and new values through
    ``Change.changed_attributes``.

    The object-level ``permitted`` decision is primarily applicable to
    insertion and deletion. Update decisions may additionally contain one
    AttributePersistenceDecision for each changed canonical attribute.

    This model deliberately does not define how insertions, updates or
    deletions are physically persisted. Those semantics belong to the
    model-specific persistence implementation.
    """

    change: Change = field(
        metadata={
            "doc": (
                "Object-level canonical change being considered for "
                "persistence. The change contains the canonical identity, "
                "operation, old values and new values."
            )
        },
    )

    permitted: bool = field(
        metadata={
            "doc": (
                "Object-level persistence decision. For inserted and deleted "
                "objects, this indicates whether the object operation is "
                "permitted. For updated objects, attribute-level decisions "
                "provide the detailed authorization result for changed "
                "attributes."
            )
        },
    )

    attribute_decisions: tuple[
        AttributePersistenceDecision,
        ...,
    ] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Persistence decisions for changed canonical attributes. "
                "These decisions are primarily used for updates and should "
                "refer only to attributes in Change.changed_attributes."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional model-specific metadata associated with the "
                "object-level persistence decision. This may contain source "
                "object identities, inheritance information, mapping "
                "provenance, cascade information or other data required by "
                "a concrete persistence adapter."
            )
        },
    )

    @property
    def permitted_attributes(
        self,
    ) -> frozenset:
        """
        Return changed attributes permitted for persistence.
        """

        return frozenset(
            decision.attribute_id
            for decision in self.attribute_decisions
            if decision.permitted
        )

    @property
    def unpermitted_attributes(
        self,
    ) -> frozenset:
        """
        Return changed attributes not permitted for persistence.
        """

        return frozenset(
            decision.attribute_id
            for decision in self.attribute_decisions
            if not decision.permitted
        )

    @property
    def decided_attributes(
        self,
    ) -> frozenset:
        """
        Return all changed attributes having a persistence decision.
        """

        return frozenset(decision.attribute_id for decision in self.attribute_decisions)


@dataclass(
    frozen=True,
    slots=True,
)
class ChangePersistenceDocument:
    """
    Ordered persistence decisions for one reviewed change snapshot.

    The document records authorization decisions independently of any
    concrete database, INTERLIS implementation or source-model mapping.
    """

    job_id: str = field(
        metadata={
            "doc": (
                "Stable identifier of the review job to which this "
                "persistence document belongs."
            )
        },
    )

    snapshot_id: UUID = field(
        metadata={
            "doc": (
                "Stable identifier of the immutable reviewed change "
                "snapshot to which these persistence decisions apply."
            )
        },
    )

    version: int = field(
        default=1,
        metadata={
            "doc": (
                "Version of the persistence-decision document contract. "
                "Consumers must reject unsupported versions rather than "
                "silently interpreting them using different semantics."
            )
        },
    )

    decisions: tuple[
        ChangePersistenceDecision,
        ...,
    ] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Ordered persistence decisions corresponding to the "
                "classified canonical changes."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional document-level metadata. Generic persistence "
                "consumers must not rely on model-specific entries."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ChangePersistenceResult:
    """
    Result of persisting one accepted canonical change.

    The affected-row count describes physical persistence work and therefore
    may be greater than one for a single canonical object. For example, one
    canonical change may affect a base table, an extension table and related
    mapping tables.
    """

    change_index: int = field(
        metadata={
            "doc": (
                "Zero-based index of the corresponding decision in "
                "ChangePersistenceDocument.decisions."
            )
        },
    )

    identity: CanonicalObjectIdentity = field(
        metadata={
            "doc": (
                "Canonical identity of the object whose persistence decision "
                "was applied."
            )
        },
    )

    affected_rows: int = field(
        metadata={
            "doc": (
                "Number of physical database rows affected while persisting "
                "the canonical change. The value may be zero when a "
                "model-specific decision intentionally results in no live "
                "mutation."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional model-specific result metadata. This may contain "
                "affected physical relations, generated identifiers, ignored "
                "operations, cascade results or diagnostic information."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceResult:
    """
    Result of atomically persisting a reviewed change set.

    A successful result indicates that the model-specific persistence adapter
    completed its transaction. The concrete adapter remains responsible for
    defining and enforcing the physical persistence semantics.
    """

    snapshot_id: UUID = field(
        metadata={
            "doc": (
                "Stable identifier of the immutable reviewed change "
                "snapshot to which these persistence decisions apply."
            )
        },
    )

    change_results: tuple[
        ChangePersistenceResult,
        ...,
    ] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Results for persistence decisions successfully processed by "
                "the model-specific persistence adapter."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional transaction-level result metadata. This may "
                "include the persistence strategy, application schema, "
                "transaction identifier, duration or cleanup information."
            )
        },
    )

    @property
    def affected_rows(
        self,
    ) -> int:
        """
        Return the total number of affected physical rows.
        """

        return sum(result.affected_rows for result in self.change_results)


@dataclass(
    frozen=True,
    slots=True,
)
class DeletionTarget:
    """
    One canonical object proposed for deletion.

    The target records the object state observed while the deletion plan was
    created. A persistence adapter must revalidate this state immediately
    before executing the deletion.
    """

    change_index: int = field(
        metadata={
            "doc": (
                "Zero-based index of the ChangePersistenceDecision from "
                "which this deletion target was derived."
            )
        },
    )

    identity: CanonicalObjectIdentity = field(
        metadata={"doc": ("Canonical identity of the object proposed for deletion.")},
    )

    last_modification: datetime | None = field(
        default=None,
        metadata={
            "doc": (
                "Last-modification value observed when the deletion plan was "
                "created. This value is used for stale-state detection before "
                "the deletion is executed."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional model-specific deletion metadata. This may include "
                "physical relation identifiers, mapped source objects, "
                "dependent-object information or cascade diagnostics."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DeletionPlan:
    """
    Immutable plan of permitted canonical deletions awaiting confirmation.

    The plan is linked to the diff snapshot and persistence-decision document
    from which it was produced. Confirming a plan does not bypass current-state
    validation. Every target must be revalidated before deletion.
    """

    plan_id: str = field(
        metadata={"doc": ("Stable identifier of this deletion plan.")},
    )

    job_id: str = field(
        metadata={"doc": ("Logical review-job identifier owning the deletion plan.")},
    )

    snapshot_id: str = field(
        metadata={
            "doc": (
                "Identifier of the immutable diff snapshot from which the "
                "deletion decisions were derived."
            )
        },
    )

    created_at: datetime = field(
        metadata={"doc": ("Timestamp when the deletion plan was created.")},
    )

    targets: tuple[
        DeletionTarget,
        ...,
    ] = field(
        default_factory=tuple,
        metadata={"doc": ("Ordered canonical objects proposed for deletion.")},
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional plan-level metadata, such as the persistence "
                "strategy or results of a transactional dry run."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DeletionConfirmation:
    """
    Explicit reviewer confirmation of one immutable deletion plan.
    """

    plan_id: str = field(
        metadata={"doc": ("Identifier of the confirmed deletion plan.")},
    )

    confirmed_at: datetime = field(
        metadata={"doc": ("Timestamp when the reviewer confirmed the plan.")},
    )

    reviewer_id: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional identifier of the reviewer who confirmed the deletion plan."
            )
        },
    )

    comment: str | None = field(
        default=None,
        metadata={
            "doc": ("Optional reviewer comment associated with the confirmation.")
        },
    )
