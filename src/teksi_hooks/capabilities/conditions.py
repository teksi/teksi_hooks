from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..models.conditions import (
    AllOfCondition,
    AnyOfCondition,
    Condition,
    LocalCondition,
    RemoteCondition,
)


@dataclass(slots=True, frozen=True)
class ConditionEvaluationContext:
    """
    Runtime values available during condition evaluation.

    Conditions should be evaluated against explicit runtime data rather than
    fetching database state directly. This keeps the condition evaluator pure
    and easy to test.
    """

    local_values: Mapping[str, Any] = field(
        metadata={
            "doc": (
                "Values of the object currently being evaluated, keyed by "
                "attribute name."
            )
        },
    )

    remote_values: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Values of related objects, keyed first by relation name and "
                "then by attribute name."
            )
        },
    )

    context_values: Mapping[str, Any] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "External runtime context values, for example provider id, "
                "dataowner id or organisation id."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ConditionsCapability:
    """
    Evaluates condition models against runtime values.

    This capability is intentionally stateless. It evaluates logical,
    local and remote conditions using a supplied `ConditionEvaluationContext`.

    It does not fetch related objects itself. Remote values must be provided
    by the caller or by a higher-level evaluator.
    """

    def evaluate(
        self,
        condition: Condition | None,
        context: ConditionEvaluationContext,
    ) -> bool:
        """
        Evaluate a condition against the given runtime context.

        A missing condition is treated as true. This is useful for rules where
        `when` is optional.
        """

        if condition is None:
            return True

        if isinstance(condition, AnyOfCondition):
            return self.evaluate_any(
                condition,
                context,
            )

        if isinstance(condition, AllOfCondition):
            return self.evaluate_all(
                condition,
                context,
            )

        if isinstance(condition, LocalCondition):
            return self.evaluate_local(
                condition,
                context,
            )

        if isinstance(condition, RemoteCondition):
            return self.evaluate_remote(
                condition,
                context,
            )

        raise TypeError(f"Unsupported condition type: {type(condition)!r}")

    def evaluate_any(
        self,
        condition: AnyOfCondition,
        context: ConditionEvaluationContext,
    ) -> bool:
        """
        Evaluate a logical OR condition.
        """

        return any(
            self.evaluate(
                child,
                context,
            )
            for child in condition.conditions
        )

    def evaluate_all(
        self,
        condition: AllOfCondition,
        context: ConditionEvaluationContext,
    ) -> bool:
        """
        Evaluate a logical AND condition.
        """

        return all(
            self.evaluate(
                child,
                context,
            )
            for child in condition.conditions
        )

    def evaluate_local(
        self,
        condition: LocalCondition,
        context: ConditionEvaluationContext,
    ) -> bool:
        """
        Evaluate a condition against the current object values.
        """

        actual_value = context.local_values.get(
            condition.attribute,
        )

        return self.compare(
            actual_value=actual_value,
            operator=condition.operator,
            expected_value=condition.value,
            context=context,
        )

    def evaluate_remote(
        self,
        condition: RemoteCondition,
        context: ConditionEvaluationContext,
    ) -> bool:
        """
        Evaluate a condition against a related object.

        The related object values must be present in
        `context.remote_values[condition.relation]`.
        """

        related_values = context.remote_values.get(
            condition.relation,
        )

        if related_values is None:
            return False

        actual_value = related_values.get(
            condition.attribute,
        )

        return self.compare(
            actual_value=actual_value,
            operator=condition.operator,
            expected_value=condition.value,
            context=context,
        )

    def compare(
        self,
        actual_value: Any,
        operator: str,
        expected_value: Any,
        context: ConditionEvaluationContext,
    ) -> bool:
        """
        Compare an actual value using the configured operator.

        Supported operators should mirror the YAML condition DSL.
        """

        match operator:
            case "equals":
                return actual_value == expected_value

            case "not_equals":
                return actual_value != expected_value

            case "is_null":
                return actual_value is None

            case "is_not_null":
                return actual_value is not None

            case "in":
                return actual_value in self._as_collection(
                    expected_value,
                )

            case "not_in":
                return actual_value not in self._as_collection(
                    expected_value,
                )

            case "equals_context":
                return actual_value == context.context_values.get(
                    expected_value,
                )

            case _:
                raise ValueError(f"Unsupported condition operator: {operator!r}")

    def _as_collection(
        self,
        value: Any,
    ) -> tuple[Any, ...]:
        """
        Normalize a condition value to a tuple for `in` and `not_in`.

        Strings are treated as scalar values, not as iterables.
        """

        if value is None:
            return ()

        if isinstance(value, str):
            return (value,)

        if isinstance(value, tuple):
            return value

        if isinstance(value, list):
            return tuple(value)

        if isinstance(value, set):
            return tuple(value)

        return (value,)
