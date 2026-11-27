from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from geoalchemy2.elements import WKBElement

from ..exceptions import Finding, Severity
from .canonical_object import CanonicalObjectIdentity
from .privilege import PrivilegeId
from .rulesets import StateTransitionRule


@dataclass(slots=True, frozen=True)
class ValidationContext:
    """
    Runtime context supplied to validation implementations.
    """

    class_id: str = field(
        metadata={"doc": ("Canonical class identifier being validated.")},
    )

    identity: CanonicalObjectIdentity | None = field(
        default=None,
        metadata={
            "doc": (
                "Canonical identity of the object being validated. "
                "This may be None for an inserted object whose complete "
                "canonical identity has not yet been derived."
            )
        },
    )

    attribute_name: str | None = field(
        default=None,
        metadata={"doc": ("Canonical attribute identifier being validated.")},
    )

    old_value: Any = field(
        default=None,
        metadata={"doc": ("Existing attribute value before the change.")},
    )

    new_value: Any = field(
        default=None,
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

    identity: CanonicalObjectIdentity = field(
        metadata={"doc": ("Complete canonical identity of the changed object.")},
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
        Return attributes whose old and new values differ.

        Some database-backed values, notably GeoAlchemy ``WKBElement`` values,
        implement comparison by returning a SQL expression rather than a Python
        boolean. Such a result cannot be evaluated with ``bool()`` and is treated
        conservatively as changed.

        Exact spatial equality must be evaluated earlier by the module's effect
        evaluator. This property only identifies attributes represented in the
        resulting Change.
        """

        attribute_names = set(self.old_values) | set(self.new_values)

        return frozenset(
            AttributeChange(
                attribute_name=attribute_name,
                old_value=self.old_values.get(attribute_name),
                new_value=self.new_values.get(attribute_name),
            )
            for attribute_name in attribute_names
            if self._values_differ(
                attribute_name=attribute_name,
                old_value=self.old_values.get(
                    attribute_name,
                ),
                new_value=self.new_values.get(
                    attribute_name,
                ),
            )
        )

    @property
    def table_name(
        self,
    ) -> str:
        """
        Return the canonical class identifier.

        This property preserves the existing Change API while the canonical
        identity remains authoritative.
        """

        return self.identity.class_id

    @property
    def object_id(
        self,
    ) -> str:
        """
        Return the scalar value of a single-attribute identity.

        The identity attribute is not assumed to be ``obj_id``. For example,
        ``agxx_last_modification`` is identified through ``fk_element``.

        Code that needs the identity attribute name must use ``identity``
        directly.
        """

        if (
            len(
                self.identity.attributes,
            )
            != 1
        ):
            raise ValueError(
                "A scalar object_id is unavailable for canonical "
                f"class {self.identity.class_id!r} because its "
                "identity does not contain exactly one attribute: "
                f"{tuple(self.identity.attributes)!r}."
            )

        value = next(
            iter(
                self.identity.attributes.values(),
            )
        )

        return str(
            value,
        )

    @property
    def identity_attribute(
        self,
    ) -> str:
        """
        Return the attribute name of a single-attribute identity.

        This compatibility helper supports persistence code that stores a
        scalar object identifier while still needing to know its canonical
        attribute.
        """

        if (
            len(
                self.identity.attributes,
            )
            != 1
        ):
            raise ValueError(
                "A scalar identity attribute is unavailable for "
                f"canonical class {self.identity.class_id!r}: "
                f"{tuple(self.identity.attributes)!r}."
            )

        return next(
            iter(
                self.identity.attributes,
            )
        )

    @classmethod
    def _values_differ(
        cls,
        *,
        attribute_name: str,
        old_value,
        new_value,
    ) -> bool:
        """
        Return whether two attribute values differ.

        Geometry-to-geometry comparison is temporarily skipped for the POC.
        Geometry creation and removal remain changes because those comparisons
        have exactly one null value.
        """
        del attribute_name

        if old_value is new_value:
            return False

        if old_value is None or new_value is None:
            return True

        if isinstance(
            old_value,
            WKBElement,
        ) and isinstance(
            new_value,
            WKBElement,
        ):
            # TODO: Replace this bypass with geometry harmonization before
            # constructing Change instances.
            return False

        comparison = old_value != new_value

        if isinstance(
            comparison,
            bool,
        ):
            return comparison

        raise TypeError(
            "Attribute comparison returned a non-boolean result. "
            f"Old value type: {type(old_value)!r}; "
            f"new value type: {type(new_value)!r}; "
            f"comparison type: {type(comparison)!r}."
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
        default_factory=lambda: datetime.now(UTC),
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

    parameters: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Validation-specific configuration values interpreted by the "
                "selected validation implementation. Generic validation "
                "orchestration must not assign semantics to these entries."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ObjectValidation:
    """
    Describes a validation rule attached to a canonical object.

    The rule identifier selects the validation implementation, while the
    severity controls the finding emitted by a failed validation.
    """

    id: str = field(
        metadata={
            "doc": (
                "Identifier of the object-level validation implementation, "
                "for example 'is_unique'."
            )
        },
    )

    level: Severity = field(
        metadata={"doc": ("Severity emitted when the validation produces a finding.")},
    )

    operations: tuple[
        ChangeOperation,
        ...,
    ] = field(
        default_factory=lambda: (
            ChangeOperation.INSERT,
            ChangeOperation.UPDATE,
        ),
        metadata={
            "doc": (
                "Change operations for which this object validation is "
                "executed. Defaults to inserts and updates."
            )
        },
    )

    parameters: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Validation-specific configuration values interpreted by the "
                "selected validation implementation. Generic validation "
                "orchestration must not assign semantics to these entries."
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


@dataclass(
    slots=True,
    frozen=True,
)
class ClassValidationDefinition:
    """
    Validation configuration declared for one canonical class.

    Class-specific mandatory attributes extend the defaults. Attribute and
    object validation entries with the same key replace their corresponding
    default entries.
    """

    class_id: str = field(
        metadata={"doc": ("Canonical identifier of the configured class.")},
    )

    mandatory_attributes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Class-specific canonical attributes that require a value. "
                "These attributes extend the default mandatory attributes."
            )
        },
    )

    attribute_validations: Mapping[
        str,
        tuple[
            AttributeValidation,
            ...,
        ],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Class-specific attribute validation rules keyed by "
                "canonical attribute identifier."
            )
        },
    )

    object_validations: Mapping[
        str,
        tuple[
            ObjectValidation,
            ...,
        ],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Class-specific object validation groups keyed by "
                "configuration identifier."
            )
        },
    )


@dataclass(
    slots=True,
    frozen=True,
)
class ValidationDefinition:
    """
    Parsed canonical validation configuration.

    Default definitions apply to every configured class unless that class
    is excluded from the corresponding default category. Class-specific
    definitions are applied after the applicable defaults.
    """

    mandatory_attributes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={"doc": ("Canonical attributes considered mandatory by default.")},
    )

    attribute_validations: Mapping[
        str,
        tuple[
            AttributeValidation,
            ...,
        ],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Default attribute validation rules keyed by canonical "
                "attribute identifier."
            )
        },
    )

    object_validations: Mapping[
        str,
        tuple[
            ObjectValidation,
            ...,
        ],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Default object validation groups keyed by configuration identifier."
            )
        },
    )

    classes: Mapping[
        str,
        ClassValidationDefinition,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Class-specific validation definitions keyed by canonical "
                "class identifier."
            )
        },
    )

    mandatory_excluded_classes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Canonical class identifiers for which default mandatory "
                "attributes do not apply. Class-specific mandatory "
                "attributes remain effective."
            )
        },
    )

    attribute_validation_excluded_classes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Canonical class identifiers for which default attribute "
                "validation rules do not apply. Class-specific attribute "
                "validation rules remain effective."
            )
        },
    )

    object_validation_excluded_classes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Canonical class identifiers for which default object "
                "validation groups do not apply. Class-specific object "
                "validation groups remain effective."
            )
        },
    )

    def mandatory_for_class(
        self,
        class_id: str,
    ) -> frozenset:
        """
        Return effective mandatory attributes for one canonical class.

        Default mandatory attributes are omitted when the class is listed in
        ``mandatory_excluded_classes``. Class-specific mandatory attributes
        always apply.
        """
        if class_id in self.mandatory_excluded_classes:
            mandatory_attributes = frozenset()
        else:
            mandatory_attributes = self.mandatory_attributes

        class_definition = self.classes.get(
            class_id,
        )

        if class_definition is None:
            return mandatory_attributes

        return mandatory_attributes | class_definition.mandatory_attributes

    def attribute_validations_for_class(
        self,
        class_id: str,
    ) -> dict[
        str,
        tuple[
            AttributeValidation,
            ...,
        ],
    ]:
        """
        Return effective attribute validations for one canonical class.

        Default attribute-validation groups are omitted when the class is
        listed in ``attribute_validation_excluded_classes``. Class-specific
        entries always apply and replace applicable defaults with the same
        attribute identifier.
        """
        if class_id in self.attribute_validation_excluded_classes:
            validations: dict[
                str,
                tuple[
                    AttributeValidation,
                    ...,
                ],
            ] = {}
        else:
            validations = dict(
                self.attribute_validations,
            )

        class_definition = self.classes.get(
            class_id,
        )

        if class_definition is not None:
            validations.update(
                class_definition.attribute_validations,
            )

        return validations

    def object_validations_for_class(
        self,
        class_id: str,
    ) -> dict[
        str,
        tuple[
            ObjectValidation,
            ...,
        ],
    ]:
        """
        Return effective object validations for one canonical class.

        Default object-validation groups are omitted when the class is listed
        in ``object_validation_excluded_classes``. Class-specific groups always
        apply and replace applicable defaults with the same configuration
        identifier.
        """
        if class_id in self.object_validation_excluded_classes:
            validations: dict[
                str,
                tuple[
                    ObjectValidation,
                    ...,
                ],
            ] = {}
        else:
            validations = dict(
                self.object_validations,
            )

        class_definition = self.classes.get(
            class_id,
        )

        if class_definition is not None:
            validations.update(
                class_definition.object_validations,
            )

        return validations
