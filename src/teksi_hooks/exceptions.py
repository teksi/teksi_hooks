from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from collections.abc import Iterable


# Base exception for all TEKSI Hook errors
class TeksiHookException(Exception):
    """Base class for all exceptions raised by TEKSI Hooks.

    Version Added:
        1.0.0
    """


class TeksiHookError(TeksiHookException):
    """Exception raised for errors by an invalid hook.

    Version Added:
        1.0.0
    """

    """
    Base class for framework failures backed by findings.
    """

    def __init__(
        self,
        findings: tuple[Finding, ...],
    ):
        if isinstance(
            findings,
            str,
        ):
            findings = (
                Finding(
                    severity=Severity.ERROR,
                    message=findings,
                ),
            )

        self.findings = findings

        super().__init__("\n".join(finding.message for finding in findings))

    @classmethod
    def raise_if_errors(
        cls,
        findings: Iterable[Finding],
    ) -> None:
        errors = tuple(
            finding for finding in findings if finding.severity == Severity.ERROR
        )

        if errors:
            raise cls(errors)

    @classmethod
    def from_message(
        cls,
        message: str,
        severity: Severity | str | None = None,
    ) -> TeksiHookError:
        """
        Create an error containing a single finding.

        Severity defaults to `Severity.ERROR`. String values must correspond
        to one of the values defined by `Severity`.
        """

        try:
            if severity is None:
                resolved_severity = Severity.ERROR
            elif isinstance(severity, Severity):
                resolved_severity = severity
            elif isinstance(severity, str):
                resolved_severity = Severity(severity.lower())
        except ValueError as error:
            allowed_severities = ", ".join(member.value for member in Severity)

            raise ValueError(
                f"Invalid severity {severity!r} for message {message!r}. "
                f"Expected one of: {allowed_severities}."
            ) from error

        return cls(
            findings=(
                Finding(
                    severity=resolved_severity,
                    message=message,
                ),
            ),
        )


class ValidationError(
    TeksiHookError,
):
    """
    Base class for validation-related failures.
    """


class EffectValidationError(
    ValidationError,
):
    """
    EffectDocument contains invalid or contradictory effects.
    """


class RightsEvaluationError(
    TeksiHookError,
):
    """
    Rights evaluation could not be completed.
    """


class SnapshotValidationError(
    ValidationError,
):
    """
    Snapshot validation failed due to invalid snapshot state.
    """


class Severity(StrEnum):
    """
    Severity levels used by findings.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class Finding:
    """
    Base class for findings.
    """

    severity: Severity = field(
        metadata={"doc": ("Severity level assigned to the finding.")},
    )

    message: str = field(
        metadata={"doc": ("Human-readable description of the validation issue.")},
    )
