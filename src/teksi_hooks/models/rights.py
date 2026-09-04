from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any

from .privilege import PrivilegeId, PrivilegeMetadata
from .validation import AttributeValidation, TransitionValidation, ObjectValidation
from .rulesets import CrudRules, ResolvedCrudRules, StateTransitionRule
from .canonical_object import CanonicalObjectIdentity
from pathlib import Path
from .oid import Oid
from ..exceptions import Finding


@dataclass(slots=True)
class RightsProfile:
    identifier: str = field(
        metadata={
            "doc": (
                "Unique identifier of the entity to which the rights profile applies. "
                "If None, defaults to the template path."
            )
        },
    )
    provider_rights_path: Path = field(
        metadata={
            "doc": (
                "Path to the provider rights yaml. "
                "If None, defaults to the template path."
            )
        },
    )
    provider_privileges_path: Path = field(
        metadata={
            "doc": (
                "Path to the provider privilege yaml. "
                "If None, defaults to the template path."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class PermissionFinding(
    Finding,
):
    """
    Finding produced by rights / permission evaluation.

    A permission finding means the proposed change may be structurally valid,
    but is not allowed for the current provider, data owner, privilege context
    or rights rule configuration.
    """

    code: str = field(
        metadata={
            "doc": (
                "Stable permission finding code. Examples: "
                "'permission_denied', 'missing_privilege', "
                "'provider_not_authorized'."
            )
        },
    )

    attribute_name: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Canonical attribute involved in the permission finding, "
                "or None if the finding applies to the whole object/change."
            )
        },
    )

    rule_id: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Identifier of the rights rule or condition that denied the "
                "change, if available."
            )
        },
    )

    provider_oid: Oid | None = field(
        default=None,
        metadata={
            "doc": (
                "Provider organisation oid used during rights evaluation, if relevant."
            )
        },
    )

    dataowner_oid: Oid | None = field(
        default=None,
        metadata={
            "doc": (
                "Data owner organisation oid used during rights evaluation, "
                "if relevant."
            )
        },
    )

    required_privilege: PrivilegeId | None = field(
        default=None,
        metadata={"doc": ("Privilege required for the attempted operation, if known.")},
    )

    available_privileges: tuple[PrivilegeId, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Privileges available to the evaluated provider/data owner context."
            )
        },
    )

    evaluation_path: tuple[str, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Optional rights evaluation path. Useful for derived or "
                "recursive rights, for example "
                "('reach_point', 'reach', 'wastewater_structure')."
            )
        },
    )

    transitive_evaluation_enabled: bool | None = field(
        default=None,
        metadata={
            "doc": (
                "Whether transitive or recursive rights evaluation was enabled "
                "when this permission finding was produced."
            )
        },
    )

    details: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Additional permission finding details that are useful for "
                "debugging, reporting or future rule types."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ResolvedRights:
    """
    Fully resolved rights configuration.

    This object aggregates all resolver outputs required by runtime
    capabilities and evaluators.
    """

    classes: Mapping[
        str,
        ResolvedClassDefinition,
    ] = field(
        metadata={
            "doc": ("Resolved class definitions keyed by canonical class identifier.")
        },
    )

    derived_rights: Mapping[
        str,
        tuple[DerivedRights, ...],
    ] = field(
        metadata={
            "doc": (
                "Rights derivation definitions keyed by canonical class identifier."
            )
        },
    )

    subclass_rights: Mapping[
        str,
        tuple[str, ...],
    ] = field(
        metadata={
            "doc": (
                "Subclass rights mappings keyed by canonical parent class identifier."
            )
        },
    )

    allow_transitive_transitions: bool = field(
        default=True,
        metadata={
            "doc": (
                "Whether rights mappings allow for transitive "
                "transitions. Defaults to True."
            )
        },
    )


@dataclass(slots=True)
class RightsDefinition:
    """
    Parsed rights configuration.

    This is the top-level object produced by the rights parser before
    inheritance, defaults, derived rights and rule references are resolved.

    Runtime validation should use resolved class definitions instead.
    """

    privileges: Mapping[
        PrivilegeId,
        PrivilegeMetadata,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Privilege definitions keyed by privilege identifier. "
                "These definitions provide metadata such as localized "
                "labels and descriptions for privilege references used "
                "throughout the rights configuration."
            )
        },
    )

    defaults: DefaultDefinitions = field(
        default_factory=lambda: DefaultDefinitions(
            crud_rules=CrudRules(),
        ),
        metadata={
            "doc": (
                "Global default definitions applied by the resolver when "
                "class-level rules are missing."
            )
        },
    )

    classes: Mapping[str, ClassDefinition] = field(
        default_factory=dict,
        metadata={
            "doc": ("Parsed class definitions keyed by canonical class identifier.")
        },
    )

    validation_rules: Mapping[
        str,
        tuple[AttributeValidation, ...],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Global attribute validation rules keyed by attribute name. "
                "Example: `last_modification`."
            )
        },
    )

    allow_transitive_transitions: bool = field(
        default=True,
        metadata={
            "doc": (
                "Whether transition validation may accept transitive paths "
                "through the configured transition graph."
            )
        },
    )


@dataclass(slots=True)
class DefaultDefinitions:
    """
    Global default rights definitions.

    Defaults are applied by the resolver when a class does not define its own
    corresponding rule set. Class-level definitions override these defaults.
    """

    crud_rules: CrudRules = field(
        default_factory=CrudRules,
        metadata={
            "doc": (
                "Default CRUD rules applied to classes that do not explicitly "
                "define their own rules."
            )
        },
    )

    attribute_defaults: tuple[AttributeDefaultDefinition, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Default attribute-level rights applied by attribute-name "
                "pattern. These defaults are resolved against concrete "
                "attributes by the resolver. Example: `ag64_*` may grant "
                "`DBW_WI`, while `ag96_*` may grant `DBW_GEP`."
            )
        },
    )
    attribute_validation_rules: Mapping[
        str,
        tuple[AttributeValidation, ...],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Default attribute validation rules keyed by canonical "
                "attribute identifier. The resolver copies matching rules "
                "into AttributeDefinition.validations."
            )
        },
    )

    object_validation_rules: Mapping[
        str,
        ObjectValidation,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Named object-level validation definitions. The resolver "
                "applies a definition to classes containing all canonical "
                "value names required by its rules."
            )
        },
    )


@dataclass(slots=True)
class ClassDefinition:
    """
    Parsed class-level rights definition.

    This model represents the rights configuration as loaded from the source
    definition before inheritance, defaults, derived rights, and rule shortcuts
    are resolved.

    `ClassDefinition` is part of the source model. Runtime validation should
    consume `ResolvedClassDefinition` instead.
    """

    id: str = field(
        metadata={
            "doc": (
                "Canonical class identifier. Usually corresponds to a TEKSI "
                "semantic class or table identifier."
            )
        },
    )

    superclass_id: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional canonical class identifier of the superclass from "
                "which this class inherits rights and attributes."
            )
        },
    )

    rights_from_subclass: bool = field(
        default=False,
        metadata={
            "doc": (
                "Whether rights should be evaluated from subclass definitions. "
                "This is mainly used for abstract or inheritance-root classes "
                "whose concrete rights are defined on subclasses."
            )
        },
    )

    derive_rights_from: tuple[DerivedRights, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Optional relations from which rights can be derived. "
                "Derived rights are resolved against related objects and "
                "combined with local rights according to resolver semantics."
            )
        },
    )

    crud_rules: CrudRules = field(
        default_factory=CrudRules,
        metadata={
            "doc": (
                "Parsed CRUD rules for this class. These may include direct "
                "rules, ownership rules and inheritance references."
            )
        },
    )

    attributes: dict[str, AttributeDefinition] = field(
        default_factory=dict,
        metadata={
            "doc": ("Attribute definitions keyed by canonical attribute identifier.")
        },
    )


@dataclass(slots=True, frozen=True)
class ResolvedClassDefinition:
    """
    Resolved and immutable class-level rights definition.

    This model is produced by the rights resolver. It should contain the
    effective rule set after defaults, inheritance, CRUD shortcuts and rule
    inheritance have been applied.

    Runtime hooks and validators should use this model instead of
    `ClassDefinition`.
    """

    id: str = field(
        metadata={"doc": ("Canonical class identifier of the resolved class.")},
    )

    crud_rules: ResolvedCrudRules = field(
        metadata={"doc": ("Fully resolved immutable CRUD rules for this class.")},
    )

    attributes: Mapping[str, ResolvedAttributeDefinition] = field(
        metadata={
            "doc": (
                "Resolved attribute definitions keyed by canonical attribute "
                "identifier."
            )
        },
    )

    transition_rules: Mapping[str, StateTransitionRule] = field(
        metadata={
            "doc": (
                "Resolved state transition rules keyed by canonical attribute "
                "identifier."
            )
        },
    )

    object_validations: tuple[ObjectValidation, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": ("Resolved object-level validation rules for this canonical class.")
        },
    )

    mandatory_attributes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Effective canonical attributes that require a value. "
                "Class-specific declarations extend the validation defaults."
            )
        },
    )
    # add when needed for debugging
    # resolution_info: ResolutionInfo | None = None


@dataclass(slots=True, frozen=True)
class DerivedRights:
    """
    Rights derivation definition.

    Defines how rights of the current class can be derived from a related
    canonical class. The relation is expressed as an attribute equality
    between the local object and the remote object.

    Examples
    --------

    Local foreign key:

        local.fk_wastewater_structure
            =
        wastewater_structure.obj_id

    YAML:

        derive_rights_from:
          - class: wastewater_structure
            local_attribute: fk_wastewater_structure

    Reverse foreign key:

        obj_id
            =
        reach.fk_reach_point_from

    YAML:

        derive_rights_from:
          - class: reach
            remote_attribute: fk_reach_point_from

    Explicit join:

        local.fk_baz
            =
        foo.fk_bar

    YAML:

        derive_rights_from:
          - class: foo
            local_attribute: fk_baz
            remote_attribute: fk_bar
    """

    class_id: str = field(
        metadata={
            "doc": ("Canonical class identifier from which rights may be derived.")
        },
    )

    local_attribute: str = field(
        default="obj_id",
        metadata={
            "doc": (
                "Local attribute participating in the rights-derivation "
                "join. Defaults to `obj_id`."
            )
        },
    )

    remote_attribute: str = field(
        default="obj_id",
        metadata={
            "doc": (
                "Attribute on the related canonical class participating in "
                "the rights-derivation join. Defaults to `obj_id`."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class CanonicalDerivedRights:
    """
    Result of a derived-rights resolution.

    Represents the canonical objects participating in a rights-derivation
    relationship after join evaluation has been performed.
    """

    local_objects: tuple[CanonicalObjectIdentity, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Canonical local objects participating in the resolved "
                "rights-derivation relationship."
            )
        },
    )

    remote_objects: tuple[CanonicalObjectIdentity, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": ("Canonical remote objects from which rights may be derived.")
        },
    )


@dataclass(slots=True)
class AttributeDefinition:
    """
    Rights and validation definition for one canonical attribute.

    Attribute definitions describe attribute-level update privileges, generic
    validations and state transition validations.
    """

    update_privileges: frozenset[PrivilegeId] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Privileges allowed to update this attribute. If empty, the "
                "attribute has no explicit attribute-level update privilege."
            )
        },
    )

    validations: list[AttributeValidation] = field(
        default_factory=list,
        metadata={
            "doc": (
                "Attribute-level validation rules, for example freshness or "
                "data-quality checks."
            )
        },
    )

    transitions: list[TransitionValidation] = field(
        default_factory=list,
        metadata={
            "doc": (
                "Transition validations for state-like attributes. These "
                "define which value transitions are allowed and under which "
                "privileges."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ResolvedAttributeDefinition:
    """
    Effective runtime attribute definition.

    Produced by the rights resolver after wildcard defaults, inheritance,
    attribute defaults and future resolver expansions have been applied.

    Runtime code should consume this model rather than
    `AttributeDefinition`.
    """

    update_privileges: frozenset[PrivilegeId] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Effective privileges allowed to update this attribute "
                "after all defaults and inheritance have been resolved."
            )
        },
    )

    validations: tuple[AttributeValidation, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": ("Effective validation rules for this attribute after resolution.")
        },
    )

    transitions: tuple[TransitionValidation, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Effective transition validations for this attribute after resolution."
            )
        },
    )


@dataclass(slots=True)
class ResolutionInfo:
    """
    Optional debug information produced during rights resolution.

    This model is not required for runtime validation. It can be attached to
    resolved models later if traceability, explanations or debugging output
    become necessary.
    """

    superclass_id: str | None = field(
        default=None,
        metadata={
            "doc": ("Identifier of the superclass used during resolution, if any.")
        },
    )

    derived_from: tuple[DerivedRights, ...] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Derived-rights declarations that contributed to the resolved "
                "definition."
            )
        },
    )

    inherited_attributes: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": ("Attribute identifiers inherited from superclass definitions.")
        },
    )

    inherited_rules: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": ("Rule-set identifiers inherited or expanded during resolution.")
        },
    )


@dataclass(slots=True, frozen=True)
class AttributeDefaultDefinition:
    """
    Default attribute rights applied by attribute-name pattern.

    This is mainly used for compact model definitions where many attributes
    share the same privilege pattern. Example:
        ag64_* -> update: [DBW_WI]
        ag96_* -> update: [DBW_GEP]

    The parser stores the pattern. The resolver decides which concrete
    attributes match the pattern.
    """

    pattern: str = field(
        metadata={
            "doc": (
                "Attribute-name pattern used to match source or canonical "
                "attributes. Usually a simple wildcard pattern such as "
                "`ag64_*`."
            )
        },
    )

    update_privileges: frozenset[PrivilegeId] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Default update privileges applied to attributes matching the pattern."
            )
        },
    )
