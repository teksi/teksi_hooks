from pathlib import Path

import pytest

from teksi_hooks.parser.model_mapping_parser import (
    ModelMappingParser,
)


DATA_DIR = Path(__file__).parent / "data"
MAPPING_PATH = DATA_DIR / "explicit_mapping.yaml"


def test_mapping_parser_imports_all_models(
    mappings,
) -> None:
    assert set(
        mappings,
    ) == {
        "agxx",
        "sia405_abwasser",
        "dss",
        "vsa_kek",
    }


def test_mapping_parser_requires_model_id_for_multi_model_file(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="model_id is required",
    ):
        parser.parse_file(
            MAPPING_PATH,
        )


def test_mapping_parser_rejects_unknown_model_id(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        KeyError,
        match="Unknown model mapping",
    ):
        parser.parse_file(
            MAPPING_PATH,
            model_id="does_not_exist",
        )


def test_agxx_mapping_parser_imports_classes(
    agxx_mapping,
) -> None:
    assert {
        "GepKnoten",
        "GepHaltung",
        "GepMassnahme",
        "Einzugsgebiet",
        "Ueberlauf_Foerderaggregat",
        "BautenAusserhalbBaugebiet",
        "SBWEinzugsgebiet",
        "VersickerungsbereichAG",
    } <= set(
        agxx_mapping.classes,
    )


def test_agxx_mapping_parser_imports_model_identity_defaults(
    agxx_mapping,
) -> None:
    identity = agxx_mapping.defaults.identity

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "obj_id"


def test_agxx_mapping_parser_imports_default_extension_identity(
    agxx_mapping,
) -> None:
    identity = agxx_mapping.defaults.identities["agxx_last_modification"]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "fk_element"


def test_agxx_mapping_parser_imports_default_attributes(
    agxx_mapping,
) -> None:
    assert set(
        agxx_mapping.defaults.attributes,
    ) == {
        "letzte_aenderung_wi",
        "letzte_aenderung_gep",
    }


def test_agxx_mapping_parser_imports_default_wi_last_modification(
    agxx_mapping,
) -> None:
    attribute = agxx_mapping.defaults.attributes["letzte_aenderung_wi"]

    assert attribute.canonical_class_id == "agxx_last_modification"
    assert attribute.canonical_attr_id == "ag64_last_modification"
    assert attribute.value_list is None
    assert attribute.values == {}


def test_agxx_mapping_parser_imports_default_gep_last_modification(
    agxx_mapping,
) -> None:
    attribute = agxx_mapping.defaults.attributes["letzte_aenderung_gep"]

    assert attribute.canonical_class_id == "agxx_last_modification"
    assert attribute.canonical_attr_id == "ag96_last_modification"
    assert attribute.value_list is None
    assert attribute.values == {}


def test_agxx_mapping_parser_imports_gepknoten_function(
    agxx_mapping,
) -> None:
    cls = agxx_mapping.classes["GepKnoten"]

    assert cls.function is not None
    assert cls.function.schema == "tww_app"
    assert cls.function.name == "fct_agxx_gepknoten_mapping_jsonb"
    assert cls.function.parameters == {
        "row": "$row",
    }

    assert cls.identities == {}
    assert cls.attributes == {}
    assert cls.relations == {}


def test_agxx_mapping_parser_imports_gephaltung_function(
    agxx_mapping,
) -> None:
    cls = agxx_mapping.classes["GepHaltung"]

    assert cls.function is not None
    assert cls.function.schema == "tww_app"
    assert cls.function.name == "fct_agxx_gephaltung_mapping_jsonb"
    assert cls.function.parameters == {
        "row": "$row",
    }

    assert cls.identities == {}
    assert cls.attributes == {}
    assert cls.relations == {}


def test_agxx_mapping_parser_imports_ueberlauf_function(
    agxx_mapping,
) -> None:
    cls = agxx_mapping.classes["Ueberlauf_Foerderaggregat"]

    assert cls.function is not None
    assert cls.function.schema == "tww_app"
    assert cls.function.name == ("fct_agxx_ueberlauf_foerderaggregat_mapping_jsonb")
    assert cls.function.parameters == {
        "row": "$row",
    }

    assert cls.identities == {}
    assert cls.attributes == {}
    assert cls.relations == {}


def test_agxx_mapping_parser_imports_attribute_backed_class(
    agxx_mapping,
) -> None:
    cls = agxx_mapping.classes["VersickerungsbereichAG"]

    assert cls.function is None
    assert "q_check" in cls.attributes
    assert "versickerungsmoeglichkeitag" in cls.attributes


def test_agxx_mapping_parser_imports_empty_identity_with_defaults(
    agxx_mapping,
) -> None:
    identity = agxx_mapping.classes["GepMassnahme"].identities["measure"]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "obj_id"


def test_agxx_mapping_parser_imports_extension_identity_override(
    agxx_mapping,
) -> None:
    identity = agxx_mapping.classes["VersickerungsbereichAG"].identities[
        "agxx_infiltration_zone"
    ]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "fk_infiltration_zone"


def test_agxx_mapping_parser_imports_base_identity(
    agxx_mapping,
) -> None:
    identity = agxx_mapping.classes["VersickerungsbereichAG"].identities[
        "infiltration_zone"
    ]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "obj_id"


def test_agxx_mapping_parser_imports_building_group_identities(
    agxx_mapping,
) -> None:
    identities = agxx_mapping.classes["BautenAusserhalbBaugebiet"].identities

    assert identities["building_group"].source_attribute == "obj_id"
    assert identities["building_group"].canonical_attribute == "obj_id"

    assert identities["agxx_building_group"].source_attribute == "obj_id"
    assert identities["agxx_building_group"].canonical_attribute == "fk_building_group"


def test_agxx_mapping_parser_imports_catchment_totals_identity(
    agxx_mapping,
) -> None:
    identity = agxx_mapping.classes["SBWEinzugsgebiet"].identities[
        "agxx_catchment_area_totals"
    ]

    assert identity.source_attribute == "obj_id"
    assert identity.canonical_attribute == "fk_catchment_area_totals"


def test_agxx_mapping_parser_imports_agxx_extension_attribute_mapping(
    agxx_mapping,
) -> None:
    attribute = agxx_mapping.classes["VersickerungsbereichAG"].attributes["q_check"]

    assert attribute.canonical_class_id == "agxx_infiltration_zone"
    assert attribute.canonical_attr_id == "ag96_q_check"
    assert attribute.value_list is None
    assert attribute.values == {}


def test_agxx_mapping_parser_imports_base_tww_attribute_mapping(
    agxx_mapping,
) -> None:
    attribute = agxx_mapping.classes["VersickerungsbereichAG"].attributes[
        "versickerungsmoeglichkeitag"
    ]

    assert attribute.canonical_class_id == "infiltration_zone"
    assert attribute.canonical_attr_id == "infiltration_capacity"
    assert attribute.value_list is not None
    assert attribute.values == {}


def test_agxx_mapping_parser_imports_value_list_mapping(
    agxx_mapping,
) -> None:
    value_list = agxx_mapping.classes["GepMassnahme"].attributes["kategorie"].value_list

    assert value_list is not None
    assert value_list.relation == ("tww_vl.measure_category_import_rel_agxx")
    assert value_list.mapping_attribute == "value_de"


def test_agxx_mapping_parser_imports_current_drainage_value_list(
    agxx_mapping,
) -> None:
    value_list = (
        agxx_mapping.classes["Einzugsgebiet"]
        .attributes["entwaesserungssystemag_ist"]
        .value_list
    )

    assert value_list is not None
    assert value_list.relation == (
        "tww_vl.catchment_area_drainage_system_current_import_rel_agxx"
    )
    assert value_list.mapping_attribute == "value_de"


def test_agxx_mapping_parser_imports_planned_drainage_value_list(
    agxx_mapping,
) -> None:
    value_list = (
        agxx_mapping.classes["Einzugsgebiet"]
        .attributes["entwaesserungssystemag_geplant"]
        .value_list
    )

    assert value_list is not None
    assert value_list.relation == (
        "tww_vl.catchment_area_drainage_system_planned_import_rel_agxx"
    )
    assert value_list.mapping_attribute == "value_de"


def test_agxx_mapping_parser_imports_sbw_targets(
    agxx_mapping,
) -> None:
    cls = agxx_mapping.classes["SBWEinzugsgebiet"]

    expected_attributes = {
        "fremdwasseranfall_geplant": ("ag96_sewer_infiltration_water_dim"),
        "schmutzabwasseranfall_geplant": ("ag96_waste_water_production_dim"),
        "perimeter_ist": ("ag96_perimeter_geometry"),
    }

    for (
        source_attribute,
        canonical_attribute,
    ) in expected_attributes.items():
        mapping = cls.attributes[source_attribute]

        assert mapping.canonical_class_id == "agxx_catchment_area_totals"
        assert mapping.canonical_attr_id == canonical_attribute


def test_sia405_mapping_parser_imports_default_relations(
    sia405_mapping,
) -> None:
    assert set(
        sia405_mapping.defaults.relations,
    ) == {
        "fk_provider",
        "fk_dataowner",
        "fk_owner",
        "fk_operator",
    }


def test_sia405_mapping_parser_imports_provider_relation(
    sia405_mapping,
) -> None:
    relation = sia405_mapping.defaults.relations["fk_provider"]

    assert "fk_provider" in (sia405_mapping.defaults.relations)
    assert relation.referenced_class_id == "organisation"
    assert relation.referenced_attribute_id == "obj_id"
    assert relation.localisations == {
        "de": "DatenbewirtschafterRef",
    }


def test_sia405_mapping_parser_imports_owner_relation(
    sia405_mapping,
) -> None:
    relation = sia405_mapping.defaults.relations["fk_owner"]

    assert "fk_owner" in (sia405_mapping.defaults.relations)
    assert relation.referenced_class_id == "organisation"
    assert relation.referenced_attribute_id == "obj_id"
    assert relation.localisations == {
        "de": "EigentuemerRef",
    }


def test_sia405_mapping_parser_imports_reach_relations(
    sia405_mapping,
) -> None:
    cls = sia405_mapping.classes["reach"]

    assert set(
        cls.relations,
    ) == {
        "fk_reach_point_from",
        "fk_reach_point_to",
    }


def test_sia405_mapping_parser_imports_reach_point_from_relation(
    sia405_mapping,
) -> None:
    relation = sia405_mapping.classes["reach"].relations["fk_reach_point_from"]

    assert relation.referenced_class_id == "reach_point"
    assert relation.referenced_attribute_id == "obj_id"
    assert relation.localisations == {
        "de": "HaltungspunktVonRef",
    }


def test_sia405_mapping_parser_imports_reach_point_to_relation(
    sia405_mapping,
) -> None:
    relation = sia405_mapping.classes["reach"].relations["fk_reach_point_to"]

    assert relation.referenced_class_id == "reach_point"
    assert relation.referenced_attribute_id == "obj_id"
    assert relation.localisations == {
        "de": "HaltungspunktNachRef",
    }


@pytest.mark.parametrize(
    (
        "model_id",
        "parent_id",
    ),
    (
        (
            "dss",
            "sia405_abwasser",
        ),
        (
            "vsa_kek",
            "sia405_abwasser",
        ),
    ),
)
def test_mapping_parser_imports_model_inheritance(
    mappings,
    model_id: str,
    parent_id: str,
) -> None:
    assert mappings[model_id].defaults.inherit_from == parent_id


def test_mapping_parser_rejects_obsolete_targets_syntax(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="obsolete `targets`",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "test": {
                        "classes": {
                            "SourceClass": {
                                "identities": {
                                    "target_class": {},
                                },
                                "attributes": {
                                    "source_attribute": {
                                        "targets": [
                                            {
                                                "class": "target_class",
                                                "attribute": "value",
                                            }
                                        ]
                                    }
                                },
                            }
                        }
                    }
                }
            }
        )


def test_mapping_parser_rejects_function_and_attributes(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="row-level function",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "test": {
                        "classes": {
                            "SourceClass": {
                                "function": {
                                    "schema": "tww_app",
                                    "name": "mapping_function",
                                },
                                "attributes": {
                                    "source_attribute": {
                                        "target": {
                                            "class": "target_class",
                                            "attribute": "value",
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        )


def test_mapping_parser_rejects_mapping_attribute_without_value_list(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="requires .*value_list",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "test": {
                        "classes": {
                            "SourceClass": {
                                "identities": {
                                    "target_class": {},
                                },
                                "attributes": {
                                    "source_attribute": {
                                        "target": {
                                            "class": "target_class",
                                            "attribute": "value",
                                            "mapping_attribute": "value_de",
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        )


def test_mapping_parser_rejects_value_list_without_mapping_attribute(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        TypeError,
        match="mapping_attribute must be a string",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "test": {
                        "classes": {
                            "SourceClass": {
                                "identities": {
                                    "target_class": {},
                                },
                                "attributes": {
                                    "source_attribute": {
                                        "target": {
                                            "class": "target_class",
                                            "attribute": "value",
                                            "value_list": ("tww_vl.lookup"),
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        )


def test_mapping_parser_rejects_unqualified_value_list(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="schema-qualified",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "test": {
                        "classes": {
                            "SourceClass": {
                                "identities": {
                                    "target_class": {},
                                },
                                "attributes": {
                                    "source_attribute": {
                                        "target": {
                                            "class": "target_class",
                                            "attribute": "value",
                                            "value_list": "lookup",
                                            "mapping_attribute": "value_de",
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        )


def test_mapping_parser_rejects_unknown_inherited_model(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        KeyError,
        match="inherits unknown model",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "child": {
                        "defaults": {
                            "inherit_from": "missing",
                        }
                    }
                }
            }
        )


def test_mapping_parser_rejects_inheritance_cycle(
    parser: ModelMappingParser,
) -> None:
    with pytest.raises(
        ValueError,
        match="inheritance cycle",
    ):
        parser.parse_models_dict(
            {
                "models": {
                    "first": {
                        "defaults": {
                            "inherit_from": "second",
                        }
                    },
                    "second": {
                        "defaults": {
                            "inherit_from": "first",
                        }
                    },
                }
            }
        )
