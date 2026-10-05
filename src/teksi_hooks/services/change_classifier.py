from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..evaluators.rights import (
    RightsEvaluationContext,
    RightsEvaluator,
)
from ..models.rights import (
    PermissionFinding,
)
from ..models.validation import (
    Change,
    ChangeClassification,
    ChangeClassificationMetadata,
    ChangeOperation,
    ClassifiedChange,
    ClassifiedChanges,
    Severity,
    ValidationFinding,
)

ChangeKey = tuple[
    str,
    str,
    ChangeOperation,
]


@dataclass(slots=True)
class ChangeClassifier:
    """
    Classify changes into review groups and attach findings.

    Classification rules:

    - INSERT + no blocking findings -> created_objects
    - UPDATE + no blocking findings -> altered_objects
    - DELETE + no blocking findings -> deleted_objects
    - rights denied -> unpermitted_changes
    - validation errors -> unpermitted_changes
    - unknown operation -> unpermitted_changes

    Permission failures are represented as PermissionFinding.

    Validation findings stay in validation_findings. Only blocking validation
    errors are stored there, because the database diff schema derives
    is_rejected from the presence of permission_findings or
    validation_findings.
    """

    rights_evaluator: RightsEvaluator

    def classify(
        self,
        changes: Sequence[Change,],
        context: RightsEvaluationContext,
        validation_findings_by_change_key: Mapping[
            ChangeKey,
            tuple[ValidationFinding, ...],
        ]
        | None = None,
        metadata: dict[
            str,
            str,
        ]
        | None = None,
    ) -> ClassifiedChanges:
        """
        Classify a sequence of changes.

        Parameters
        ----------
        changes:
            Changes to classify.

        context:
            Base rights evaluation context. Operation, old_values and
            new_values are replaced per change before rights evaluation.

        validation_findings_by_change_key:
            Optional validation findings keyed by
            (table_name, object_id, operation).

        metadata:
            Optional workflow-level metadata copied into the result.
        """

        validation_findings_by_change_key = validation_findings_by_change_key or {}

        result = ClassifiedChanges(
            metadata=metadata or {},
        )

        for change in changes:
            validation_findings = validation_findings_by_change_key.get(
                self.change_key(
                    change,
                ),
                (),
            )

            classified_change = self._classify_change(
                change=change,
                base_context=context,
                validation_findings=validation_findings,
            )

            result.add(
                classified_change,
            )

        return result

    def _classify_change(
        self,
        change: Change,
        base_context: RightsEvaluationContext,
        validation_findings: tuple[ValidationFinding, ...],
    ) -> ClassifiedChange:
        context = self._context_for_change(
            base_context=base_context,
            change=change,
        )

        blocking_validation_findings = self._blocking_validation_findings(
            validation_findings,
        )

        permitted = self._is_permitted(
            change=change,
            context=context,
        )

        permission_findings = self._permission_findings(
            change=change,
            context=context,
            permitted=permitted,
        )

        blocking_findings = (
            *permission_findings,
            *blocking_validation_findings,
        )

        if blocking_findings:
            return ClassifiedChange(
                change=change,
                metadata=ChangeClassificationMetadata(
                    classification=ChangeClassification.UNPERMITTED_CHANGE,
                    permitted=permitted,
                    severity=self._highest_severity(
                        blocking_findings,
                    ),
                    permission_findings=permission_findings,
                    validation_findings=blocking_validation_findings,
                ),
            )

        classification = self._classification_for_operation(
            change.operation,
        )

        if classification == ChangeClassification.UNPERMITTED_CHANGE:
            permission_finding = self._unsupported_operation_finding(
                change=change,
                context=context,
            )

            return ClassifiedChange(
                change=change,
                metadata=ChangeClassificationMetadata(
                    classification=ChangeClassification.UNPERMITTED_CHANGE,
                    permitted=False,
                    severity=permission_finding.severity,
                    permission_findings=(permission_finding,),
                    validation_findings=(),
                ),
            )

        return ClassifiedChange(
            change=change,
            metadata=ChangeClassificationMetadata(
                classification=classification,
                permitted=True,
                severity=None,
                permission_findings=(),
                validation_findings=(),
            ),
        )

    def _context_for_change(
        self,
        base_context: RightsEvaluationContext,
        change: Change,
    ) -> RightsEvaluationContext:
        """
        Create a rights evaluation context for one change.
        """

        return replace(
            base_context,
            operation=change.operation,
            old_values=change.old_values,
            new_values=change.new_values,
        )

    def _is_permitted(
        self,
        change: Change,
        context: RightsEvaluationContext,
    ) -> bool:
        if change.operation == ChangeOperation.INSERT:
            return self.rights_evaluator.can_create(
                change.table_name,
                context,
            )

        if change.operation == ChangeOperation.UPDATE:
            return self.rights_evaluator.can_update(
                change.table_name,
                context,
            )

        if change.operation == ChangeOperation.DELETE:
            return self.rights_evaluator.can_delete(
                change.table_name,
                context,
            )

        return False

    def _permission_findings(
        self,
        *,
        change: Change,
        context: RightsEvaluationContext,
        permitted: bool,
    ) -> tuple[PermissionFinding, ...]:
        if permitted:
            return ()

        return (
            PermissionFinding(
                code="permission_denied",
                severity=Severity.ERROR,
                message=("Change is not permitted by rights evaluation."),
                attribute_name=None,
                provider_oid=context.provider_oid,
                dataowner_oid=context.dataowner_oid,
                transitive_evaluation_enabled=(self._transitive_evaluation_enabled()),
                details={
                    "class_id": change.table_name,
                    "object_id": change.object_id,
                    "operation": change.operation.value,
                },
            ),
        )

    def _unsupported_operation_finding(
        self,
        *,
        change: Change,
        context: RightsEvaluationContext,
    ) -> PermissionFinding:
        return PermissionFinding(
            code="unsupported_change_operation",
            severity=Severity.ERROR,
            message=(f"Unsupported change operation: {change.operation!r}."),
            attribute_name=None,
            provider_oid=context.provider_oid,
            dataowner_oid=context.dataowner_oid,
            transitive_evaluation_enabled=(self._transitive_evaluation_enabled()),
            details={
                "class_id": change.table_name,
                "object_id": change.object_id,
                "operation": str(
                    change.operation,
                ),
            },
        )

    def _blocking_validation_findings(
        self,
        findings: Sequence[ValidationFinding,],
    ) -> tuple[ValidationFinding, ...]:
        """
        Return validation findings that should reject the import.

        The database diff schema derives is_rejected from the presence of
        validation_findings, so only ERROR findings are persisted here.
        """

        return tuple(
            finding for finding in findings if finding.severity == Severity.ERROR
        )

    def _classification_for_operation(
        self,
        operation: ChangeOperation,
    ) -> ChangeClassification:
        if operation == ChangeOperation.INSERT:
            return ChangeClassification.CREATED_OBJECT

        if operation == ChangeOperation.UPDATE:
            return ChangeClassification.ALTERED_OBJECT

        if operation == ChangeOperation.DELETE:
            return ChangeClassification.DELETED_OBJECT

        return ChangeClassification.UNPERMITTED_CHANGE

    def _highest_severity(
        self,
        findings: Sequence,
    ) -> Severity | None:
        """
        Return the highest finding severity.

        Ordering is:

            error > warning > info
        """

        if not findings:
            return None

        severities = tuple(finding.severity for finding in findings)

        for severity in (
            Severity.ERROR,
            Severity.WARNING,
            Severity.INFO,
        ):
            if severity in severities:
                return severity

        return severities[0]

    def _transitive_evaluation_enabled(
        self,
    ) -> bool | None:
        """
        Return whether recursive/transitive rights evaluation is enabled,
        if this information is available on the evaluator.
        """

        resolved_rights = getattr(
            self.rights_evaluator,
            "resolved_rights",
            None,
        )

        if resolved_rights is None:
            resolved_rights = getattr(
                self.rights_evaluator,
                "rights",
                None,
            )

        if resolved_rights is None:
            return None

        return getattr(
            resolved_rights,
            "allow_transitive_transitions",
            None,
        )

    def change_key(
        self,
        change: Change,
    ) -> ChangeKey:
        """
        Return a stable key for attaching validation findings to a change.

        This avoids using Change objects as dictionary keys, because Change is
        a workflow model and may be mutable.
        """

        return (
            change.table_name,
            change.object_id,
            change.operation,
        )
