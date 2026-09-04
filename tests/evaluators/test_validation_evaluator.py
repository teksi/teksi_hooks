from unittest.mock import Mock
import pytest

from teksi_hooks.capabilities.rights import RightsCapability
from teksi_hooks.evaluators.validation import (
    ValidationEvaluator,
)
from teksi_hooks.resolver.rights_resolver import RightsResolver
from teksi_hooks.models.validation import (
    AttributeValidation,
    Change,
    ChangeOperation,
    ValidationContext,
    ValidationFinding,
)

from teksi_hooks.capabilities.validation import (
    ValidationRegistry,
)
from teksi_hooks.models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)
from teksi_hooks.models.effects import (
    UpdateAttributeEffect,
)
from teksi_hooks.services.change_builder import (
    ChangeBuilder,
)

from teksi_hooks.exceptions import Severity


def test_validation_evaluator_uses_registry(
    resolved_rights,
) -> None:
    registry = Mock(
        spec=ValidationRegistry,
    )

    validator = Mock(
        return_value=(
            ValidationFinding(
                code="test",
                severity=Severity.WARNING,
                message="test",
                attribute_name="status_survey_year",
            ),
        )
    )

    registry.validation.return_value = validator

    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_attribute(
        class_id="wastewater_structure",
        attribute_name="status_survey_year",
        old_value=2024,
        new_value=2020,
        operation=ChangeOperation.UPDATE,
    )

    registry.validation.assert_called_once_with(
        "cannot_decrease",
    )

    validator.assert_called_once()

    validation_context = validator.call_args.kwargs["context"]

    assert validation_context.class_id == ("wastewater_structure")

    assert validation_context.attribute_name == ("status_survey_year")

    assert (
        len(
            findings,
        )
        == 1
    )


def test_validation_evaluator_accepts_allowed_transition(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_transition(
        class_id="wastewater_structure",
        attribute_name="status",
        old_value="other.planned",
        new_value="operational",
    )

    assert findings == ()


def test_validation_evaluator_accepts_bilateral_transition(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_transition(
        class_id="wastewater_structure",
        attribute_name="status",
        old_value="other.planned",
        new_value="other.calculation_alternative",
    )

    assert findings == ()


def test_validation_evaluator_accepts_transitive_transition(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_transition(
        class_id="wastewater_structure",
        attribute_name="status",
        old_value="other.calculation_alternative",
        new_value="operational",
    )

    assert findings == ()


def test_validation_evaluator_rejects_invalid_transition(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_transition(
        class_id="wastewater_structure",
        attribute_name="status",
        old_value="operational",
        new_value="invalid_state",
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].code == "invalid_transition"
    assert findings[0].attribute_name == "status"


def test_validation_evaluator_ignores_attribute_without_transition_rules(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_transition(
        class_id="maintenance",
        attribute_name="remark",
        old_value="foo",
        new_value="bar",
    )

    assert findings == ()


def test_validation_evaluator_uses_transitive_transition_flag(
    rights_definition_non_transitive,
    validation_definition,
    registry,
) -> None:
    resolved_rights = RightsResolver().resolve(
        definition=rights_definition_non_transitive,
        validation_definition=validation_definition,
    )

    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_transition(
        class_id="wastewater_structure",
        attribute_name="status",
        old_value="other.calculation_alternative",
        new_value="operational",
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].code == "invalid_transition"
    assert findings[0].attribute_name == "status"


def test_validation_finding_is_created() -> None:
    finding = ValidationFinding(
        code="newer_than_existing",
        severity=Severity.WARNING,
        message="Value is older than existing value.",
        attribute_name="status",
    )

    assert finding.code == "newer_than_existing"


def test_validation_evaluator_accepts_newer_than_existing(
    registry,
) -> None:
    validation = AttributeValidation(
        id="newer_than_existing",
        level=Severity.WARNING,
    )

    findings = registry.validation(
        "newer_than_existing",
    )(
        validation=validation,
        context=ValidationContext(
            class_id="wastewater_structure",
            attribute_name="last_modification",
            old_value="2024-01-01T00:00:00",
            new_value="2025-01-01T00:00:00",
        ),
    )

    assert findings == ()


def test_validation_evaluator_rejects_older_than_existing(
    registry,
) -> None:
    validation = AttributeValidation(
        id="newer_than_existing",
        level=Severity.WARNING,
    )

    findings = registry.validation(
        "newer_than_existing",
    )(
        validation=validation,
        context=ValidationContext(
            class_id="wastewater_structure",
            attribute_name="last_modification",
            old_value="2025-01-01T00:00:00",
            new_value="2024-01-01T00:00:00",
        ),
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].code == "newer_than_existing"


def test_validation_evaluator_accepts_non_decreasing_value(
    registry,
) -> None:
    validation = AttributeValidation(
        id="cannot_decrease",
        level=Severity.WARNING,
    )

    findings = registry.validation(
        "cannot_decrease",
    )(
        validation=validation,
        context=ValidationContext(
            class_id="wastewater_structure",
            attribute_name="inspection_year",
            old_value=2018,
            new_value=2024,
        ),
    )

    assert findings == ()


def test_validation_evaluator_rejects_decreasing_value(
    registry,
) -> None:
    validation = AttributeValidation(
        id="cannot_decrease",
        level=Severity.WARNING,
    )

    findings = registry.validation(
        "cannot_decrease",
    )(
        validation=validation,
        context=ValidationContext(
            class_id="wastewater_structure",
            attribute_name="inspection_year",
            old_value=2024,
            new_value=2018,
        ),
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].code == "cannot_decrease"


def test_validation_registry_rejects_unknown_validation(
    registry,
) -> None:
    with pytest.raises(
        NotImplementedError,
    ):
        registry.validation(
            "does_not_exist",
        )


def test_validation_evaluator_executes_cannot_decrease(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    findings = evaluator.validate_attribute(
        class_id="wastewater_structure",
        attribute_name="status_survey_year",
        old_value=2024,
        new_value=2020,
        operation=ChangeOperation.UPDATE,
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].code == "cannot_decrease"
    assert findings[0].attribute_name == "status_survey_year"
    assert findings[0].severity == Severity.WARNING


def test_validation_evaluator_validates_change(
    resolved_rights,
    registry,
) -> None:
    current = CanonicalObject(
        identity=CanonicalObjectIdentity(
            class_id="wastewater_structure",
            attributes={
                "obj_id": "ch987654WS123456",
            },
        ),
        values={
            "status_survey_year": 2024,
        },
    )

    change = ChangeBuilder().build(
        current_object=current,
        effects=(
            UpdateAttributeEffect(
                identity=current.identity,
                attribute_id="status_survey_year",
                value=2020,
            ),
        ),
    )

    findings = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    ).validate_change(
        class_id="wastewater_structure",
        change=change,
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    finding = findings[0]

    assert finding.code == "cannot_decrease"
    assert finding.attribute_name == "status_survey_year"


def test_validation_evaluator_accepts_valid_change(
    resolved_rights,
    registry,
) -> None:
    current = CanonicalObject(
        identity=CanonicalObjectIdentity(
            class_id="wastewater_structure",
            attributes={
                "obj_id": "ch987654WS123456",
            },
        ),
        values={
            "status_survey_year": 2020,
        },
    )

    change = ChangeBuilder().build(
        current_object=current,
        effects=(
            UpdateAttributeEffect(
                identity=current.identity,
                attribute_id="status_survey_year",
                value=2024,
            ),
        ),
    )

    findings = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    ).validate_change(
        class_id="wastewater_structure",
        change=change,
    )

    assert findings == ()


def test_validation_evaluator_rejects_insert_context_value_mismatch(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    change = Change(
        table_name="wastewater_structure",
        object_id="ch987654WS123456",
        operation=ChangeOperation.INSERT,
        old_values={},
        new_values={
            "fk_provider": "ch000000wrong01",
            "fk_dataowner": "ch000000awgde001",
        },
    )

    assert {attribute.attribute_name for attribute in change.changed_attributes} == {
        "fk_provider",
        "fk_dataowner",
    }

    validations = RightsCapability(
        rights=resolved_rights,
    ).try_validations(
        "wastewater_structure",
        "fk_provider",
    )

    assert validations

    findings = evaluator.validate_change(
        class_id="wastewater_structure",
        change=change,
        context_values={
            "provider_oid": "ch000000geping01",
            "dataowner_oid": "ch000000awgde001",
        },
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].code == "equals_context_value"
    assert findings[0].severity == Severity.ERROR
    assert findings[0].attribute_name == "fk_provider"


def test_validation_evaluator_accepts_matching_insert_context_values(
    resolved_rights,
    registry,
) -> None:
    evaluator = ValidationEvaluator(
        rights=RightsCapability(
            rights=resolved_rights,
        ),
        registry=registry,
    )

    change = Change(
        table_name="wastewater_structure",
        object_id="ch987654WS123456",
        operation=ChangeOperation.INSERT,
        old_values={},
        new_values={
            "fk_provider": "ch000000geping01",
            "fk_dataowner": "ch000000awgde001",
        },
    )

    findings = evaluator.validate_change(
        class_id="wastewater_structure",
        change=change,
        context_values={
            "provider_oid": "ch000000geping01",
            "dataowner_oid": "ch000000awgde001",
        },
    )

    assert findings == ()
