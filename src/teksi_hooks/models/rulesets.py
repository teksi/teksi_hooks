from dataclasses import dataclass, field

from .conditions import Condition
from .privilege import PrivilegeId


class Rule:
    """
    Base marker class for authorization rules.

    Rule subclasses describe how a requested operation may be authorized.
    They are evaluated by the rights engine against the current provider,
    object state, operation type and optional conditions.
    """


@dataclass(slots=True, frozen=True)
class PrivilegeRule(Rule):
    """
    Authorizes an operation based on one or more required privileges.

    A privilege rule may optionally be guarded by a condition. If a condition
    is present, the rule only applies when the condition evaluates to true.
    """

    privileges: frozenset[PrivilegeId] = field(
        metadata={
            "doc": (
                "Privileges that grant the operation if this rule applies. "
                "The provider must have at least one of these privileges in "
                "the relevant data-owner context."
            )
        },
    )

    when: Condition | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional condition restricting when this privilege rule "
                "applies. If omitted, the rule applies unconditionally."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class OwnershipRule(Rule):
    """
    Authorizes an operation based on ownership.

    Ownership is evaluated by comparing a provider-related value with the
    value stored in the configured attribute. For updates and deletes this
    should be evaluated against the existing database row. For inserts this
    should be evaluated against the submitted row.
    """

    attribute: str = field(
        metadata={
            "doc": (
                "Attribute used to determine ownership. Typical example: `fk_provider`."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class InheritRule(Rule):
    """
    Reuses another rule set.

    This is used for declarations such as `inherit: create_rules` or
    `inherit: update_rules`. The resolver expands inherited rules into
    effective rules before runtime evaluation.
    """

    source: str = field(
        metadata={
            "doc": (
                "Name of the rule set to inherit from, for example "
                "`create_rules`, `update_rules` or `delete_rules`."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class StateTransitionRule(Rule):
    """
    Authorizes a state transition for an attribute.

    A state transition rule describes one permitted edge in a state graph.
    It is usually attached to an attribute such as `status`.
    """

    privileges: frozenset[PrivilegeId] = field(
        metadata={"doc": ("Privileges that grant this specific transition.")},
    )

    from_value: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Allowed source value of the transition. If omitted, the "
                "transition may be interpreted as matching any source value, "
                "depending on the resolver semantics."
            )
        },
    )

    to_value: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Allowed target value of the transition. If omitted, the "
                "transition may be interpreted as matching any target value, "
                "depending on the resolver semantics."
            )
        },
    )

    bilateral: bool = field(
        default=False,
        metadata={
            "doc": (
                "Whether the transition is allowed in both directions. If "
                "true, `from_value -> to_value` also allows "
                "`to_value -> from_value`."
            )
        },
    )


@dataclass(slots=True)
class CrudRules:
    """
    Mutable rule container for parsed CRUD authorization rules.

    This model represents the rules as loaded from configuration before the
    resolver expands defaults, inheritance and shortcuts. The resolved model
    should use `ResolvedCrudRules`.
    """

    create_rules: list[Rule] = field(
        default_factory=list,
        metadata={"doc": ("Rules governing creation of new objects.")},
    )

    read_rules: list[Rule] = field(
        default_factory=list,
        metadata={
            "doc": (
                "Rules governing read access. Currently not required by the "
                "import validation workflow, but included for future use."
            )
        },
    )

    update_rules: list[Rule] = field(
        default_factory=list,
        metadata={"doc": ("Rules governing updates to existing objects.")},
    )

    delete_rules: list[Rule] = field(
        default_factory=list,
        metadata={"doc": ("Rules governing deletion of existing objects.")},
    )


@dataclass(slots=True, frozen=True)
class ResolvedCrudRules:
    """
    Immutable rule container for compiled CRUD authorization rules.

    This model is produced by the resolver and should be consumed by runtime
    components such as hooks and validators. Lists from `CrudRules` are
    converted to tuples to make the resolved rule set immutable.
    """

    create_rules: tuple[Rule, ...] = field(
        metadata={"doc": ("Resolved rules governing creation of new objects.")},
    )

    read_rules: tuple[Rule, ...] = field(
        metadata={"doc": ("Resolved rules governing read access.")},
    )

    update_rules: tuple[Rule, ...] = field(
        metadata={"doc": ("Resolved rules governing updates to existing objects.")},
    )

    delete_rules: tuple[Rule, ...] = field(
        metadata={"doc": ("Resolved rules governing deletion of existing objects.")},
    )
