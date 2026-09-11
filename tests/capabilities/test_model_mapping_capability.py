import pytest

from teksi_hooks.capabilities.mapping import (
    ModelMappingCapability,
)


@pytest.fixture
def capability(
    agxx_mapping,
) -> ModelMappingCapability:
    return ModelMappingCapability(
        mapping=agxx_mapping,
    )


def test_model_mapping_capability_returns_function_backed_class(
    capability: ModelMappingCapability,
) -> None:
    cls = capability.class_definition(
        "GepKnoten",
    )

    assert cls.function is not None
    assert cls.function.schema == "tww_app"
    assert cls.function.name == "fct_agxx_gepknoten_mapping_jsonb"
    assert cls.function.parameters == {
        "row": "$row",
    }

    assert cls.identities == {}
    assert cls.attributes == {}
    assert cls.relations == {}


def test_model_mapping_capability_returns_attribute_backed_class(
    capability: ModelMappingCapability,
) -> None:
    cls = capability.class_definition(
        "VersickerungsbereichAG",
    )

    assert cls.function is None
    assert "q_check" in cls.attributes
    assert "versickerungsmoeglichkeitag" in cls.attributes


def test_model_mapping_capability_returns_attribute_definition(
    capability: ModelMappingCapability,
) -> None:
    attribute = capability.attribute_definition(
        "VersickerungsbereichAG",
        "q_check",
    )

    assert attribute.canonical_class_id == "agxx_infiltration_zone"
    assert attribute.canonical_attr_id == "ag96_q_check"
    assert attribute.value_list is None
    assert attribute.values == {}


def test_model_mapping_capability_returns_value_list_attribute_definition(
    capability: ModelMappingCapability,
) -> None:
    attribute = capability.attribute_definition(
        "VersickerungsbereichAG",
        "versickerungsmoeglichkeitag",
    )

    assert attribute.canonical_class_id == "infiltration_zone"
    assert attribute.canonical_attr_id == "infiltration_capacity"

    assert attribute.value_list is not None
    assert attribute.value_list.relation == (
        "tww_vl.infiltration_zone_infiltration_capacity"
    )
    assert attribute.value_list.mapping_attribute == "value_de"


def test_model_mapping_capability_returns_class_identity(
    capability: ModelMappingCapability,
) -> None:
    cls = capability.class_definition(
        "VersickerungsbereichAG",
    )

    identity = cls.identities["agxx_infiltration_zone"]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "fk_infiltration_zone"


def test_model_mapping_capability_returns_defaulted_class_identity(
    capability: ModelMappingCapability,
) -> None:
    cls = capability.class_definition(
        "VersickerungsbereichAG",
    )

    identity = cls.identities["infiltration_zone"]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "obj_id"


def test_model_mapping_capability_returns_multiple_target_identities(
    capability: ModelMappingCapability,
) -> None:
    cls = capability.class_definition(
        "BautenAusserhalbBaugebiet",
    )

    assert set(
        cls.identities,
    ) == {
        "agxx_building_group",
        "building_group",
    }

    extension_identity = cls.identities["agxx_building_group"]

    assert extension_identity.source_attribute == "obj_id"
    assert extension_identity.canonical_attribute == "fk_building_group"

    base_identity = cls.identities["building_group"]

    assert base_identity.source_attribute == "obj_id"
    assert base_identity.canonical_attribute == "obj_id"


def test_model_mapping_capability_returns_sbw_identity(
    capability: ModelMappingCapability,
) -> None:
    cls = capability.class_definition(
        "SBWEinzugsgebiet",
    )

    identity = cls.identities["agxx_catchment_area_totals"]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "fk_catchment_area_totals"


def test_model_mapping_capability_exposes_mapping_defaults(
    capability: ModelMappingCapability,
) -> None:
    defaults = capability.mapping.defaults

    assert defaults.identity.source_attribute == "obj_id"
    assert defaults.identity.canonical_attribute == "obj_id"

    assert "agxx_last_modification" in defaults.identities
    assert "letzte_aenderung_wi" in defaults.attributes
    assert "letzte_aenderung_gep" in defaults.attributes


def test_model_mapping_capability_exposes_default_last_modification_identity(
    capability: ModelMappingCapability,
) -> None:
    identity = capability.mapping.defaults.identities["agxx_last_modification"]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "fk_element"


def test_model_mapping_capability_exposes_default_attribute_mapping(
    capability: ModelMappingCapability,
) -> None:
    attribute = capability.mapping.defaults.attributes["letzte_aenderung_wi"]

    assert attribute.canonical_class_id == "agxx_last_modification"
    assert attribute.canonical_attr_id == "ag64_last_modification"


def test_model_mapping_capability_reports_non_ssot_mapping(
    capability: ModelMappingCapability,
) -> None:
    assert capability.mapping.is_ssot is False


def test_model_mapping_capability_try_class_definition_returns_none(
    capability: ModelMappingCapability,
) -> None:
    assert (
        capability.try_class_definition(
            "DoesNotExist",
        )
        is None
    )


def test_model_mapping_capability_try_attribute_definition_returns_none(
    capability: ModelMappingCapability,
) -> None:
    assert (
        capability.try_attribute_definition(
            "VersickerungsbereichAG",
            "does_not_exist",
        )
        is None
    )


def test_model_mapping_capability_class_definition_rejects_unknown_class(
    capability: ModelMappingCapability,
) -> None:
    with pytest.raises(
        KeyError,
        match="Unknown class",
    ):
        capability.class_definition(
            "DoesNotExist",
        )


def test_model_mapping_capability_attribute_definition_rejects_unknown_class(
    capability: ModelMappingCapability,
) -> None:
    with pytest.raises(
        KeyError,
        match="Unknown class",
    ):
        capability.attribute_definition(
            "DoesNotExist",
            "q_check",
        )


def test_model_mapping_capability_attribute_definition_rejects_unknown_attribute(
    capability: ModelMappingCapability,
) -> None:
    with pytest.raises(
        KeyError,
        match="Unknown attribute",
    ):
        capability.attribute_definition(
            "VersickerungsbereichAG",
            "does_not_exist",
        )
