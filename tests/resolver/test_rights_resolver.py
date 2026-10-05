from teksi_hooks.models.rulesets import (
    InheritRule,
    OwnershipRule,
    PrivilegeRule,
    ResolvedCrudRules,
)


def test_rights_resolver_resolves_classes(
    resolved_rights,
) -> None:
    assert "wastewater_structure" in resolved_rights.classes
    assert "wastewater_networkelement" in resolved_rights.classes
    assert "wastewater_node" in resolved_rights.classes
    assert "maintenance" in resolved_rights.classes
    assert "pipe_profile" in resolved_rights.classes


def test_rights_resolver_returns_resolved_crud_rules(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["wastewater_structure"]

    assert isinstance(
        resolved.crud_rules,
        ResolvedCrudRules,
    )

    assert isinstance(
        resolved.crud_rules.create_rules,
        tuple,
    )
    assert isinstance(
        resolved.crud_rules.update_rules,
        tuple,
    )
    assert isinstance(
        resolved.crud_rules.delete_rules,
        tuple,
    )


def test_rights_resolver_expands_inherit_rules(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["wastewater_structure"]

    assert len(resolved.crud_rules.create_rules) == 2
    assert len(resolved.crud_rules.update_rules) == 2
    assert len(resolved.crud_rules.delete_rules) == 2

    assert all(
        not isinstance(rule, InheritRule) for rule in resolved.crud_rules.update_rules
    )

    assert all(
        not isinstance(rule, InheritRule) for rule in resolved.crud_rules.delete_rules
    )


def test_rights_resolver_preserves_privilege_rules(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["wastewater_structure"]

    first_rule = resolved.crud_rules.create_rules[0]

    assert isinstance(
        first_rule,
        PrivilegeRule,
    )

    assert first_rule.privileges == frozenset(
        {
            "DBW_GEP",
        }
    )


def test_rights_resolver_expands_crud_rules_shortcut(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["pipe_profile"]

    assert len(resolved.crud_rules.create_rules) == 1
    assert len(resolved.crud_rules.read_rules) == 1
    assert len(resolved.crud_rules.update_rules) == 1
    assert len(resolved.crud_rules.delete_rules) == 1

    create_rule = resolved.crud_rules.create_rules[0]
    read_rule = resolved.crud_rules.read_rules[0]
    update_rule = resolved.crud_rules.update_rules[0]
    delete_rule = resolved.crud_rules.delete_rules[0]

    assert isinstance(
        create_rule,
        PrivilegeRule,
    )

    assert create_rule.privileges == frozenset(
        {
            "DBW_WI",
            "DBW_GEP",
        }
    )

    assert read_rule == create_rule
    assert update_rule == create_rule
    assert delete_rule == create_rule


def test_rights_resolver_preserves_attribute_privileges(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["wastewater_structure"]

    status = resolved.attributes["status"]

    assert status.update_privileges == frozenset(
        {
            "DBW_GEP",
            "DBW_WI",
        }
    )


def test_rights_resolver_inherits_derived_rights_to_reach(
    resolved_rights,
) -> None:
    assert "reach" in resolved_rights.derived_rights

    assert any(
        relation.class_id == "wastewater_structure"
        for relation in resolved_rights.derived_rights["reach"]
    )


def test_rights_resolver_preserves_attribute_transitions(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["wastewater_structure"]

    status = resolved.attributes["status"]

    assert len(status.transitions) == 1

    transition_validation = status.transitions[0]

    assert transition_validation.allow_transitive is True
    assert len(transition_validation.ruleset) == 2


def test_rights_resolver_preserves_ownership_rules(
    resolved_rights,
) -> None:
    resolved = resolved_rights.classes["maintenance"]

    assert len(resolved.crud_rules.update_rules) == 1
    assert len(resolved.crud_rules.delete_rules) == 1

    update_rule = resolved.crud_rules.update_rules[0]
    delete_rule = resolved.crud_rules.delete_rules[0]

    assert isinstance(
        update_rule,
        OwnershipRule,
    )
    assert update_rule.attribute == "fk_provider"

    assert isinstance(
        delete_rule,
        OwnershipRule,
    )
    assert delete_rule.attribute == "fk_provider"
