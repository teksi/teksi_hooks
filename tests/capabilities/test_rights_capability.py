import pytest

from teksi_hooks.capabilities.rights import (
    RightsCapability,
)
from teksi_hooks.resolver.rights_resolver import RightsResolver


def test_rights_capability_returns_class_definition(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    cls = capability.class_definition(
        "wastewater_structure",
    )

    assert cls.id == "wastewater_structure"


def test_rights_capability_returns_attribute_definition(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    attribute = capability.attribute_definition(
        "wastewater_structure",
        "status",
    )

    assert attribute.update_privileges == frozenset(
        {
            "DBW_GEP",
            "DBW_WI",
        }
    )


def test_rights_capability_returns_update_privileges(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    assert capability.update_privileges(
        "wastewater_structure",
        "status",
    ) == frozenset(
        {
            "DBW_GEP",
            "DBW_WI",
        }
    )


def test_rights_capability_returns_crud_rules(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    assert (
        len(
            capability.create_rules(
                "wastewater_structure",
            )
        )
        == 2
    )

    assert (
        len(
            capability.update_rules(
                "wastewater_structure",
            )
        )
        == 2
    )


def test_rights_capability_try_class_definition_returns_none(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    assert (
        capability.try_class_definition(
            "does_not_exist",
        )
        is None
    )


def test_rights_capability_try_attribute_definition_returns_none(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    assert (
        capability.try_attribute_definition(
            "wastewater_structure",
            "does_not_exist",
        )
        is None
    )


def test_rights_capability_returns_transition_rules(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    rules = capability.transition_rules(
        "wastewater_structure",
        "status",
    )

    assert rules

    assert any(
        rule.from_value == "other.planned" and rule.to_value == "operational"
        for rule in rules
    )


def test_rights_capability_rejects_unknown_transition_attribute(
    resolved_rights,
) -> None:
    capability = RightsCapability(
        rights=resolved_rights,
    )

    with pytest.raises(
        KeyError,
    ):
        capability.transition_rules(
            "wastewater_structure",
            "does_not_exist",
        )


def test_rights_capability_try_transition_rules_returns_none(
    rights_definition, resolved_rights
) -> None:
    RightsResolver().resolve(
        rights_definition,
    )
    capability = RightsCapability(
        rights=resolved_rights,
    )

    assert (
        capability.try_transition_rules(
            "wastewater_structure",
            "does_not_exist",
        )
        is None
    )
