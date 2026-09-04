from __future__ import annotations
from dataclasses import dataclass, field
from collections.abc import Callable
from datetime import datetime


from ..models.validation import (
    ValidationContext,
    ValidationFinding,
    AttributeValidation,
    ObjectValidation,
)
from ..exceptions import Severity


@dataclass(slots=True)
class ValidationResult:
    """
    Collects validation findings produced during hook execution.

    The internal finding list is mutable so validators can append findings.
    Consumers receive an immutable tuple through the `findings` property.
    """

    _findings: list[ValidationFinding] = field(
        default_factory=list,
    )

    @property
    def findings(
        self,
    ) -> tuple[ValidationFinding, ...]:
        """
        Return collected validation findings as an immutable tuple.
        """

        return tuple(
            self._findings,
        )

    def add(
        self,
        severity: Severity,
        message: str,
    ) -> None:
        """
        Add a validation finding.
        """

        self._findings.append(
            ValidationFinding(
                severity=severity,
                message=message,
            )
        )

    def error(
        self,
        message: str,
    ) -> None:
        """
        Add an error finding.
        """

        self.add(
            Severity.ERROR,
            message,
        )

    def warning(
        self,
        message: str,
    ) -> None:
        """
        Add a warning finding.
        """

        self.add(
            Severity.WARNING,
            message,
        )

    def info(
        self,
        message: str,
    ) -> None:
        """
        Add an informational finding.
        """

        self.add(
            Severity.INFO,
            message,
        )

    def has(
        self,
        severity: Severity,
    ) -> bool:
        """
        Return whether at least one finding with the given severity exists.
        """

        return any(finding.severity == severity for finding in self._findings)

    @property
    def has_errors(
        self,
    ) -> bool:
        """
        Return whether at least one error finding exists.
        """

        return self.has(
            Severity.ERROR,
        )


class ValidationRegistry:
    def validation(
        self,
        validation_id: str,
    ) -> Callable:
        if validation_id == "newer_than_existing":
            return self._validate_newer_than_existing

        if validation_id == "cannot_decrease":
            return self._validate_cannot_decrease

        if validation_id == "equals_context_value":
            return self._equals_context_value

        if validation_id == "is_unique":
            return self._is_unique

        raise NotImplementedError(f"Unknown validation: {validation_id}")

    def _validate_newer_than_existing(
        self,
        *,
        validation: AttributeValidation,
        context: ValidationContext,
    ) -> tuple[ValidationFinding, ...]:
        if context.old_value is None or context.new_value is None:
            return ()

        old_dt = self._as_datetime(
            context.old_value,
        )

        new_dt = self._as_datetime(
            context.new_value,
        )

        if new_dt >= old_dt:
            return ()

        return (
            ValidationFinding(
                code=validation.id,
                severity=validation.level,
                message=("New value must be newer than the existing value."),
                attribute_name=context.attribute_name,
            ),
        )

    def _validate_cannot_decrease(
        self,
        *,
        validation: AttributeValidation,
        context: ValidationContext,
    ) -> tuple[ValidationFinding, ...]:
        if context.old_value is None or context.new_value is None:
            return ()

        if context.new_value >= context.old_value:
            return ()

        return (
            ValidationFinding(
                code=validation.id,
                severity=validation.level,
                message=("New value must not be smaller than the existing value."),
                attribute_name=context.attribute_name,
            ),
        )

    def _equals_context_value(
        self,
        *,
        validation: AttributeValidation,
        context: ValidationContext,
    ) -> tuple:
        if validation.context_value is None:
            return (
                ValidationFinding(
                    code=validation.id,
                    severity=validation.level,
                    message=("Validation requires a context value name."),
                    attribute_name=context.attribute_name,
                ),
            )

        if validation.context_value not in context.context_values:
            return (
                ValidationFinding(
                    code=validation.id,
                    severity=validation.level,
                    message=(f"Context value {validation.context_value!r} is missing."),
                    attribute_name=context.attribute_name,
                ),
            )

        expected_value = context.context_values[validation.context_value]

        if str(context.new_value) == str(expected_value):
            return ()

        return (
            ValidationFinding(
                code=validation.id,
                severity=validation.level,
                message=(
                    f"Value of {context.attribute_name!r} must match "
                    f"context value {validation.context_value!r}."
                ),
                attribute_name=context.attribute_name,
            ),
        )

    def _is_unique(
        self,
        *,
        validation: ObjectValidation,
        context: ValidationContext,
    ):
        pass

    def _as_datetime(
        self,
        value,
    ) -> datetime:
        if isinstance(
            value,
            datetime,
        ):
            return value

        return datetime.fromisoformat(
            str(value),
        )
