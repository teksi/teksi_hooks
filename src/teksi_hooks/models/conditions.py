from dataclasses import dataclass, field


class Condition:
    """
    Base marker class for rule conditions.

    Conditions are predicates used to restrict when an authorization rule
    applies. Concrete condition classes describe how values are read and
    compared during rule evaluation.
    """


@dataclass(slots=True, frozen=True)
class AnyOfCondition(Condition):
    """
    Composite condition that is true if at least one child condition is true.

    This represents a logical OR between the contained conditions.
    """

    conditions: tuple[Condition, ...] = field(
        metadata={"doc": ("Conditions of which at least one must evaluate to true.")},
    )


@dataclass(slots=True, frozen=True)
class AllOfCondition(Condition):
    """
    Composite condition that is true only if all child conditions are true.

    This represents a logical AND between the contained conditions.
    """

    conditions: tuple[Condition, ...] = field(
        metadata={"doc": ("Conditions that must all evaluate to true.")},
    )


@dataclass(slots=True, frozen=True)
class LocalCondition(Condition):
    """
    Condition evaluated against the current object.

    A local condition reads an attribute from the object currently being
    validated and compares it using the configured operator and optional
    value.
    """

    attribute: str = field(
        metadata={"doc": ("Name of the local attribute to evaluate.")},
    )

    operator: str = field(
        metadata={
            "doc": (
                "Comparison operator to apply, for example `equals`, "
                "`is_null`, `in` or `equals_context`."
            )
        },
    )

    value: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional comparison value. Some operators, such as "
                "`is_null`, may not require a value."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class RemoteCondition(Condition):
    """
    Condition evaluated against a related object.

    A remote condition follows a relation from the current object, reads an
    attribute on the related object and compares it using the configured
    operator and optional value.
    """

    relation: str = field(
        metadata={"doc": ("Name of the relation used to reach the related object.")},
    )

    attribute: str = field(
        metadata={"doc": ("Name of the attribute on the related object to evaluate.")},
    )

    operator: str = field(
        metadata={
            "doc": (
                "Comparison operator to apply, for example `equals`, "
                "`is_null`, `in` or `equals_context`."
            )
        },
    )

    value: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional comparison value. Some operators may not require a value."
            )
        },
    )
