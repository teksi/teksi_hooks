from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from ..capabilities.mapping import (
    ImplicitModelMappingCapability,
)
from ..models.canonical_object import (
    CanonicalIdentityMapping,
)
from ..models.mapping import (
    AttributeMapping,
    ClassMapping,
    ModelMapping,
    MappingDefaults,
)


@dataclass(slots=True, frozen=True)
class ImplicitModelMappingResolver:
    """
    Build the implicit SSOT ModelMapping from dictionary metadata.

    The dictionary capability exposes source INTERLIS identifiers and their
    canonical TEKSI counterparts. This resolver converts those lookup records
    into the same ModelMapping structure used by explicit YAML mappings.

    The resolved mapping is marked as SSOT because dictionary metadata
    describes the canonical DSS source-model correspondence.

    Explicit mappings remain separate and may override or supplement this
    mapping through EffectiveModelMappingCapability.
    """

    dictionary: ImplicitModelMappingCapability

    source_identity_attribute: str = "obj_id"

    canonical_identity_attribute: str = "obj_id"

    def resolve(
        self,
    ) -> ModelMapping:
        """
        Return the resolved implicit SSOT model mapping.

        Raises
        ------
        ValueError
            If dictionary metadata contains empty identifiers, duplicate
            source definitions, or attribute mappings for unknown source
            classes.
        """

        default_identity = CanonicalIdentityMapping(
            source_attribute=self.source_identity_attribute,
            canonical_attribute=self.canonical_identity_attribute,
        )

        classes = {
            ili_class_name: self._class_mapping(
                ili_class_name=ili_class_name,
                canonical_class_id=canonical_class_id,
                default_identity=default_identity,
            )
            for (
                ili_class_name,
                canonical_class_id,
            ) in self._validated_table_mappings()
        }

        self._assert_no_orphan_attribute_mappings(
            known_class_ids=frozenset(
                classes,
            ),
        )

        return ModelMapping(
            classes=classes,
            defaults=MappingDefaults(
                identity=default_identity,
            ),
            is_ssot=True,
        )

    def _class_mapping(
        self,
        *,
        ili_class_name: str,
        canonical_class_id: str,
        default_identity: CanonicalIdentityMapping,
    ) -> ClassMapping:
        """
        Build the implicit mapping for one source class.
        """

        return ClassMapping(
            canonical_class_id=canonical_class_id,
            identities={
                canonical_class_id: default_identity,
            },
            attributes=self._attributes_for_class(
                ili_class_name=ili_class_name,
            ),
            relations={},
            function=None,
        )

    def _attributes_for_class(
        self,
        *,
        ili_class_name: str,
    ) -> dict[
        str,
        AttributeMapping,
    ]:
        """
        Return implicit attribute mappings for one source class.
        """

        attributes: dict[
            str,
            AttributeMapping,
        ] = {}

        for (
            source_class_id,
            source_attribute_id,
        ), (
            canonical_class_id,
            canonical_attribute_id,
        ) in self.dictionary.attribute_mapping.items():
            if source_class_id != ili_class_name:
                continue

            source_attribute_id = self._required_identifier(
                source_attribute_id,
                context=(f"Implicit source attribute for class {ili_class_name!r}"),
            )

            canonical_class_id = self._required_identifier(
                canonical_class_id,
                context=(
                    "Implicit canonical class for "
                    f"{ili_class_name!r}."
                    f"{source_attribute_id!r}"
                ),
            )

            canonical_attribute_id = self._required_identifier(
                canonical_attribute_id,
                context=(
                    "Implicit canonical attribute for "
                    f"{ili_class_name!r}."
                    f"{source_attribute_id!r}"
                ),
            )

            if source_attribute_id in attributes:
                raise ValueError(
                    "Duplicate implicit attribute mapping for "
                    f"{ili_class_name!r}."
                    f"{source_attribute_id!r}."
                )

            attributes[source_attribute_id] = AttributeMapping(
                canonical_class_id=canonical_class_id,
                canonical_attr_id=canonical_attribute_id,
                value_list=None,
            )

        return attributes

    def _validated_table_mappings(
        self,
    ) -> tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]:
        """
        Return validated and deterministically ordered table mappings.
        """

        mappings: list[
            tuple[
                str,
                str,
            ]
        ] = []

        for (
            ili_class_name,
            canonical_class_id,
        ) in self.dictionary.table_mapping.items():
            ili_class_name = self._required_identifier(
                ili_class_name,
                context="Implicit source class identifier",
            )

            canonical_class_id = self._required_identifier(
                canonical_class_id,
                context=(f"Implicit canonical class identifier for {ili_class_name!r}"),
            )

            mappings.append(
                (
                    ili_class_name,
                    canonical_class_id,
                )
            )

        mappings.sort(
            key=lambda mapping: mapping[0],
        )

        return tuple(
            mappings,
        )

    def _assert_no_orphan_attribute_mappings(
        self,
        *,
        known_class_ids: frozenset[str],
    ) -> None:
        """
        Reject attribute mappings whose source class has no table mapping.
        """

        orphan_class_ids = frozenset(
            source_class_id
            for (
                source_class_id,
                _source_attribute_id,
            ) in self.dictionary.attribute_mapping
            if source_class_id not in known_class_ids
        )

        if orphan_class_ids:
            raise ValueError(
                "Implicit attribute mappings refer to source classes "
                "without table mappings: "
                f"{tuple(sorted(orphan_class_ids))!r}."
            )

    def _required_identifier(
        self,
        value: object,
        *,
        context: str,
    ) -> str:
        """
        Validate and return one non-empty mapping identifier.
        """

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(f"{context} must be a string, got {type(value)!r}.")

        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{context} must not be empty.")

        return normalized


@dataclass(slots=True, frozen=True)
class ModelMappingInheritanceResolver:
    """
    Resolve inheritance between named model mappings.

    This resolver combines parsed model declarations. It does not inspect
    source relations and does not apply conditional defaults to concrete
    source classes.

    Parent definitions are inherited first. Child definitions with the same
    key replace the corresponding parent definitions.
    """

    mappings: Mapping[
        str,
        ModelMapping,
    ]

    def resolve(
        self,
        model_id: str,
    ) -> ModelMapping:
        """
        Return one inheritance-resolved model mapping.
        """

        return self._resolve(
            model_id=model_id,
            resolving=(),
            cache={},
        )

    def resolve_all(
        self,
    ) -> dict[
        str,
        ModelMapping,
    ]:
        """
        Return all model mappings with inheritance resolved.
        """

        cache: dict[
            str,
            ModelMapping,
        ] = {}

        return {
            model_id: self._resolve(
                model_id=model_id,
                resolving=(),
                cache=cache,
            )
            for model_id in self.mappings
        }

    def _resolve(
        self,
        *,
        model_id: str,
        resolving: tuple[
            str,
            ...,
        ],
        cache: dict[
            str,
            ModelMapping,
        ],
    ) -> ModelMapping:
        cached = cache.get(
            model_id,
        )

        if cached is not None:
            return cached

        if model_id in resolving:
            cycle_start = resolving.index(
                model_id,
            )

            cycle = (
                *resolving[cycle_start:],
                model_id,
            )

            raise ValueError(
                "Model mapping inheritance cycle: "
                + " -> ".join(
                    cycle,
                )
            )

        try:
            child = self.mappings[model_id]
        except KeyError as exception:
            raise KeyError(f"Unknown model mapping {model_id!r}.") from exception

        parent_id = child.defaults.inherit_from

        if parent_id is None:
            resolved = self._without_inheritance(
                child,
            )
        else:
            if parent_id not in self.mappings:
                raise KeyError(
                    f"Model mapping {model_id!r} inherits unknown model {parent_id!r}."
                )

            parent = self._resolve(
                model_id=parent_id,
                resolving=(
                    *resolving,
                    model_id,
                ),
                cache=cache,
            )

            resolved = self._merge(
                parent=parent,
                child=child,
            )

        cache[model_id] = resolved

        return resolved

    def _merge(
        self,
        *,
        parent: ModelMapping,
        child: ModelMapping,
    ) -> ModelMapping:
        """
        Merge one child mapping over its resolved parent.
        """

        defaults = self._merge_defaults(
            parent=parent.defaults,
            child=child.defaults,
        )

        classes = self._merge_classes(
            parent=parent.classes,
            child=child.classes,
        )

        return ModelMapping(
            defaults=defaults,
            classes=classes,
            is_ssot=child.is_ssot,
            languages=(child.languages if child.languages else parent.languages),
        )

    def _merge_defaults(
        self,
        *,
        parent: MappingDefaults,
        child: MappingDefaults,
    ) -> MappingDefaults:
        """
        Merge model defaults.

        Child keyed definitions replace parent definitions with the same key.
        """

        return MappingDefaults(
            identity=child.identity,
            identities={
                **parent.identities,
                **child.identities,
            },
            attributes={
                **parent.attributes,
                **child.attributes,
            },
            relations={
                **parent.relations,
                **child.relations,
            },
            inherit_from=None,
        )

    def _merge_classes(
        self,
        *,
        parent: Mapping[
            str,
            ClassMapping,
        ],
        child: Mapping[
            str,
            ClassMapping,
        ],
    ) -> dict[
        str,
        ClassMapping,
    ]:
        """
        Merge classes with complete child-class replacement.

        A child class declaration replaces the inherited class declaration
        having the same source class identifier.
        """

        return {
            **parent,
            **child,
        }

    def _without_inheritance(
        self,
        mapping: ModelMapping,
    ) -> ModelMapping:
        """
        Return a root mapping with its inheritance marker removed.
        """

        defaults = mapping.defaults

        return ModelMapping(
            defaults=MappingDefaults(
                identity=defaults.identity,
                identities=dict(
                    defaults.identities,
                ),
                attributes=dict(
                    defaults.attributes,
                ),
                relations=dict(
                    defaults.relations,
                ),
                inherit_from=None,
            ),
            classes=dict(
                mapping.classes,
            ),
            is_ssot=mapping.is_ssot,
            languages=mapping.languages,
        )
