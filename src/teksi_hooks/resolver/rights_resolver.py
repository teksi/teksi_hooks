from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from ..models.rights import (
    AttributeDefinition,
    ClassDefinition,
    DerivedRights,
    ResolvedAttributeDefinition,
    ResolvedClassDefinition,
    ResolvedRights,
    RightsDefinition,
)
from ..models.rulesets import (
    CrudRules,
    InheritRule,
    ResolvedCrudRules,
    Rule,
)
from ..models.validation import (
    AttributeValidation,
    ObjectValidation,
    ValidationDefinition,
)
from .validation_resolver import (
    ValidationResolver,
)


@dataclass(slots=True)
class RightsResolver:
    """
    Resolve parsed rights and validation definitions into runtime definitions.

    Responsibilities:

    - apply default CRUD rules;
    - expand inherited CRUD rules;
    - apply wildcard attribute defaults;
    - apply default and class-specific attribute validations;
    - apply default and class-specific object validations;
    - apply default and class-specific mandatory attributes;
    - produce immutable resolved models;
    - build class-level transition definitions.

    Rights and validation definitions are parsed separately and combined only
    while constructing the resolved runtime configuration.
    """

    validation_resolver: ValidationResolver = field(
        default_factory=ValidationResolver,
    )

    def resolve(
        self,
        definition: RightsDefinition,
        validation_definition: ValidationDefinition | None = None,
    ) -> ResolvedRights:
        """
        Resolve rights and validation configuration.

        Validation configuration is optional to preserve compatibility with
        callers that currently resolve rights without a validation file.
        """

        effective_validation_definition = (
            validation_definition
            if validation_definition is not None
            else ValidationDefinition()
        )

        return ResolvedRights(
            classes={
                class_id: self._resolve_class(
                    class_definition=class_definition,
                    definition=definition,
                    validation_definition=(effective_validation_definition),
                )
                for (
                    class_id,
                    class_definition,
                ) in definition.classes.items()
            },
            derived_rights=self.resolve_derived_rights_config(
                definition,
            ),
            subclass_rights=self.resolve_subclass_rights(
                definition,
            ),
            allow_transitive_transitions=(definition.allow_transitive_transitions),
        )

    def _resolve_class(
        self,
        *,
        class_definition: ClassDefinition,
        definition: RightsDefinition,
        validation_definition: ValidationDefinition,
    ) -> ResolvedClassDefinition:
        """
        Resolve one class from rights and validation configuration.
        """

        attribute_validations = self._attribute_validations_for_class(
            class_id=class_definition.id,
            validation_definition=validation_definition,
        )

        attributes = self._resolve_attributes(
            class_definition=class_definition,
            definition=definition,
            attribute_validations=attribute_validations,
        )

        return ResolvedClassDefinition(
            id=class_definition.id,
            crud_rules=self._resolve_crud_rules(
                class_definition=class_definition,
                defaults=definition.defaults.crud_rules,
            ),
            attributes=attributes,
            transition_rules=(
                self.validation_resolver.resolve_class_transition_rules(
                    attributes,
                )
            ),
            mandatory_attributes=(
                self._mandatory_attributes_for_class(
                    class_id=class_definition.id,
                    validation_definition=validation_definition,
                )
            ),
            object_validations=(
                self._object_validations_for_class(
                    class_id=class_definition.id,
                    validation_definition=validation_definition,
                )
            ),
        )

    def _resolve_crud_rules(
        self,
        *,
        class_definition: ClassDefinition,
        defaults: CrudRules,
    ) -> ResolvedCrudRules:
        """
        Resolve effective CRUD rules for one class.
        """

        create_rules = self._rules_or_default(
            class_definition.crud_rules.create_rules,
            defaults.create_rules,
        )

        read_rules = self._rules_or_default(
            class_definition.crud_rules.read_rules,
            defaults.read_rules,
        )

        update_rules = self._rules_or_default(
            class_definition.crud_rules.update_rules,
            defaults.update_rules,
        )

        delete_rules = self._rules_or_default(
            class_definition.crud_rules.delete_rules,
            defaults.delete_rules,
        )

        rule_sets = {
            "create_rules": create_rules,
            "read_rules": read_rules,
            "update_rules": update_rules,
            "delete_rules": delete_rules,
        }

        return ResolvedCrudRules(
            create_rules=self._expand_inherit_rules(
                create_rules,
                rule_sets,
            ),
            read_rules=self._expand_inherit_rules(
                read_rules,
                rule_sets,
            ),
            update_rules=self._expand_inherit_rules(
                update_rules,
                rule_sets,
            ),
            delete_rules=self._expand_inherit_rules(
                delete_rules,
                rule_sets,
            ),
        )

    def _rules_or_default(
        self,
        rules: list[Rule,],
        default_rules: list[Rule,],
    ) -> tuple[
        Rule,
        ...,
    ]:
        """
        Return explicitly configured rules or the corresponding defaults.
        """

        if rules:
            return tuple(
                rules,
            )

        return tuple(
            default_rules,
        )

    def _expand_inherit_rules(
        self,
        rules: tuple[
            Rule,
            ...,
        ],
        rule_sets: Mapping[
            str,
            tuple[
                Rule,
                ...,
            ],
        ],
    ) -> tuple[
        Rule,
        ...,
    ]:
        """
        Expand direct references to another CRUD rule set.
        """

        expanded: list[Rule] = []

        for rule in rules:
            if isinstance(
                rule,
                InheritRule,
            ):
                try:
                    inherited_rules = rule_sets[rule.source]
                except KeyError as exception:
                    raise KeyError(
                        f"Unknown inherited rule set: {rule.source!r}"
                    ) from exception

                expanded.extend(
                    inherited_rule
                    for inherited_rule in inherited_rules
                    if not isinstance(
                        inherited_rule,
                        InheritRule,
                    )
                )
            else:
                expanded.append(
                    rule,
                )

        return tuple(
            expanded,
        )

    def _resolve_attributes(
        self,
        *,
        class_definition: ClassDefinition,
        definition: RightsDefinition,
        attribute_validations: Mapping[
            str,
            tuple[
                AttributeValidation,
                ...,
            ],
        ],
    ) -> Mapping[
        str,
        ResolvedAttributeDefinition,
    ]:
        """
        Resolve attribute rights, validations and transitions for one class.

        Attributes declared only in the validation configuration are included
        even when the rights configuration has no explicit attribute entry.
        """

        resolved: dict[
            str,
            ResolvedAttributeDefinition,
        ] = {}

        attribute_names = set(
            class_definition.attributes,
        )

        attribute_names.update(
            attribute_validations,
        )

        for attribute_name in attribute_names:
            attribute_definition = class_definition.attributes.get(
                attribute_name,
                AttributeDefinition(),
            )

            resolved[attribute_name] = self._resolve_attribute(
                attribute_name=attribute_name,
                attribute_definition=attribute_definition,
                definition=definition,
                validation_rules=(
                    attribute_validations.get(
                        attribute_name,
                        (),
                    )
                ),
            )

        return resolved

    def _resolve_attribute(
        self,
        *,
        attribute_name: str,
        attribute_definition: AttributeDefinition,
        definition: RightsDefinition,
        validation_rules: tuple[
            AttributeValidation,
            ...,
        ] = (),
    ) -> ResolvedAttributeDefinition:
        """
        Resolve rights, validations and transitions for one attribute.
        """

        update_privileges = attribute_definition.update_privileges

        if not update_privileges:
            for default in definition.defaults.attribute_defaults:
                if fnmatchcase(
                    attribute_name,
                    default.pattern,
                ):
                    update_privileges = default.update_privileges
                    break

        validations = list(
            attribute_definition.validations,
        )

        validations.extend(
            validation_rules,
        )

        return ResolvedAttributeDefinition(
            update_privileges=update_privileges,
            validations=tuple(
                validations,
            ),
            transitions=tuple(
                attribute_definition.transitions,
            ),
        )

    def _attribute_validations_for_class(
        self,
        *,
        class_id: str,
        validation_definition: ValidationDefinition,
    ) -> Mapping[
        str,
        tuple[
            AttributeValidation,
            ...,
        ],
    ]:
        """
        Return effective attribute validations for one class.

        Default attribute validations apply to every configured class.
        A class-specific validation group replaces the default group for the
        same canonical attribute.
        """

        validations = dict(
            validation_definition.attribute_validations,
        )

        class_validation_definition = validation_definition.classes.get(
            class_id,
        )

        if class_validation_definition is not None:
            validations.update(
                class_validation_definition.attribute_validations,
            )

        return validations

    def _mandatory_attributes_for_class(
        self,
        *,
        class_id: str,
        validation_definition: ValidationDefinition,
    ) -> frozenset[str]:
        """
        Return effective mandatory attributes for one class.

        Class-specific mandatory attributes extend the default set.
        """

        mandatory_attributes = set(
            validation_definition.mandatory_attributes,
        )

        class_validation_definition = validation_definition.classes.get(
            class_id,
        )

        if class_validation_definition is not None:
            mandatory_attributes.update(
                class_validation_definition.mandatory_attributes,
            )

        return frozenset(
            mandatory_attributes,
        )

    def _object_validations_for_class(
        self,
        *,
        class_id: str,
        validation_definition: ValidationDefinition,
    ) -> tuple[
        ObjectValidation,
        ...,
    ]:
        """
        Return effective object validations for one class.

        Default object-validation groups apply to every configured class.
        A class-specific group replaces the default group with the same
        configuration identifier.
        """

        validation_groups = dict(
            validation_definition.object_validations,
        )

        class_validation_definition = validation_definition.classes.get(
            class_id,
        )

        if class_validation_definition is not None:
            validation_groups.update(
                class_validation_definition.object_validations,
            )

        return tuple(
            validation
            for validations in validation_groups.values()
            for validation in validations
        )

    def resolve_subclass_rights(
        self,
        definition: RightsDefinition,
    ) -> Mapping[
        str,
        tuple[
            str,
            ...,
        ],
    ]:
        """
        Resolve subclass-based rights inheritance.

        Return parent class identifiers mapped to child classes whose rights
        should be considered during authorization evaluation.
        """

        subclasses: dict[
            str,
            list[str,],
        ] = {}

        for child in definition.classes.values():
            if not child.superclass_id:
                continue

            if not child.rights_from_subclass:
                continue

            subclasses.setdefault(
                child.superclass_id,
                [],
            ).append(
                child.id,
            )

        return {
            parent_class: tuple(
                child_classes,
            )
            for (
                parent_class,
                child_classes,
            ) in subclasses.items()
        }

    def resolve_derived_rights_config(
        self,
        definition: RightsDefinition,
    ) -> Mapping[
        str,
        tuple[
            DerivedRights,
            ...,
        ],
    ]:
        """
        Resolve derived-rights definitions for all configured classes.
        """

        resolved: dict[
            str,
            tuple[
                DerivedRights,
                ...,
            ],
        ] = {}

        for (
            class_id,
            class_definition,
        ) in definition.classes.items():
            derived_rights = self._derived_rights_for_class(
                class_definition=class_definition,
                definition=definition,
                visited=(),
            )

            if derived_rights:
                resolved[class_id] = derived_rights

        return resolved

    def _derived_rights_for_class(
        self,
        *,
        class_definition: ClassDefinition,
        definition: RightsDefinition,
        visited: tuple[
            str,
            ...,
        ],
    ) -> tuple[
        DerivedRights,
        ...,
    ]:
        """
        Return direct and inherited derived-rights definitions for one class.
        """

        if class_definition.id in visited:
            return ()

        next_visited = visited + (class_definition.id,)

        inherited: list[DerivedRights] = []

        if class_definition.superclass_id:
            superclass = definition.classes.get(
                class_definition.superclass_id,
            )

            if superclass is not None:
                inherited.extend(
                    self._derived_rights_for_class(
                        class_definition=superclass,
                        definition=definition,
                        visited=next_visited,
                    )
                )

        inherited.extend(
            class_definition.derive_rights_from,
        )

        return tuple(
            inherited,
        )
