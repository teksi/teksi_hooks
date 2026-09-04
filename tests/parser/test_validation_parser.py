from __future__ import annotations

from teksi_hooks.exceptions import (
    Severity,
)
from teksi_hooks.models.validation import (
    AttributeValidation,
    ChangeOperation,
    ObjectValidation,
    ValidationDefinition,
)


def test_validation_parser_parses_validation_definition(
    validation_definition: ValidationDefinition,
) -> None:
    assert validation_definition.mandatory_attributes == frozenset(
        {
            "obj_id",
            "identifier",
            "fk_provider",
            "fk_dataowner",
        }
    )

    assert validation_definition.attribute_validations == {
        "last_modification": (
            AttributeValidation(
                id="newer_than_existing",
                level=Severity.INFO,
                operations=(
                    ChangeOperation.INSERT,
                    ChangeOperation.UPDATE,
                    ChangeOperation.DELETE,
                ),
                context_value=None,
                parameters={},
            ),
        ),
        "fk_provider": (
            AttributeValidation(
                id="equals_context_value",
                level=Severity.ERROR,
                operations=(ChangeOperation.INSERT,),
                context_value="provider_oid",
                parameters={},
            ),
        ),
        "fk_dataowner": (
            AttributeValidation(
                id="equals_context_value",
                level=Severity.ERROR,
                operations=(ChangeOperation.INSERT,),
                context_value="dataowner_oid",
                parameters={},
            ),
        ),
    }

    assert validation_definition.object_validations == {
        "unique_identifier_combo": (
            ObjectValidation(
                id="is_unique",
                level=Severity.ERROR,
                operations=(
                    ChangeOperation.INSERT,
                    ChangeOperation.UPDATE,
                ),
                parameters={
                    "attributes": (
                        "identifier",
                        "fk_dataowner",
                    ),
                },
            ),
        ),
    }

    maintenance_event = validation_definition.classes["maintenance_event"]

    assert maintenance_event.class_id == "maintenance_event"
    assert maintenance_event.mandatory_attributes == frozenset()
    assert maintenance_event.attribute_validations == {}

    assert maintenance_event.object_validations == {
        "unique_identifier_combo": (
            ObjectValidation(
                id="is_unique",
                level=Severity.ERROR,
                operations=(
                    ChangeOperation.INSERT,
                    ChangeOperation.UPDATE,
                ),
                parameters={
                    "attributes": (
                        "identifier",
                        "fk_dataowner",
                        "time_point",
                    ),
                },
            ),
        ),
    }
