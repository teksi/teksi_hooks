from teksi_hooks.models.rights import AttributeDefinition
from teksi_hooks.models.rulesets import StateTransitionRule
from teksi_hooks.models.validation import TransitionValidation
from teksi_hooks.resolver.validation_resolver import (
    ValidationResolver,
)


def test_validation_resolver_collects_transition_rules() -> None:
    resolver = ValidationResolver()

    attribute = AttributeDefinition(
        transitions=[
            TransitionValidation(
                ruleset=frozenset(
                    {
                        StateTransitionRule(
                            privileges=frozenset(
                                {
                                    "DBW_GEP",
                                }
                            ),
                            from_value="planned",
                            to_value="active",
                        ),
                    }
                ),
            ),
        ],
    )

    rules = resolver.resolve_transition_rules(
        attribute,
    )

    assert len(rules) == 1

    rule = next(iter(rules))

    assert rule.from_value == "planned"
    assert rule.to_value == "active"


def test_validation_resolver_expands_bilateral_rule() -> None:
    resolver = ValidationResolver()

    attribute = AttributeDefinition(
        transitions=[
            TransitionValidation(
                ruleset=frozenset(
                    {
                        StateTransitionRule(
                            privileges=frozenset(
                                {
                                    "DBW_GEP",
                                }
                            ),
                            from_value="planned",
                            to_value="active",
                            bilateral=True,
                        ),
                    }
                ),
            ),
        ],
    )

    rules = resolver.resolve_transition_rules(
        attribute,
    )

    assert len(rules) == 2

    assert (
        "planned",
        "active",
    ) in {
        (
            rule.from_value,
            rule.to_value,
        )
        for rule in rules
    }

    assert (
        "active",
        "planned",
    ) in {
        (
            rule.from_value,
            rule.to_value,
        )
        for rule in rules
    }


def test_validation_resolver_groups_rules_by_attribute() -> None:
    resolver = ValidationResolver()

    attribute = AttributeDefinition(
        transitions=[
            TransitionValidation(
                ruleset=frozenset(
                    {
                        StateTransitionRule(
                            privileges=frozenset(
                                {
                                    "DBW_GEP",
                                }
                            ),
                            from_value="planned",
                            to_value="active",
                        ),
                    }
                ),
            ),
        ],
    )

    transition_rules = resolver.resolve_class_transition_rules(
        {
            "status": attribute,
        }
    )

    assert set(
        transition_rules.keys(),
    ) == {
        "status",
    }

    assert (
        len(
            transition_rules["status"],
        )
        == 1
    )


def test_validation_resolver_ignores_attributes_without_transitions() -> None:
    resolver = ValidationResolver()

    transition_rules = resolver.resolve_class_transition_rules(
        {
            "remark": AttributeDefinition(),
        }
    )

    assert transition_rules == {}
