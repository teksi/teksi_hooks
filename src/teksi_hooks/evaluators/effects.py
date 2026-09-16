from __future__ import annotations


from dataclasses import dataclass, replace
from typing import Any
from collections import defaultdict

from ..models.effects import (
    Effect,
    EffectDocument,
    EffectEvaluationResult,
    EffectEvaluationStatus,
    EnforceExistsEffect,
    EnforceNotExistsEffect,
    UpdateAttributeEffect,
)
from ..models.validation import ValidationFinding
from ..models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)
from ..capabilities.effects import (
    CanonicalObjectLookupCapability,
    EffectEvaluationPolicy,
)

from ..exceptions import EffectValidationError, Severity

DOCUMENT_MAX_VERSION = 1


@dataclass(slots=True)
class EffectDocumentValidator:
    """
    Validates EffectDocument instances.

    The validator performs structural and semantic checks before effects are
    persisted or transformed into snapshots.
    """

    def validate(
        self,
        document: EffectDocument,
    ) -> tuple[ValidationFinding, ...]:
        findings: list[ValidationFinding] = []

        if document.version > DOCUMENT_MAX_VERSION:
            findings.append(
                ValidationFinding(
                    code="invalid_version",
                    severity=Severity.ERROR,
                    message=(
                        f"Unsupported effect document version: {document.version}"
                    ),
                )
            )

        for effect in document.effects:
            if not effect.identity.class_id:
                findings.append(
                    ValidationFinding(
                        code="missing_attribute",
                        severity=Severity.ERROR,
                        message=("Effect identity is missing class_id."),
                    )
                )

            if not effect.identity.attributes:
                findings.append(
                    ValidationFinding(
                        code="missing_attribute",
                        severity=Severity.ERROR,
                        message=("Effect identity is missing identity attributes."),
                    )
                )

            if isinstance(
                effect,
                UpdateAttributeEffect,
            ):
                if not effect.attribute_id:
                    findings.append(
                        ValidationFinding(
                            code="missing_attribute",
                            severity=Severity.ERROR,
                            message=("Update effect missing attribute_id."),
                        )
                    )

            elif isinstance(
                effect,
                (
                    EnforceExistsEffect,
                    EnforceNotExistsEffect,
                ),
            ):
                pass

            else:
                findings.append(
                    ValidationFinding(
                        code="unsupported_effect",
                        severity=Severity.ERROR,
                        message=(f"Unsupported effect type: {type(effect).__name__}"),
                    )
                )

        findings.extend(
            self._validate_conflicting_effects(
                document,
            )
        )
        return tuple(
            findings,
        )

    def validate_or_raise(
        self,
        document: EffectDocument,
    ) -> tuple[ValidationFinding, ...]:
        findings = self.validate(document)
        EffectValidationError.raise_if_errors(
            findings,
        )
        return findings

    def _identity_key(
        self,
        identity: CanonicalObjectIdentity,
    ) -> tuple:
        return (
            identity.class_id,
            tuple(
                sorted(
                    identity.attributes.items(),
                ),
            ),
        )

    def _validate_conflicting_effects(
        self,
        document: EffectDocument,
    ) -> tuple[
        ValidationFinding,
        ...,
    ]:
        """
        Validate that effects for the same identity do not contradict each other.

        The following combinations are invalid:

        - requiring one object both to exist and not exist;
        - updating an object while requiring it not to exist;
        - assigning different values to the same attribute of the same object.
        """

        findings: list[ValidationFinding,] = []

        effects_by_identity: dict[
            tuple,
            list[Effect,],
        ] = defaultdict(
            list,
        )

        for effect in document.effects:
            identity_key = self._identity_key(
                effect.identity,
            )

            effects_by_identity[identity_key].append(
                effect,
            )

        for (
            identity_key,
            effects,
        ) in effects_by_identity.items():
            has_exists = any(
                isinstance(
                    effect,
                    EnforceExistsEffect,
                )
                for effect in effects
            )

            has_not_exists = any(
                isinstance(
                    effect,
                    EnforceNotExistsEffect,
                )
                for effect in effects
            )

            update_effects = tuple(
                effect
                for effect in effects
                if isinstance(
                    effect,
                    UpdateAttributeEffect,
                )
            )

            if has_exists and has_not_exists:
                findings.append(
                    ValidationFinding(
                        code="contradicting_effects",
                        attribute_name=None,
                        severity=Severity.ERROR,
                        message=(
                            "Object cannot be required to exist and "
                            "not exist at the same time."
                        ),
                    )
                )

            if update_effects and has_not_exists:
                findings.append(
                    ValidationFinding(
                        code="contradicting_effects",
                        attribute_name=None,
                        severity=Severity.ERROR,
                        message=(
                            "Object cannot be updated and required "
                            "not to exist at the same time."
                        ),
                    )
                )

            updates_by_attribute: dict[
                str,
                list[UpdateAttributeEffect,],
            ] = defaultdict(
                list,
            )

            for effect in update_effects:
                updates_by_attribute[effect.attribute_id].append(
                    effect,
                )

            for (
                attribute_id,
                attribute_effects,
            ) in updates_by_attribute.items():
                values = [effect.value for effect in attribute_effects]

                if not self._all_values_equal(
                    values,
                ):
                    findings.append(
                        ValidationFinding(
                            code=("contradicting_attribute_updates"),
                            attribute_name=attribute_id,
                            severity=Severity.ERROR,
                            message=(
                                "Multiple update effects assign "
                                "different values to attribute "
                                f"{attribute_id!r} for the same "
                                "canonical object."
                            ),
                        )
                    )

        return tuple(
            findings,
        )

    def _all_values_equal(
        self,
        values: list,
    ) -> bool:
        """
        Return whether all effect values are equal.
        """

        if not values:
            return True

        first_value = values[0]

        return all(value == first_value for value in values[1:])


@dataclass(
    slots=True,
)
class EffectEvaluator:
    """
    Evaluate desired-state effects against current canonical state.

    The evaluator determines whether each effect is already satisfied. An
    injected policy classifies unsatisfied effects as remediable or blocked.

    The evaluator does not mutate canonical state.
    """

    object_lookup: CanonicalObjectLookupCapability

    policy: EffectEvaluationPolicy

    def evaluate(
        self,
        document: EffectDocument,
    ) -> tuple[
        EffectEvaluationResult,
        ...,
    ]:
        """
        Evaluate every effect in document order.

        Returns exactly one evaluation result per effect.
        """

        results: list[EffectEvaluationResult,] = []

        for effect_index, effect in enumerate(
            document.effects,
        ):
            result = self.evaluate_effect(
                effect=effect,
                effect_index=effect_index,
            )

            results.append(
                result,
            )

        return tuple(
            results,
        )

    def evaluate_effect(
        self,
        *,
        effect: Effect,
        effect_index: int,
    ) -> EffectEvaluationResult:
        """
        Evaluate one desired-state effect.
        """

        current_object = self.object_lookup.canonical_object(
            effect.identity,
        )

        if isinstance(
            effect,
            UpdateAttributeEffect,
        ):
            return self._evaluate_update_attribute(
                effect=effect,
                effect_index=effect_index,
                current_object=current_object,
            )

        if isinstance(
            effect,
            EnforceExistsEffect,
        ):
            return self._evaluate_enforce_exists(
                effect=effect,
                effect_index=effect_index,
                current_object=current_object,
            )

        if isinstance(
            effect,
            EnforceNotExistsEffect,
        ):
            return self._evaluate_enforce_not_exists(
                effect=effect,
                effect_index=effect_index,
                current_object=current_object,
            )

        return EffectEvaluationResult(
            effect_index=effect_index,
            status=EffectEvaluationStatus.BLOCKED,
            findings=(
                ValidationFinding(
                    code="unsupported_effect",
                    severity=Severity.ERROR,
                    message=(
                        "Effect evaluation does not support effect "
                        f"type {type(effect).__name__!r}."
                    ),
                ),
            ),
            metadata={
                "effect_type": type(
                    effect,
                ).__name__,
            },
        )

    def _evaluate_update_attribute(
        self,
        *,
        effect: UpdateAttributeEffect,
        effect_index: int,
        current_object: CanonicalObject | None,
    ) -> EffectEvaluationResult:
        """
        Evaluate one desired attribute value.
        """

        if current_object is None:
            return self._unsatisfied_result(
                effect=effect,
                effect_index=effect_index,
                current_object=None,
            )

        actual_value = current_object.values.get(
            effect.attribute_id,
        )

        if self._values_equal(
            actual_value,
            effect.value,
        ):
            return EffectEvaluationResult(
                effect_index=effect_index,
                status=EffectEvaluationStatus.SATISFIED,
                metadata={
                    "attribute_id": effect.attribute_id,
                    "actual_value": actual_value,
                    "expected_value": effect.value,
                },
            )

        return self._unsatisfied_result(
            effect=effect,
            effect_index=effect_index,
            current_object=current_object,
            metadata={
                "attribute_id": effect.attribute_id,
                "actual_value": actual_value,
                "expected_value": effect.value,
            },
        )

    def _evaluate_enforce_exists(
        self,
        *,
        effect: EnforceExistsEffect,
        effect_index: int,
        current_object: CanonicalObject | None,
    ) -> EffectEvaluationResult:
        """
        Evaluate whether the requested canonical object exists.
        """

        if current_object is not None:
            return EffectEvaluationResult(
                effect_index=effect_index,
                status=EffectEvaluationStatus.SATISFIED,
                metadata={
                    "object_exists": True,
                },
            )

        return self._unsatisfied_result(
            effect=effect,
            effect_index=effect_index,
            current_object=None,
            metadata={
                "object_exists": False,
            },
        )

    def _evaluate_enforce_not_exists(
        self,
        *,
        effect: EnforceNotExistsEffect,
        effect_index: int,
        current_object: CanonicalObject | None,
    ) -> EffectEvaluationResult:
        """
        Evaluate whether the requested canonical object is absent.
        """

        if current_object is None:
            return EffectEvaluationResult(
                effect_index=effect_index,
                status=EffectEvaluationStatus.SATISFIED,
                metadata={
                    "object_exists": False,
                },
            )

        return self._unsatisfied_result(
            effect=effect,
            effect_index=effect_index,
            current_object=current_object,
            metadata={
                "object_exists": True,
            },
        )

    def _unsatisfied_result(
        self,
        *,
        effect: Effect,
        effect_index: int,
        current_object: CanonicalObject | None,
        metadata: dict[
            str,
            Any,
        ]
        | None = None,
    ) -> EffectEvaluationResult:
        """
        Ask the model-specific policy to classify an unsatisfied effect.
        """

        result = self.policy.unsatisfied_status(
            effect=effect,
            current_object=current_object,
        )

        merged_metadata = dict(
            result.metadata,
        )

        merged_metadata.update(
            metadata or {},
        )

        return replace(
            result,
            effect_index=effect_index,
            metadata=merged_metadata,
        )

    def _values_equal(
        self,
        actual_value: Any,
        expected_value: Any,
    ) -> bool:
        """
        Compare current and desired canonical values.

        Model-specific normalization must occur before effect evaluation.
        """

        return actual_value == expected_value


@dataclass(
    slots=True,
    frozen=True,
)
class BlockingEffectEvaluationPolicy:
    """
    Conservatively block every unsatisfied desired-state effect.

    This policy is suitable when no model-specific persistence guarantees are
    available.
    """

    def unsatisfied_status(
        self,
        *,
        effect: Effect,
        current_object: CanonicalObject | None,
    ) -> EffectEvaluationResult:
        """
        Return a blocked result for one unsatisfied effect.
        """

        return EffectEvaluationResult(
            effect_index=-1,
            status=EffectEvaluationStatus.BLOCKED,
            findings=(
                ValidationFinding(
                    code="effect_not_satisfied",
                    severity=Severity.ERROR,
                    message=(
                        "The desired-state effect is not satisfied and "
                        "no persistence policy permits reconciliation."
                    ),
                ),
            ),
            metadata={
                "effect_type": type(
                    effect,
                ).__name__,
                "target_class_id": (effect.identity.class_id),
                "target_exists": (current_object is not None),
            },
        )
