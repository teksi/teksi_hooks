from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import Severity
from ..models.conditions import (
    AllOfCondition,
    AnyOfCondition,
    Condition,
    LocalCondition,
    RemoteCondition,
)
from ..models.privilege import (
    ALL_PRIVILEGES,
    PrivilegeId,
    PrivilegeMetadata,
)
from ..models.rights import (
    AttributeDefaultDefinition,
    AttributeDefinition,
    ClassDefinition,
    DefaultDefinitions,
    DerivedRights,
    RightsDefinition,
)
from ..models.rulesets import (
    CrudRules,
    InheritRule,
    OwnershipRule,
    PrivilegeRule,
    Rule,
    StateTransitionRule,
)
from ..models.validation import (
    AttributeValidation,
    ChangeOperation,
    TransitionValidation,
)


@dataclass(slots=True)
class RightsParser:
    """
    Parser for rights YAML definitions.

    Converts YAML dictionaries into parsed rights model objects.
    This parser does not resolve inheritance, defaults, derived rights,
    or inherited rule references. That is the responsibility of the
    rights resolver.
    """

    def parse_text(
        self,
        txt: str,
    ) -> RightsDefinition:
        data = yaml.safe_load(txt)

        return self._parse_dict(
            data or {},
        )

    def parse_file(
        self,
        path: str | Path,
    ) -> RightsDefinition:
        with open(path, encoding="utf-8") as file:
            data = yaml.safe_load(file)

        return self._parse_dict(
            data or {},
        )

    def _parse_dict(
        self,
        data: dict[str, Any],
    ) -> RightsDefinition:
        settings = data.get(
            "settings",
            {},
        )

        defaults_settings = data.get(
            "defaults",
            {},
        )

        class_definitions = self._parse_classes(
            data.get(
                "classes",
                [],
            ),
        )

        defaults = self._parse_defaults(
            defaults_settings,
        )

        return RightsDefinition(
            defaults=defaults,
            privileges=self._parse_privileges(
                data.get(
                    "privileges",
                    {},
                )
            ),
            classes={
                class_definition.id: class_definition
                for class_definition in class_definitions
            },
            validation_rules=self._parse_validation_rules(
                defaults_settings.get(
                    "validation_rules",
                    {},
                ),
            ),
            allow_transitive_transitions=settings.get(
                "allow_transitive_transitions",
                True,
            ),
        )

    def _parse_defaults(
        self,
        raw: dict[str, Any],
    ) -> DefaultDefinitions:
        return DefaultDefinitions(
            crud_rules=CrudRules(
                create_rules=self._parse_rules(
                    raw.get(
                        "create_rules",
                        [],
                    ),
                ),
                read_rules=self._parse_rules(
                    raw.get(
                        "read_rules",
                        [],
                    ),
                ),
                update_rules=self._parse_rules(
                    raw.get(
                        "update_rules",
                        [],
                    ),
                ),
                delete_rules=self._parse_rules(
                    raw.get(
                        "delete_rules",
                        [],
                    ),
                ),
            ),
            attribute_defaults=self._parse_attribute_defaults(
                raw.get(
                    "attribute_defaults",
                    {},
                ),
            ),
        )

    def _parse_attribute_defaults(
        self,
        raw: dict[str, Any],
    ) -> tuple[AttributeDefaultDefinition, ...]:
        return tuple(
            self._parse_attribute_default(
                pattern,
                definition,
            )
            for pattern, definition in raw.items()
        )

    def _parse_attribute_default(
        self,
        pattern: str,
        raw: dict[str, Any],
    ) -> AttributeDefaultDefinition:
        if not isinstance(
            raw,
            dict,
        ):
            raise TypeError(
                f"Expected mapping for wildcard default {pattern!r}, got {type(raw)!r}"
            )

        return AttributeDefaultDefinition(
            pattern=pattern,
            update_privileges=self._parse_privilege_ids(
                raw.get(
                    "update",
                    [],
                ),
            ),
        )

    def _parse_classes(
        self,
        raw_classes: list[dict[str, Any]],
    ) -> list:
        return [
            self._parse_class(
                raw,
            )
            for raw in raw_classes
        ]

    def _parse_class(
        self,
        raw: dict[str, Any],
    ) -> ClassDefinition:
        return ClassDefinition(
            id=raw["id"],
            superclass_id=raw.get(
                "extends",
            ),
            rights_from_subclass=raw.get(
                "rights_from_subclass",
                False,
            ),
            derive_rights_from=self._parse_derive_rights_from(
                raw.get(
                    "derive_rights_from",
                    [],
                ),
            ),
            crud_rules=self._parse_crud_rules(
                raw,
            ),
            attributes=self._parse_attributes(
                raw.get(
                    "attributes",
                    {},
                ),
            ),
        )

    def _parse_crud_rules(
        self,
        raw: dict[str, Any],
    ) -> CrudRules:
        crud_rules = self._parse_rules(
            raw.get(
                "crud_rules",
                [],
            ),
        )

        if crud_rules:
            return CrudRules(
                create_rules=list(
                    crud_rules,
                ),
                read_rules=list(
                    crud_rules,
                ),
                update_rules=list(
                    crud_rules,
                ),
                delete_rules=list(
                    crud_rules,
                ),
            )

        return CrudRules(
            create_rules=self._parse_rules(
                raw.get(
                    "create_rules",
                    [],
                ),
            ),
            read_rules=self._parse_rules(
                raw.get(
                    "read_rules",
                    [],
                ),
            ),
            update_rules=self._parse_rules(
                raw.get(
                    "update_rules",
                    [],
                ),
            ),
            delete_rules=self._parse_rules(
                raw.get(
                    "delete_rules",
                    [],
                ),
            ),
        )

    def _parse_derive_rights_from(
        self,
        raw_items: list[dict[str, Any]],
    ) -> tuple[DerivedRights, ...]:
        return tuple(
            DerivedRights(
                class_id=raw["class"],
                local_attribute=raw.get(
                    "local_attribute",
                    "obj_id",
                ),
                remote_attribute=raw.get(
                    "remote_attribute",
                    "obj_id",
                ),
            )
            for raw in raw_items
        )

    def _parse_attributes(
        self,
        raw_attributes: dict[str, Any],
    ) -> dict[str, AttributeDefinition]:
        return {
            attribute_name: self._parse_attribute(
                raw,
            )
            for attribute_name, raw in raw_attributes.items()
        }

    def _parse_attribute(
        self,
        raw: dict[str, Any],
    ) -> AttributeDefinition:
        return AttributeDefinition(
            update_privileges=self._parse_privilege_ids(
                raw.get(
                    "update",
                    [],
                ),
            ),
            validations=self._parse_attribute_validations(
                raw.get(
                    "rules",
                    [],
                ),
            ),
            transitions=self._parse_transition_validations(
                raw.get(
                    "transitions",
                    [],
                ),
            ),
        )

    def _parse_attribute_validation(
        self,
        data: dict[str, Any],
    ) -> AttributeValidation:
        operation_values = data.get(
            "operations",
            [
                "insert",
                "update",
                "delete",
            ],
        )

        return AttributeValidation(
            id=data["id"],
            level=Severity(
                data.get(
                    "level",
                    "error",
                ),
            ),
            operations=tuple(
                ChangeOperation(
                    operation,
                )
                for operation in operation_values
            ),
            context_value=data.get(
                "context_value",
            ),
        )

    def _parse_rules(
        self,
        raw_rules: list[dict[str, Any]] | dict[str, Any],
    ) -> list:
        if not raw_rules:
            return []

        if isinstance(
            raw_rules,
            dict,
        ):
            raw_rules = [
                raw_rules,
            ]

        return [
            self._parse_rule(
                raw,
            )
            for raw in raw_rules
        ]

    def _parse_rule(
        self,
        raw: dict[str, Any],
    ) -> Rule:
        if "privileges" in raw:
            return PrivilegeRule(
                privileges=self._parse_privilege_ids(
                    raw["privileges"],
                ),
                when=self._parse_condition(
                    raw.get(
                        "when",
                    ),
                ),
            )

        if "ownership" in raw:
            ownership = raw["ownership"]

            return OwnershipRule(
                attribute=ownership["attribute"],
            )

        if "inherit" in raw:
            return InheritRule(
                source=raw["inherit"],
            )

        raise ValueError(f"Unknown rule definition: {raw!r}")

    def _parse_privilege_ids(
        self,
        raw: str | list[str],
    ) -> frozenset:
        if isinstance(
            raw,
            str,
        ):
            if raw != "all":
                raise ValueError(f"Unknown privilege selector: {raw!r}")

            return frozenset(
                {
                    ALL_PRIVILEGES,
                },
            )

        return frozenset(raw)

    def _parse_privileges(
        self,
        raw_privileges: dict[str, Any],
    ) -> dict[
        PrivilegeId,
        PrivilegeMetadata,
    ]:
        return {
            privilege_id: PrivilegeMetadata(
                labels=definition.get(
                    "labels",
                    {},
                ),
                descriptions=definition.get(
                    "descriptions",
                    {},
                ),
            )
            for privilege_id, definition in raw_privileges.items()
        }

    def _parse_condition(
        self,
        raw: dict[str, Any] | None,
    ) -> Condition | None:
        if raw is None:
            return None

        if "local" in raw:
            return self._parse_local_condition(
                raw["local"],
            )

        if "remote" in raw:
            return self._parse_remote_condition(
                raw["remote"],
            )

        if "any_of" in raw:
            return AnyOfCondition(
                conditions=tuple(
                    condition
                    for condition in (
                        self._parse_condition(
                            item,
                        )
                        for item in raw["any_of"]
                    )
                    if condition is not None
                ),
            )

        if "all_of" in raw:
            return AllOfCondition(
                conditions=tuple(
                    condition
                    for condition in (
                        self._parse_condition(
                            item,
                        )
                        for item in raw["all_of"]
                    )
                    if condition is not None
                ),
            )

        raise ValueError(f"Unknown condition definition: {raw!r}")

    def _parse_local_condition(
        self,
        raw: dict[str, Any],
    ) -> LocalCondition:
        operator, value = self._parse_operator_value(
            raw,
        )

        return LocalCondition(
            attribute=raw["attribute"],
            operator=operator,
            value=value,
        )

    def _parse_remote_condition(
        self,
        raw: dict[str, Any],
    ) -> RemoteCondition:
        operator, value = self._parse_operator_value(
            raw,
        )

        return RemoteCondition(
            relation=raw["relation"],
            attribute=raw["attribute"],
            operator=operator,
            value=value,
        )

    def _parse_operator_value(
        self,
        raw: dict[str, Any],
    ) -> tuple[str, Any]:
        ignored_keys = {
            "attribute",
            "relation",
        }

        operator_keys = [key for key in raw if key not in ignored_keys]

        if (
            len(
                operator_keys,
            )
            != 1
        ):
            raise ValueError(f"Expected exactly one condition operator in {raw!r}")

        operator = operator_keys[0]

        return operator, raw[operator]

    def _parse_transition_validations(
        self,
        raw_rules: list[dict[str, Any]],
    ) -> list:
        if not raw_rules:
            return []

        ruleset = frozenset(
            StateTransitionRule(
                privileges=self._parse_privilege_ids(
                    raw["privileges"],
                ),
                from_value=raw.get(
                    "from",
                ),
                to_value=raw.get(
                    "to",
                ),
                bilateral=raw.get(
                    "bilateral",
                    False,
                ),
            )
            for raw in raw_rules
        )

        return [
            TransitionValidation(
                ruleset=ruleset,
                allow_transitive=True,
            ),
        ]

    def _parse_attribute_validations(
        self,
        raw_validations: list[dict[str, Any]],
    ) -> tuple[AttributeValidation, ...]:
        return tuple(
            self._parse_attribute_validation(
                raw_validation,
            )
            for raw_validation in raw_validations
        )

    def _parse_validation_rules(
        self,
        raw_rules: dict[str, Any],
    ) -> dict[
        str,
        tuple[AttributeValidation, ...],
    ]:
        return {
            attribute_name: self._parse_attribute_validations(
                definition.get(
                    "rules",
                    [],
                ),
            )
            for attribute_name, definition in raw_rules.items()
        }

    def _merge_validation_rules(
        self,
        base,
        override,
    ):
        merged = {}

        for attribute_name, rules in base.items():
            merged[attribute_name] = tuple(
                rules,
            )

        for attribute_name, rules in override.items():
            if attribute_name in merged:
                merged[attribute_name] = merged[attribute_name] + tuple(
                    rules,
                )
            else:
                merged[attribute_name] = tuple(
                    rules,
                )

        return merged
