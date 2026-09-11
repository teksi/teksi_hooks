from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models.canonical_object import (
    CanonicalIdentityMapping,
)
from ..models.mapping import (
    AttributeMapping,
    ClassMapping,
    ModelMapping,
    RelationMapping,
    ValueMapping,
)


class ModelMappingLookupCapability(Protocol):
    """
    Provide runtime lookup access to one resolved model mapping.

    Implementations may expose explicitly configured mappings, mappings
    derived implicitly from metadata, or a composition of both.
    """

    def class_definition(
        self,
        class_id: str,
    ) -> ClassMapping:
        """
        Return the mapping for one source-model class.
        """

        ...

    def try_class_definition(
        self,
        class_id: str,
    ) -> ClassMapping | None:
        """
        Return the mapping for one source-model class if available.
        """

        ...

    def attribute_definition(
        self,
        class_id: str,
        attribute_name: str,
    ) -> AttributeMapping:
        """
        Return the mapping for one source-model attribute.
        """

        ...

    def try_attribute_definition(
        self,
        class_id: str,
        attribute_name: str,
    ) -> AttributeMapping | None:
        """
        Return the mapping for one source-model attribute if available.
        """

        ...

    def value_mapping(
        self,
        class_id: str,
        attribute_name: str,
        value: str,
    ) -> ValueMapping:
        """
        Return the static mapping for one source-model value.
        """

        ...

    def try_value_mapping(
        self,
        class_id: str,
        attribute_name: str,
        value: str,
    ) -> ValueMapping | None:
        """
        Return the static mapping for one source-model value if available.
        """

        ...

    def identity_definition(
        self,
        class_id: str,
        canonical_class_id: str,
    ) -> CanonicalIdentityMapping:
        """
        Return the resolved identity for one canonical target class.
        """

        ...

    def try_identity_definition(
        self,
        class_id: str,
        canonical_class_id: str,
    ) -> CanonicalIdentityMapping | None:
        """
        Return the resolved identity for one target class if available.
        """

        ...

    def relation_definition(
        self,
        class_id: str,
        relation_id: str,
    ) -> RelationMapping:
        """
        Return the resolved mapping for one canonical relation.
        """

        ...

    def try_relation_definition(
        self,
        class_id: str,
        relation_id: str,
    ) -> RelationMapping | None:
        """
        Return the resolved relation mapping if available.
        """

        ...

    @property
    def is_ssot(
        self,
    ) -> bool:
        """
        Return whether the mapping represents a source-of-truth model.
        """

        ...


@dataclass(slots=True, frozen=True)
class ModelMappingCapability:
    """
    Provide runtime lookup access to one resolved `ModelMapping`.

    The model mapping describes how one source model maps to the canonical
    internal model. Model inheritance, model defaults, localized source
    identifiers and conditional default attributes must already be resolved
    before this capability is created.

    Existing class, attribute and value lookup methods remain available for
    compatibility with current mapping consumers.
    """

    mapping: ModelMapping

    def class_definition(
        self,
        class_id: str,
    ) -> ClassMapping:
        """
        Return the mapping for a source-model class.

        Parameters
        ----------
        class_id:
            Resolved source-model class identifier.

        Raises
        ------
        KeyError
            If the source class is unknown.
        """

        try:
            return self.mapping.classes[class_id]
        except KeyError as exception:
            raise KeyError(f"Unknown class: {class_id!r}.") from exception

    def try_class_definition(
        self,
        class_id: str,
    ) -> ClassMapping | None:
        """
        Return a class mapping if available.
        """

        return self.mapping.classes.get(
            class_id,
        )

    def attribute_definition(
        self,
        class_id: str,
        attribute_name: str,
    ) -> AttributeMapping:
        """
        Return the mapping for a source-model attribute.

        Parameters
        ----------
        class_id:
            Resolved source-model class identifier.

        attribute_name:
            Source-model runtime attribute identifier.

        Raises
        ------
        KeyError
            If the class or attribute is unknown.
        """

        class_mapping = self.class_definition(
            class_id,
        )

        try:
            return class_mapping.attributes[attribute_name]
        except KeyError as exception:
            raise KeyError(
                f"Unknown attribute {attribute_name!r} for class {class_id!r}."
            ) from exception

    def try_attribute_definition(
        self,
        class_id: str,
        attribute_name: str,
    ) -> AttributeMapping | None:
        """
        Return an attribute mapping if available.
        """

        class_mapping = self.try_class_definition(
            class_id,
        )

        if class_mapping is None:
            return None

        return class_mapping.attributes.get(
            attribute_name,
        )

    def value_mapping(
        self,
        class_id: str,
        attribute_name: str,
        value: str,
    ) -> ValueMapping:
        """
        Return the static mapping for a source-model value.

        Database-backed value-list translations are represented by
        `AttributeMapping.value_list` and are not returned by this method.

        Parameters
        ----------
        class_id:
            Resolved source-model class identifier.

        attribute_name:
            Source-model runtime attribute identifier.

        value:
            Source-model value.

        Raises
        ------
        KeyError
            If the class, attribute or value is unknown.
        """

        attribute_mapping = self.attribute_definition(
            class_id,
            attribute_name,
        )

        try:
            return attribute_mapping.values[value]
        except KeyError as exception:
            raise KeyError(
                "Unknown value "
                f"{value!r} for attribute "
                f"{class_id!r}.{attribute_name!r}."
            ) from exception

    def try_value_mapping(
        self,
        class_id: str,
        attribute_name: str,
        value: str,
    ) -> ValueMapping | None:
        """
        Return a static value mapping if available.

        Database-backed value-list translations are represented by
        `AttributeMapping.value_list` and are not returned by this method.
        """

        attribute_mapping = self.try_attribute_definition(
            class_id,
            attribute_name,
        )

        if attribute_mapping is None:
            return None

        return attribute_mapping.values.get(
            value,
        )

    def identity_definition(
        self,
        class_id: str,
        canonical_class_id: str,
    ) -> CanonicalIdentityMapping:
        """
        Return the resolved identity for a canonical target class.

        Parameters
        ----------
        class_id:
            Resolved source-model class identifier.

        canonical_class_id:
            Canonical target class identifier.

        Raises
        ------
        KeyError
            If the source class or target identity is unknown.
        """

        class_mapping = self.class_definition(
            class_id,
        )

        identity = class_mapping.identities.get(
            canonical_class_id,
        )

        if identity is not None:
            return identity

        if (
            class_mapping.canonical_class_id == canonical_class_id
            and class_mapping.identity is not None
        ):
            return class_mapping.identity

        raise KeyError(
            f"Unknown target identity {canonical_class_id!r} for class {class_id!r}."
        )

    def try_identity_definition(
        self,
        class_id: str,
        canonical_class_id: str,
    ) -> CanonicalIdentityMapping | None:
        """
        Return the resolved identity for a target class if available.
        """

        class_mapping = self.try_class_definition(
            class_id,
        )

        if class_mapping is None:
            return None

        identity = class_mapping.identities.get(
            canonical_class_id,
        )

        if identity is not None:
            return identity

        if class_mapping.canonical_class_id == canonical_class_id:
            return class_mapping.identity

        return None

    def relation_definition(
        self,
        class_id: str,
        relation_id: str,
    ) -> RelationMapping:
        """
        Return the resolved mapping for a canonical relation.

        Parameters
        ----------
        class_id:
            Resolved source-model class identifier.

        relation_id:
            Stable canonical relation identifier.

        Raises
        ------
        KeyError
            If the source class or relation is unknown.
        """

        class_mapping = self.class_definition(
            class_id,
        )

        try:
            return class_mapping.relations[relation_id]
        except KeyError as exception:
            raise KeyError(
                f"Unknown relation {relation_id!r} for class {class_id!r}."
            ) from exception

    def try_relation_definition(
        self,
        class_id: str,
        relation_id: str,
    ) -> RelationMapping | None:
        """
        Return a resolved relation mapping if available.
        """

        class_mapping = self.try_class_definition(
            class_id,
        )

        if class_mapping is None:
            return None

        return class_mapping.relations.get(
            relation_id,
        )

    @property
    def is_ssot(
        self,
    ) -> bool:
        """
        Return whether the mapping describes a source-of-truth model.
        """

        return self.mapping.is_ssot


class ImplicitModelMappingCapability(
    ModelMappingLookupCapability,
    Protocol,
):
    """
    Provide source-to-canonical mappings derived from metadata.

    Implementations may use dictionary metadata, generated model metadata,
    static reconciliation maps or another source. Database-backed
    implementations belong in the plugin layer.

    Returned class mappings must be resolved. Callers must not need to merge
    model defaults, inherited relations or localized source identifiers.
    """


@dataclass(slots=True, frozen=True)
class EffectiveModelMappingCapability:
    """
    Resolve effective source-to-canonical mappings.

    Explicit mappings take precedence at the most specific lookup level.
    Missing explicit classes, attributes, values, identities and relations
    fall back to the implicit mapping provider.

    A function-backed explicit class remains authoritative for projection.
    Consumers must inspect `ClassMapping.function` before requesting
    attribute mappings for that class.
    """

    explicit_mapping: ModelMappingCapability
    implicit_mapping: ImplicitModelMappingCapability | None = None

    def class_definition(
        self,
        class_id: str,
    ) -> ClassMapping:
        """
        Return the effective class mapping.
        """

        explicit = self.explicit_mapping.try_class_definition(
            class_id,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return self.explicit_mapping.class_definition(
                class_id,
            )

        return self.implicit_mapping.class_definition(
            class_id,
        )

    def try_class_definition(
        self,
        class_id: str,
    ) -> ClassMapping | None:
        """
        Return the effective class mapping if available.
        """

        explicit = self.explicit_mapping.try_class_definition(
            class_id,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return None

        return self.implicit_mapping.try_class_definition(
            class_id,
        )

    def attribute_definition(
        self,
        class_id: str,
        attribute_name: str,
    ) -> AttributeMapping:
        """
        Return the effective attribute mapping.
        """

        explicit = self.explicit_mapping.try_attribute_definition(
            class_id,
            attribute_name,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return self.explicit_mapping.attribute_definition(
                class_id,
                attribute_name,
            )

        return self.implicit_mapping.attribute_definition(
            class_id,
            attribute_name,
        )

    def try_attribute_definition(
        self,
        class_id: str,
        attribute_name: str,
    ) -> AttributeMapping | None:
        """
        Return the effective attribute mapping if available.
        """

        explicit = self.explicit_mapping.try_attribute_definition(
            class_id,
            attribute_name,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return None

        return self.implicit_mapping.try_attribute_definition(
            class_id,
            attribute_name,
        )

    def value_mapping(
        self,
        class_id: str,
        attribute_name: str,
        value: str,
    ) -> ValueMapping:
        """
        Return the effective static value mapping.
        """

        explicit = self.explicit_mapping.try_value_mapping(
            class_id,
            attribute_name,
            value,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return self.explicit_mapping.value_mapping(
                class_id,
                attribute_name,
                value,
            )

        return self.implicit_mapping.value_mapping(
            class_id,
            attribute_name,
            value,
        )

    def try_value_mapping(
        self,
        class_id: str,
        attribute_name: str,
        value: str,
    ) -> ValueMapping | None:
        """
        Return the effective static value mapping if available.
        """

        explicit = self.explicit_mapping.try_value_mapping(
            class_id,
            attribute_name,
            value,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return None

        return self.implicit_mapping.try_value_mapping(
            class_id,
            attribute_name,
            value,
        )

    def identity_definition(
        self,
        class_id: str,
        canonical_class_id: str,
    ) -> CanonicalIdentityMapping:
        """
        Return the effective target identity.
        """

        explicit = self.explicit_mapping.try_identity_definition(
            class_id,
            canonical_class_id,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return self.explicit_mapping.identity_definition(
                class_id,
                canonical_class_id,
            )

        return self.implicit_mapping.identity_definition(
            class_id,
            canonical_class_id,
        )

    def try_identity_definition(
        self,
        class_id: str,
        canonical_class_id: str,
    ) -> CanonicalIdentityMapping | None:
        """
        Return the effective target identity if available.
        """

        explicit = self.explicit_mapping.try_identity_definition(
            class_id,
            canonical_class_id,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return None

        return self.implicit_mapping.try_identity_definition(
            class_id,
            canonical_class_id,
        )

    def relation_definition(
        self,
        class_id: str,
        relation_id: str,
    ) -> RelationMapping:
        """
        Return the effective relation mapping.
        """

        explicit = self.explicit_mapping.try_relation_definition(
            class_id,
            relation_id,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return self.explicit_mapping.relation_definition(
                class_id,
                relation_id,
            )

        return self.implicit_mapping.relation_definition(
            class_id,
            relation_id,
        )

    def try_relation_definition(
        self,
        class_id: str,
        relation_id: str,
    ) -> RelationMapping | None:
        """
        Return the effective relation mapping if available.
        """

        explicit = self.explicit_mapping.try_relation_definition(
            class_id,
            relation_id,
        )

        if explicit is not None:
            return explicit

        if self.implicit_mapping is None:
            return None

        return self.implicit_mapping.try_relation_definition(
            class_id,
            relation_id,
        )

    @property
    def is_ssot(
        self,
    ) -> bool:
        """
        Return whether the explicit mapping is a source-of-truth mapping.
        """

        return self.explicit_mapping.is_ssot
