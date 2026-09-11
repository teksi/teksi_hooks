from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from teksi_hooks.resolver.model_mapping_resolver import (
    ImplicitModelMappingResolver,
)


@dataclass(slots=True)
class FakeImplicitModelMappingCapability:
    """
    Minimal test double for ImplicitModelMappingCapability.
    """

    table_mapping: dict[
        str,
        str,
    ]

    attribute_mapping: dict[
        tuple[
            str,
            str,
        ],
        tuple[
            str,
            str,
        ],
    ]


@pytest.fixture
def dictionary() -> FakeImplicitModelMappingCapability:
    return FakeImplicitModelMappingCapability(
        table_mapping={
            "Abwasserbauwerk": ("wastewater_structure"),
            "Haltung": "reach",
            "Organisation": "organisation",
        },
        attribute_mapping={
            (
                "Abwasserbauwerk",
                "Bezeichnung",
            ): (
                "wastewater_structure",
                "identifier",
            ),
            (
                "Abwasserbauwerk",
                "EigentuemerRef",
            ): (
                "wastewater_structure",
                "fk_owner",
            ),
            (
                "Haltung",
                "LaengeEffektiv",
            ): (
                "reach",
                "length_effective",
            ),
            (
                "Haltung",
                "HaltungspunktVonRef",
            ): (
                "reach",
                "fk_reach_point_from",
            ),
            (
                "Haltung",
                "HaltungspunktNachRef",
            ): (
                "reach",
                "fk_reach_point_to",
            ),
            (
                "Organisation",
                "Bezeichnung",
            ): (
                "organisation",
                "identifier",
            ),
        },
    )


@pytest.fixture
def resolved_mapping(
    dictionary: FakeImplicitModelMappingCapability,
):
    return ImplicitModelMappingResolver(
        dictionary=dictionary,
    ).resolve()


def test_model_mapping_resolver_returns_ssot_mapping(
    resolved_mapping,
) -> None:
    assert resolved_mapping.is_ssot is True


def test_model_mapping_resolver_imports_all_classes(
    resolved_mapping,
) -> None:
    assert set(
        resolved_mapping.classes,
    ) == {
        "Abwasserbauwerk",
        "Haltung",
        "Organisation",
    }


def test_model_mapping_resolver_maps_source_class_to_canonical_class(
    resolved_mapping,
) -> None:
    cls = resolved_mapping.classes["Abwasserbauwerk"]

    assert cls.canonical_class_id == "wastewater_structure"


def test_model_mapping_resolver_uses_default_identity(
    resolved_mapping,
) -> None:
    identity = resolved_mapping.defaults.identity

    assert identity.source_attribute == "t_ili_tid"
    assert identity.canonical_attribute == "obj_id"


def test_model_mapping_resolver_adds_class_identity(
    resolved_mapping,
) -> None:
    cls = resolved_mapping.classes["Abwasserbauwerk"]

    assert set(
        cls.identities,
    ) == {
        "wastewater_structure",
    }

    identity = cls.identities["wastewater_structure"]

    assert identity.source_attribute == "t_ili_tid"
    assert identity.canonical_attribute == "obj_id"


def test_model_mapping_resolver_reuses_default_identity_for_classes(
    resolved_mapping,
) -> None:
    default_identity = resolved_mapping.defaults.identity

    for cls in resolved_mapping.classes.values():
        assert (
            len(
                cls.identities,
            )
            == 1
        )

        class_identity = next(
            iter(
                cls.identities.values(),
            )
        )

        assert class_identity == default_identity


def test_model_mapping_resolver_imports_class_attributes(
    resolved_mapping,
) -> None:
    cls = resolved_mapping.classes["Abwasserbauwerk"]

    assert set(
        cls.attributes,
    ) == {
        "Bezeichnung",
        "EigentuemerRef",
    }


def test_model_mapping_resolver_maps_literal_attribute(
    resolved_mapping,
) -> None:
    attribute = resolved_mapping.classes["Abwasserbauwerk"].attributes["Bezeichnung"]

    assert attribute.canonical_class_id == "wastewater_structure"
    assert attribute.canonical_attr_id == "identifier"
    assert attribute.value_list is None
    assert attribute.values == {}


def test_model_mapping_resolver_maps_foreign_key_attribute(
    resolved_mapping,
) -> None:
    attribute = resolved_mapping.classes["Abwasserbauwerk"].attributes["EigentuemerRef"]

    assert attribute.canonical_class_id == "wastewater_structure"
    assert attribute.canonical_attr_id == "fk_owner"
    assert attribute.value_list is None
    assert attribute.values == {}


def test_model_mapping_resolver_maps_reach_point_references(
    resolved_mapping,
) -> None:
    attributes = resolved_mapping.classes["Haltung"].attributes

    from_mapping = attributes["HaltungspunktVonRef"]
    to_mapping = attributes["HaltungspunktNachRef"]

    assert from_mapping.canonical_class_id == "reach"
    assert from_mapping.canonical_attr_id == "fk_reach_point_from"

    assert to_mapping.canonical_class_id == "reach"
    assert to_mapping.canonical_attr_id == "fk_reach_point_to"


def test_model_mapping_resolver_does_not_add_function_mapping(
    resolved_mapping,
) -> None:
    for cls in resolved_mapping.classes.values():
        assert cls.function is None


def test_model_mapping_resolver_does_not_add_relations(
    resolved_mapping,
) -> None:
    for cls in resolved_mapping.classes.values():
        assert cls.relations == {}


def test_model_mapping_resolver_has_empty_model_defaults(
    resolved_mapping,
) -> None:
    defaults = resolved_mapping.defaults

    assert defaults.inherit_from is None
    assert defaults.identities == {}
    assert defaults.attributes == {}
    assert defaults.relations == {}


def test_model_mapping_resolver_supports_custom_identity_attributes(
    dictionary: FakeImplicitModelMappingCapability,
) -> None:
    mapping = ImplicitModelMappingResolver(
        dictionary=dictionary,
        source_identity_attribute="source_oid",
        canonical_identity_attribute="canonical_oid",
    ).resolve()

    assert mapping.defaults.identity.source_attribute == "source_oid"
    assert mapping.defaults.identity.canonical_attribute == "canonical_oid"

    identity = mapping.classes["Haltung"].identities["reach"]

    assert identity.source_attribute == "source_oid"
    assert identity.canonical_attribute == "canonical_oid"


def test_model_mapping_resolver_supports_empty_dictionary() -> None:
    dictionary = FakeImplicitModelMappingCapability(
        table_mapping={},
        attribute_mapping={},
    )

    mapping = ImplicitModelMappingResolver(
        dictionary=dictionary,
    ).resolve()

    assert mapping.classes == {}
    assert mapping.is_ssot is True
    assert mapping.defaults.identity.source_attribute == "t_ili_tid"
    assert mapping.defaults.identity.canonical_attribute == "obj_id"


def test_model_mapping_resolver_rejects_orphan_attribute_mapping() -> None:
    dictionary = FakeImplicitModelMappingCapability(
        table_mapping={
            "Haltung": "reach",
        },
        attribute_mapping={
            (
                "UnknownClass",
                "Attribute",
            ): (
                "unknown_class",
                "attribute",
            ),
        },
    )

    with pytest.raises(
        ValueError,
        match=("attribute mappings refer to source classes without table mappings"),
    ):
        ImplicitModelMappingResolver(
            dictionary=dictionary,
        ).resolve()


@pytest.mark.parametrize(
    (
        "table_mapping",
        "expected_message",
    ),
    (
        (
            {
                "": "reach",
            },
            "source class identifier must not be empty",
        ),
        (
            {
                "Haltung": "",
            },
            "canonical class identifier",
        ),
        (
            {
                42: "reach",
            },
            "must be a string",
        ),
        (
            {
                "Haltung": 42,
            },
            "must be a string",
        ),
    ),
)
def test_model_mapping_resolver_rejects_invalid_table_mapping(
    table_mapping: dict[Any, Any],
    expected_message: str,
) -> None:
    dictionary = FakeImplicitModelMappingCapability(
        table_mapping=table_mapping,
        attribute_mapping={},
    )

    with pytest.raises(
        (
            TypeError,
            ValueError,
        ),
        match=expected_message,
    ):
        ImplicitModelMappingResolver(
            dictionary=dictionary,
        ).resolve()


@pytest.mark.parametrize(
    (
        "attribute_mapping",
        "expected_message",
    ),
    (
        (
            {
                (
                    "Haltung",
                    "",
                ): (
                    "reach",
                    "length_effective",
                ),
            },
            "source attribute",
        ),
        (
            {
                (
                    "Haltung",
                    "LaengeEffektiv",
                ): (
                    "",
                    "length_effective",
                ),
            },
            "canonical class",
        ),
        (
            {
                (
                    "Haltung",
                    "LaengeEffektiv",
                ): (
                    "reach",
                    "",
                ),
            },
            "canonical attribute",
        ),
        (
            {
                (
                    "Haltung",
                    42,
                ): (
                    "reach",
                    "length_effective",
                ),
            },
            "must be a string",
        ),
    ),
)
def test_model_mapping_resolver_rejects_invalid_attribute_mapping(
    attribute_mapping: dict[Any, Any],
    expected_message: str,
) -> None:
    dictionary = FakeImplicitModelMappingCapability(
        table_mapping={
            "Haltung": "reach",
        },
        attribute_mapping=attribute_mapping,
    )

    with pytest.raises(
        (
            TypeError,
            ValueError,
        ),
        match=expected_message,
    ):
        ImplicitModelMappingResolver(
            dictionary=dictionary,
        ).resolve()


def test_model_mapping_resolver_output_is_deterministic() -> None:
    dictionary = FakeImplicitModelMappingCapability(
        table_mapping={
            "Organisation": "organisation",
            "Haltung": "reach",
            "Abwasserbauwerk": ("wastewater_structure"),
        },
        attribute_mapping={},
    )

    mapping = ImplicitModelMappingResolver(
        dictionary=dictionary,
    ).resolve()

    assert tuple(
        mapping.classes,
    ) == (
        "Abwasserbauwerk",
        "Haltung",
        "Organisation",
    )
