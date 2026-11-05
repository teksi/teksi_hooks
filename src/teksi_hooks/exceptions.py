from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum


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


class DiffSchemaError(
    TeksiHookError,
):
    """
    Base class for diff-schema failures.
    """


class DiffJobNotFoundError(
    DiffSchemaError,
):
    """
    Raised when a requested diff review job does not exist.
    """

    def __init__(
        self,
        *,
        job_id: str,
    ) -> None:
        self.job_id = job_id

        super().__init__(
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    message=(f"Diff review job {job_id!r} does not exist."),
                ),
            ),
        )


class DiffJobStateError(
    DiffSchemaError,
):
    """
    Raised when a diff job is not in the required lifecycle state.
    """

    def __init__(
        self,
        *,
        job_id: str,
        expected_status: str,
        actual_status: str,
    ) -> None:
        self.job_id = job_id
        self.expected_status = expected_status
        self.actual_status = actual_status

        super().__init__(
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    message=(
                        f"Diff review job {job_id!r} has status "
                        f"{actual_status!r}; expected "
                        f"{expected_status!r}."
                    ),
                ),
            ),
        )


class DiffJobTransitionError(
    DiffSchemaError,
):
    """
    Raised when a diff-job lifecycle transition cannot be completed.
    """

    def __init__(
        self,
        *,
        job_id: str,
        expected_status: str,
        new_status: str,
        actual_status: str,
    ) -> None:
        self.job_id = job_id
        self.expected_status = expected_status
        self.new_status = new_status
        self.actual_status = actual_status

        super().__init__(
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    message=(
                        f"Diff review job {job_id!r} cannot transition "
                        f"from {expected_status!r} to {new_status!r}. "
                        f"Its current status is {actual_status!r}."
                    ),
                ),
            ),
        )


class DiffJobEligibilityError(
    DiffSchemaError,
):
    """
    Raised when a pending review job is not eligible for acceptance.
    """

    def __init__(
        self,
        *,
        job_id: str,
        reason: str,
    ) -> None:
        self.job_id = job_id
        self.reason = reason

        super().__init__(
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    message=(
                        f"Diff review job {job_id!r} is not eligible "
                        f"for acceptance: {reason}"
                    ),
                ),
            ),
        )


class DiffSchemaContractError(
    DiffSchemaError,
):
    """
    Raised when the persisted tww_diff schema violates its contract.
    """

    def __init__(
        self,
        *,
        message: str,
        table_name: str | None = None,
        column_name: str | None = None,
    ) -> None:
        self.table_name = table_name
        self.column_name = column_name

        context = []

        if table_name is not None:
            context.append(f"table={table_name!r}")

        if column_name is not None:
            context.append(f"column={column_name!r}")

        context_message = f" ({', '.join(context)})" if context else ""

        super().__init__(
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    message=(f"{message}{context_message}"),
                ),
            ),
        )


class DiffJobPersistenceError(
    DiffSchemaError,
):
    """
    Raised when an accepted diff job cannot be persisted.
    """

    def __init__(
        self,
        *,
        job_id: str,
        phase: str,
        message: str,
    ) -> None:
        self.job_id = job_id
        self.phase = phase

        super().__init__(
            findings=(
                Finding(
                    severity=Severity.ERROR,
                    message=(
                        f"Persistence of diff review job {job_id!r} "
                        f"failed during phase {phase!r}: {message}"
                    ),
                ),
            ),
        )


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
