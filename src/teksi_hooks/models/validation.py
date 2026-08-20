from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .privilege import PrivilegeId
from .rulesets import StateTransitionRule
from ..exceptions import Severity, Finding
from .canonical_object import CanonicalObjectIdentity


from collections.abc import Mapping


@dataclass(slots=True, frozen=True)
class ValidationContext:
    """
    Runtime context supplied to validation implementations.
    """

    attribute_name: str = field(
        metadata={"doc": ("Canonical attribute identifier being validated.")},
    )

    old_value: Any = field(
        metadata={"doc": ("Existing attribute value before the change.")},
    )

    new_value: Any = field(
        metadata={"doc": ("New attribute value after the change.")},
    )

    context_values: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Runtime context values available to validations, such as "
                "`provider_oid` and `dataowner_oid`."
            )
        },
    )


dataclass(slots=True, frozen=True)


class AttributePermission:
    """
    Describes a privilege requirement for one concrete attribute.

    This is a lightweight runtime representation used when permission checks
    need to be expressed at attribute level.
    """

    table_name: str = field(
        metadata={
            "doc": ("Canonical table or class identifier containing the attribute.")
        },
    )

    attribute_name: str = field(
        metadata={
            "doc": ("Canonical attribute identifier for which the privilege applies.")
        },
    )

    privilege: PrivilegeId = field(
        metadata={
            "doc": ("ID of privilege required to modify or access the attribute.")
        },
    )


@dataclass(slots=True, frozen=True)
class AttributeChange:
    """
    Represents the change of a single attribute within a row-level change.

    The row-level context, such as table name, object id and operation type,
    remains on `Change`. This object only describes the changed attribute
    itself.
    """

    attribute_name: str = field(
        metadata={"doc": ("Name of the changed attribute.")},
    )

    old_value: Any | None = field(
        metadata={
            "doc": (
                "Previous value of the attribute. For inserts this is usually `None`."
            )
        },
    )

    new_value: Any | None = field(
        metadata={
            "doc": (
                "Submitted or resulting value of the attribute. For deletes "
                "this is usually `None`."
            )
        },
    )


@dataclass(slots=True)
class Change:
    """
    Represents a row-level change.

    A change describes one inserted, updated or deleted object. Attribute-level
    changes can be derived from `old_values` and `new_values` via
    `changed_attributes`.
    """

    table_name: str = field(
        metadata={
            "doc": ("Canonical table or class identifier affected by the change.")
        },
    )

    object_id: str = field(
        metadata={"doc": ("Object identifier of the changed row.")},
    )

    operation: ChangeOperation = field(
        metadata={"doc": ("Type of row-level operation: insert, update or delete.")},
    )

    old_values: dict[str, Any] = field(
        metadata={
            "doc": (
                "Attribute values before the change. For inserts this is usually empty."
            )
        },
    )

    new_values: dict[str, Any] = field(
        metadata={
            "doc": (
                "Attribute values after the change. For deletes this is usually empty."
            )
        },
    )

    @property
    def changed_attributes(
        self,
    ) -> frozenset:
        """
        Return attribute-level changes derived from old and new row values.
        Attributes whose old and new values are equal are omitted.
        """

        attribute_names = set(self.old_values) | set(self.new_values)

        return frozenset(
            AttributeChange(
                attribute_name=attribute,
                old_value=self.old_values.get(attribute),
                new_value=self.new_values.get(attribute),
            )
            for attribute in attribute_names
            if self.old_values.get(attribute) != self.new_values.get(attribute)
        )

    @property
    def identity(
        self,
    ) -> CanonicalObjectIdentity:
        return CanonicalObjectIdentity(
            class_id=self.table_name,
            attributes={
                "obj_id": self.object_id,
            },
        )


class ChangeOperation(StrEnum):
    """
    Supported row-level change operations.
    """

    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class ChangeClassification(StrEnum):
    """
    Review classification assigned to a change.
    """

    CREATED_OBJECT = "created_object"
    ALTERED_OBJECT = "altered_object"
    DELETED_OBJECT = "deleted_object"
    UNPERMITTED_CHANGE = "unpermitted_change"


@dataclass(slots=True)
class ChangeClassificationMetadata:
    """
    Metadata explaining how and why a change was classified.
    """

    classification: ChangeClassification = field(
        metadata={"doc": ("Review classification assigned to the change.")},
    )

    permitted: bool = field(
        default=True,
        metadata={"doc": ("Whether the change is permitted by rights evaluation.")},
    )

    severity: Severity | None = field(
        default=None,
        metadata={
            "doc": (
                "Highest severity associated with this classified change, "
                "if findings are attached."
            )
        },
    )

    permission_findings: tuple[ValidationFinding, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": ("Permission or rights findings associated with this change.")
        },
    )

    validation_findings: tuple[ValidationFinding, ...] = field(
        default_factory=tuple,
        metadata={"doc": ("Validation findings associated with this change.")},
    )

    classified_at: datetime = field(
        default_factory=datetime.utcnow,
        metadata={"doc": ("UTC timestamp at which the change was classified.")},
    )

    @property
    def findings(
        self,
    ) -> tuple[ValidationFinding, ...]:
        """
        Combined findings for compatibility and simple consumers.
        """

        return (
            *self.permission_findings,
            *self.validation_findings,
        )


@dataclass(slots=True)
class ClassifiedChange:
    """
    A change together with its review classification metadata.
    """

    change: Change = field(
        metadata={"doc": ("The row-level canonical change.")},
    )

    metadata: ChangeClassificationMetadata = field(
        metadata={"doc": ("Classification metadata for the change.")},
    )


@dataclass(slots=True)
class ClassifiedChanges:
    """
    Collection of classified changes grouped for review/export.

    This model is intentionally mutable. A workflow may enrich it
    incrementally with findings, review metadata or export artifacts.
    """

    created_objects: list[ClassifiedChange] = field(
        default_factory=list,
        metadata={"doc": ("Permitted insert changes.")},
    )

    altered_objects: list[ClassifiedChange] = field(
        default_factory=list,
        metadata={"doc": ("Permitted update changes.")},
    )

    deleted_objects: list[ClassifiedChange] = field(
        default_factory=list,
        metadata={"doc": ("Permitted delete changes.")},
    )

    unpermitted_changes: list[ClassifiedChange] = field(
        default_factory=list,
        metadata={"doc": ("Changes rejected by rights evaluation or validation.")},
    )

    metadata: dict[
        str,
        str,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Workflow-level metadata for the classified change set. "
                "Examples: source model, import schema, provider oid, "
                "dataowner oid, job id, output folder."
            )
        },
    )

    def all_changes(
        self,
    ) -> tuple[ClassifiedChange, ...]:
        """
        Return all classified changes in review order.
        """

        return (
            *self.created_objects,
            *self.altered_objects,
            *self.deleted_objects,
            *self.unpermitted_changes,
        )

    def add(
        self,
        classified_change: ClassifiedChange,
    ) -> None:
        """
        Add a classified change to the matching group.
        """

        classification = classified_change.metadata.classification

        if classification == ChangeClassification.CREATED_OBJECT:
            self.created_objects.append(
                classified_change,
            )
            return

        if classification == ChangeClassification.ALTERED_OBJECT:
            self.altered_objects.append(
                classified_change,
            )
            return

        if classification == ChangeClassification.DELETED_OBJECT:
            self.deleted_objects.append(
                classified_change,
            )
            return

        if classification == ChangeClassification.UNPERMITTED_CHANGE:
            self.unpermitted_changes.append(
                classified_change,
            )
            return

        raise ValueError(f"Unsupported change classification: {classification}")


@dataclass(slots=True, frozen=True)
class ValidationFinding(Finding):
    """
    One validation finding emitted during validation.
    """

    code: str = field(
        metadata={"doc": ("Stable machine-readable validation identifier.")},
    )

    attribute_name: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Affected canonical attribute identifier if the finding "
                "applies to a specific attribute."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class AttributeValidation:
    """
    Describes a validation rule attached to an attribute.

    This is intentionally lightweight. The `id` identifies the validation
    implementation, while `level` controls the emitted severity.
    """

    id: str = field(
        metadata={
            "doc": (
                "Identifier of the validation rule, for example `newer_than_existing`."
            )
        },
    )

    level: Severity = field(
        metadata={"doc": ("Severity emitted when this validation produces a finding.")},
    )

    operations: list[ChangeOperation] = field(
        default_factory=lambda: (
            ChangeOperation.INSERT,
            ChangeOperation.UPDATE,
            ChangeOperation.DELETE,
        ),
        metadata={
            "doc": (
                "List of ChangeOperations on which the AttributeValidation "
                "is executed. Defaults to insert, update and delete"
            )
        },
    )

    context_value: str = field(
        default=None,
        metadata={
            "doc": (
                "Optional context value name that is needed for validation, "
                "for example `provider_oid` or `dataowner_oid`."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class TransitionValidation:
    """
    Describes transition validation for a class based on  state-like attributes.

    The transition graph is expressed as a set of `StateTransitionRule`
    instances. `allow_transitive` controls whether indirect paths through
    the transition graph are accepted.
    """

    ruleset: frozenset[StateTransitionRule] = field(
        metadata={"doc": ("Allowed state transition rules for the attribute.")},
    )

    allow_transitive: bool = field(
        default=True,
        metadata={
            "doc": (
                "Whether transitive transitions are allowed. If true, a "
                "transition may be accepted when a path exists through the "
                "transition graph, even if no direct edge exists."
            )
        },
    )
