from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any

from ..models.oid import Oid

from ..capabilities.conditions import (
    ConditionsCapability,
    ConditionEvaluationContext,
)
from ..capabilities.privilege import ResolvedProviderCapability
from ..capabilities.rights import (
    RightsCapability,
    DerivedRightsCapability,
    SubclassRightsCapability,
)
from ..capabilities.relation_lookup import RelationLookupCapability


from ..models.rights import CanonicalDerivedRights
from ..models.canonical_object import CanonicalObjectIdentity
from ..models.rulesets import (
    Rule,
    PrivilegeRule,
    OwnershipRule,
)
from ..models.privilege import PrivilegeId, ALL_PRIVILEGES
from ..models.validation import ChangeOperation


@dataclass(
    slots=True,
    frozen=True,
)
class RightsEvaluationBaseContext:
    """
    Rights context shared by every change in one workflow.
    """

    dataowner_oid: Oid
    provider_oid: Oid

    context_values: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict,
    )


@dataclass(slots=True, frozen=True)
class RightsEvaluationContext:
    """
    Runtime context used for evaluating rights rules.

    The context contains all runtime values needed by rule evaluators:
    provider, data owner, operation type and old/new row values.
    """

    dataowner_oid: Oid
    provider_oid: Oid

    operation: ChangeOperation

    old_values: Mapping[str, Any] = field(
        default_factory=dict,
    )

    new_values: Mapping[str, Any] = field(
        default_factory=dict,
    )

    context_values: Mapping[str, Any] = field(
        default_factory=dict,
    )


class RightsEvaluator:
    """
    Evaluates resolved rights definitions against provider permissions
    and runtime change contexts.

    This class combines:
    - RightsCapability
    - ResolvedProviderCapability
    - ConditionsCapability

    It should contain authorization logic, while the capabilities remain
    lookup/evaluation helpers.
    """

    def __init__(
        self,
        rights: RightsCapability,
        provider: ResolvedProviderCapability,
        conditions: ConditionsCapability,
        derived_rights: DerivedRightsCapability,
        relation_lookup: RelationLookupCapability,
        subclass_rights: SubclassRightsCapability,
    ):
        self.rights = rights
        self.provider = provider
        self.conditions = conditions
        self.derived_rights = derived_rights
        self.relation_lookup = relation_lookup
        self.subclass_rights = subclass_rights

    def can_update_attribute(
        self,
        class_id: str,
        attribute_name: str,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Check whether the provider has the required attribute-level update
        privilege for a canonical class and attribute.
        Ownership and class-level CRUD rules are evaluated separately.
        """

        required_privileges = self.rights.update_privileges(
            class_id,
            attribute_name,
        )

        return self._has_privilege(
            required_privileges,
            context,
        )

    def can_create(
        self,
        class_id: str,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Check whether the provider may create an object of the class.
        """

        return self._can_apply_any_rule(
            self.rights.create_rules(class_id),
            context,
        )

    def can_update(
        self,
        class_id: str,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Check whether the provider may update an object of the class.
        """

        return self._can_update(
            class_id,
            context,
            visited=(),
        )

    def _can_update(
        self,
        class_id: str,
        context: RightsEvaluationContext,
        visited: tuple[str, ...],
    ) -> bool:
        """
        Recursive update-right evaluation.

        Evaluation order:

        1. Direct class update rules.
        2. Derived rights.
        3. Subclass rights.

        `visited` prevents infinite loops in cyclic configurations.
        """

        if class_id in visited:
            return False

        next_visited = visited + (class_id,)

        if self._can_apply_any_rule(
            self.rights.update_rules(
                class_id,
            ),
            context,
        ):
            return True

        if self._can_update_via_derived_rights(
            class_id,
            context,
            visited=next_visited,
        ):
            return True

        return self._can_update_via_subclass_rights(
            class_id,
            context,
            visited=next_visited,
        )

    def _can_update_via_derived_rights(
        self,
        class_id: str,
        context: RightsEvaluationContext,
        visited: tuple[str, ...],
    ) -> bool:
        """
        Check whether update rights may be inherited from related objects.
        """

        derived = self._resolve_derived_rights(
            class_id,
            context,
        )

        for related_object in derived.remote_objects:
            current = self.relation_lookup.current_object(
                related_object,
            )

            if current is None:
                continue

            related_values = {}

            for key, value in current.identity.attributes.items():
                related_values[key] = value

            for key, value in current.values.items():
                related_values[key] = value

            related_context = RightsEvaluationContext(
                dataowner_oid=context.dataowner_oid,
                provider_oid=context.provider_oid,
                operation=context.operation,
                old_values=related_values,
                new_values={},
                context_values=context.context_values,
            )

            if self._can_update(
                related_object.class_id,
                related_context,
                visited=visited,
            ):
                return True

        return False

    def can_delete(
        self,
        class_id: str,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Check whether the provider may delete an object of the class.
        """

        return self._can_apply_any_rule(
            self.rights.delete_rules(class_id),
            context,
        )

    def _can_apply_any_rule(
        self,
        rules: tuple[Rule, ...],
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Return true if at least one rule grants access.
        """

        return any(
            self.can_apply_rule(
                rule,
                context,
            )
            for rule in rules
        )

    def can_apply_rule(
        self,
        rule: Rule,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Dispatch rule evaluation by concrete rule type.
        """

        if isinstance(rule, PrivilegeRule):
            return self.can_apply_privilege_rule(
                rule,
                context,
            )

        if isinstance(rule, OwnershipRule):
            return self.can_apply_ownership_rule(
                rule,
                context,
            )

        raise TypeError(f"Unsupported rule type: {type(rule)!r}")

    def can_apply_privilege_rule(
        self,
        rule: PrivilegeRule,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Evaluate a privilege-based rule.

        If the rule has a condition, the condition must match before
        privileges are checked.
        """

        if rule.when is not None:
            if not self.conditions.evaluate(
                rule.when,
                self._condition_context(context),
            ):
                return False

        return any(
            self.provider.has_privilege(
                context.dataowner_oid,
                privilege,
            )
            for privilege in rule.privileges
        )

    def can_apply_ownership_rule(
        self,
        rule: OwnershipRule,
        context: RightsEvaluationContext,
    ) -> bool:
        """
        Evaluate an ownership rule.

        Ownership semantics:

        - INSERT: check ownership against submitted/new values.
        - UPDATE: check ownership against existing/old values.
        - DELETE: check ownership against existing/old values.

        This prevents a provider from passing ownership validation by
        changing the ownership attribute to themselves during an update.
        """

        if context.operation == ChangeOperation.INSERT:
            values = context.new_values
        else:
            values = context.old_values

        actual_owner = values.get(
            rule.attribute,
        )

        if actual_owner is None:
            return False

        return str(actual_owner) == str(context.provider_oid)

    def _condition_context(
        self,
        context: RightsEvaluationContext,
    ) -> ConditionEvaluationContext:
        """
        Convert a rights evaluation context into a condition evaluation
        context.
        """

        if context.operation == ChangeOperation.INSERT:
            local_values = context.new_values
        else:
            local_values = context.old_values

        return ConditionEvaluationContext(
            local_values=local_values,
            remote_values={},
            context_values={
                **context.context_values,
                "provider_oid": context.provider_oid,
                "dataowner_oid": context.dataowner_oid,
            },
        )

    def _can_update_via_subclass_rights(
        self,
        class_id: str,
        context: RightsEvaluationContext,
        visited: tuple[str, ...] = (),
    ) -> bool:
        """
        Check whether update rights may be inherited from subclasses.

        A parent class may opt into subclass-based rights evaluation via
        `rights_from_subclass`.
        """

        subclasses = self.subclass_rights.try_subclasses(
            class_id,
        )

        if not subclasses:
            return False

        return any(
            self._can_update(
                subclass_id,
                context,
                visited=visited,
            )
            for subclass_id in subclasses
        )

    def _resolve_derived_rights(
        self,
        class_id: str,
        context: RightsEvaluationContext,
    ) -> CanonicalDerivedRights:
        definitions = self.derived_rights.try_derived_rights(
            class_id,
        )

        if not definitions:
            return CanonicalDerivedRights()

        local_object = CanonicalObjectIdentity(
            class_id=class_id,
            attributes={
                key: value
                for key, value in {
                    **context.old_values,
                    **context.new_values,
                }.items()
                if value is not None
            },
        )

        remote_objects: list[CanonicalObjectIdentity] = []

        for relation in definitions:
            try:
                value = local_object.attributes[relation.local_attribute]
            except KeyError:
                continue

            remote_objects.extend(
                self.relation_lookup.canonical_objects(
                    local_class_id=class_id,
                    related_class_id=relation.class_id,
                    local_attribute=relation.local_attribute,
                    related_attribute=relation.remote_attribute,
                    value=value,
                )
            )

        return CanonicalDerivedRights(
            local_objects=(local_object,),
            remote_objects=tuple(
                remote_objects,
            ),
        )

    def _has_privilege(
        self,
        required: frozenset[PrivilegeId],
        context: RightsEvaluationContext,
    ) -> bool:
        if ALL_PRIVILEGES in required:
            return True

        return any(
            self.provider.has_privilege(
                context.dataowner_oid,
                privilege,
            )
            for privilege in required
        )
