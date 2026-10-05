import pytest

from teksi_hooks.exceptions import (
    EffectValidationError,
)
from teksi_hooks.models.canonical_object import CanonicalObjectIdentity
from teksi_hooks.models.effects import (
    EnforceExistsEffect,
    EnforceNotExistsEffect,
    UpdateAttributeEffect,
)
from teksi_hooks.parser.effects_parser import EffectParser


def test_parse_update_attribute_effect() -> None:
    parser = EffectParser()

    document = parser.parse_json(
        """
        {
          "version": 1,
          "source": {
            "model": "agxx",
            "class_id": "GepKnoten",
            "object_id": "ch123456AG987654"
          },
          "effects": [
            {
              "kind": "update_attribute",
              "identity": {
                "class_id": "agxx_wastewater_node",
                "attributes": {
                  "fk_wastewater_node": "ch123456AG987654"
                }
              },
              "attribute_id": "ag64_function",
              "value": 1234
            }
          ]
        }
        """
    )

    assert document.version == 1
    assert document.source.model == "agxx"
    assert document.source.class_id == "GepKnoten"
    assert len(document.effects) == 1

    effect = document.effects[0]

    assert isinstance(
        effect,
        UpdateAttributeEffect,
    )

    assert effect.identity == (
        CanonicalObjectIdentity(
            class_id="agxx_wastewater_node",
            attributes={
                "fk_wastewater_node": "ch123456AG987654",
            },
        )
    )
    assert effect.attribute_id == "ag64_function"
    assert effect.value == 1234


def test_parse_enforce_exists_effect() -> None:
    parser = EffectParser()

    document = parser.parse_json(
        """
        {
          "version": 1,
          "source": {
            "model": "agxx",
            "class_id": "GepKnoten",
            "object_id": "ch123456AG987654"
          },
          "effects": [
            {
              "kind": "enforce_exists",
              "identity": {
                "class_id": "agxx_wastewater_node",
                "attributes": {
                  "fk_wastewater_node": "ch123456AG987654"
                }
              }
            }
          ]
        }
        """
    )

    effect = document.effects[0]

    assert isinstance(
        effect,
        EnforceExistsEffect,
    )

    assert effect.identity == (
        CanonicalObjectIdentity(
            class_id="agxx_wastewater_node",
            attributes={
                "fk_wastewater_node": "ch123456AG987654",
            },
        )
    )


def test_parse_enforce_not_exists_effect() -> None:
    parser = EffectParser()

    document = parser.parse_json(
        """
        {
          "version": 1,
          "source": {
            "model": "agxx",
            "class_id": "GepKnoten",
            "object_id": "ch123456AG987654"
          },
          "effects": [
           {
              "kind": "enforce_not_exists",
              "identity": {
                "class_id": "agxx_wastewater_node",
                "attributes": {
                  "fk_wastewater_node": "ch123456AG987654"
                }
              }
            }
          ]
        }
        """
    )

    effect = document.effects[0]

    assert isinstance(
        effect,
        EnforceNotExistsEffect,
    )

    assert effect.identity == (
        CanonicalObjectIdentity(
            class_id="agxx_wastewater_node",
            attributes={
                "fk_wastewater_node": "ch123456AG987654",
            },
        )
    )


def test_reject_unknown_effect_kind() -> None:
    parser = EffectParser()

    try:
        parser.parse_json(
            """
            {
              "version": 1,
              "source": {
                "model": "agxx",
                "class_id": "GepKnoten",
                "object_id": "ch123456AG987654"
              },
              "effects": [
                {
                  "kind": "explode_database"
                }
              ]
            }
            """
        )
    except ValueError as exc:
        assert "Unsupported effect kind" in str(
            exc,
        )
    else:
        raise AssertionError("Expected ValueError")


def test_reject_unsupported_version() -> None:
    parser = EffectParser()

    with pytest.raises(
        EffectValidationError,
    ):
        parser.parse_json(
            """
            {
              "version": 99,
              "source": {
                "model": "agxx",
                "class_id": "GepKnoten",
                "object_id": "ch123456AG987654"
              },
              "effects": []
            }
            """
        )


def test_parse_multiple_effects() -> None:
    parser = EffectParser()

    document = parser.parse_json(
        """
        {
          "version": 1,
          "source": {
            "model": "agxx",
            "class_id": "GepKnoten",
            "object_id": "ch123456AG987654"
          },
          "effects": [
            {
              "kind": "enforce_exists",
              "identity": {
                "class_id": "agxx_wastewater_node",
                "attributes": {
                  "fk_wastewater_node": "ch123456AG987654"
                }
              }
            },
            {
              "kind": "update_attribute",
              "identity": {
                "class_id": "agxx_wastewater_node",
                "attributes": {
                  "fk_wastewater_node": "ch123456AG876543"
                }
              },
              "attribute_id": "ag64_function",
              "value": 1234
            }
          ]
        }
        """
    )

    assert document.version == 1
    assert len(document.effects) == 2

    assert (
        len(
            document.effects,
        )
        == 2
    )

    assert isinstance(
        document.effects[0],
        EnforceExistsEffect,
    )

    assert isinstance(
        document.effects[1],
        UpdateAttributeEffect,
    )


def test_reject_contradicting_effects() -> None:
    parser = EffectParser()

    with pytest.raises(
        EffectValidationError,
    ):
        parser.parse_json(
            """
            {
              "version": 1,
              "source": {
                "model": "agxx",
                "class_id": "GepKnoten",
                "object_id": "ch123456AG987654"
              },
              "effects": [
                {
                  "kind": "enforce_not_exists",
                  "identity": {
                    "class_id": "agxx_wastewater_node",
                    "attributes": {
                      "fk_wastewater_node": "ch123456AG987654"
                    }
                  }
                },
                {
                  "kind": "update_attribute",
                  "identity": {
                    "class_id": "agxx_wastewater_node",
                    "attributes": {
                      "fk_wastewater_node": "ch123456AG987654"
                    }
                  },
                  "attribute_id": "ag64_function",
                  "value": 1234
                }
              ]
            }
            """
        )
