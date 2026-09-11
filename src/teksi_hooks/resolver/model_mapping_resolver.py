from __future__ import annotations

from dataclasses import dataclass

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

    source_identity_attribute: str = "t_ili_tid"

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
