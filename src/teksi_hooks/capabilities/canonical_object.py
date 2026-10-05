from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models.canonical_object import (
    CanonicalAttributeMetadata,
    CanonicalClassMetadata,
    CanonicalModelMetadata,
    CanonicalObjectIdentity,
    CanonicalValueMetadata,
)


class CanonicalModelCapability(Protocol):
    """
    Capability for accessing canonical model metadata.

    Implementations may load metadata from database tables, YAML, JSON,
    generated metadata, or in-memory test data.
    """

    def canonical_model(
        self,
    ) -> CanonicalModelMetadata:
        """
        Return complete canonical model metadata.
        """

    def classes(
        self,
    ) -> dict[
        str,
        CanonicalClassMetadata,
    ]:
        """
        Return class metadata keyed by class_id.
        """

    def attributes(
        self,
        class_id: str | None = None,
    ) -> dict[
        tuple[
            str,
            str,
        ],
        CanonicalAttributeMetadata,
    ]:
        """
        Return attribute metadata keyed by (class_id, attribute_id).
        """

    def values(
        self,
        class_id: str | None = None,
        attribute_id: str | None = None,
    ) -> dict[
        tuple[
            str,
            str,
            str,
        ],
        CanonicalValueMetadata,
    ]:
        """
        Return value metadata keyed by (class_id, attribute_id, value_id).
        """

    def class_metadata(
        self,
        class_id: str,
    ) -> CanonicalClassMetadata | None:
        """
        Return metadata for one class.
        """

    def attribute_metadata(
        self,
        class_id: str,
        attribute_id: str,
    ) -> CanonicalAttributeMetadata | None:
        """
        Return metadata for one attribute.
        """

    def value_metadata(
        self,
        class_id: str,
        attribute_id: str,
        value_id: str,
    ) -> CanonicalValueMetadata | None:
        """
        Return metadata for one value.
        """

    def _identity_key(
        self,
        identity: CanonicalObjectIdentity,
    ) -> tuple:
        return (
            identity.class_id,
            tuple(
                sorted(
                    identity.attributes.items(),
                )
            ),
        )


@dataclass(slots=True, frozen=True)
class InMemoryCanonicalModelCapability(
    CanonicalModelCapability,
):
    """
    In-memory canonical model metadata provider.

    Useful for tests, examples and offline workflows.
    """

    metadata: CanonicalModelMetadata

    def canonical_model(
        self,
    ) -> CanonicalModelMetadata:
        return self.metadata

    def classes(
        self,
    ) -> dict[
        str,
        CanonicalClassMetadata,
    ]:
        return self.metadata.classes

    def attributes(
        self,
        class_id: str | None = None,
    ) -> dict[
        tuple[
            str,
            str,
        ],
        CanonicalAttributeMetadata,
    ]:
        if class_id is None:
            return self.metadata.attributes

        return {
            key: value
            for key, value in self.metadata.attributes.items()
            if key[0] == class_id
        }

    def values(
        self,
        class_id: str | None = None,
        attribute_id: str | None = None,
    ) -> dict[
        tuple[
            str,
            str,
            str,
        ],
        CanonicalValueMetadata,
    ]:
        return {
            key: value
            for key, value in self.metadata.values.items()
            if (class_id is None or key[0] == class_id)
            and (attribute_id is None or key[1] == attribute_id)
        }

    def class_metadata(
        self,
        class_id: str,
    ) -> CanonicalClassMetadata | None:
        return self.metadata.classes.get(
            class_id,
        )

    def attribute_metadata(
        self,
        class_id: str,
        attribute_id: str,
    ) -> CanonicalAttributeMetadata | None:
        return self.metadata.attributes.get(
            (
                class_id,
                attribute_id,
            )
        )

    def value_metadata(
        self,
        class_id: str,
        attribute_id: str,
        value_id: str,
    ) -> CanonicalValueMetadata | None:
        return self.metadata.values.get(
            (
                class_id,
                attribute_id,
                value_id,
            )
        )


@dataclass(slots=True, frozen=True)
class CanonicalGeometryCapability:
    """
    Metadata-driven helper for identifying canonical geometry attributes.

    Geometry identification is derived solely from canonical attribute
    metadata rather than naming conventions.
    """

    metadata: CanonicalModelMetadata

    def is_geometry_attribute(
        self,
        class_id: str,
        attribute_id: str,
    ) -> bool:
        """
        Return whether a canonical attribute represents geometry.
        """

        attribute = self.metadata.attributes.get(
            (
                class_id,
                attribute_id,
            )
        )

        if attribute is None:
            return False

        return self._is_geometry_datatype(
            attribute.field_datatype,
        )

    def geometry_attribute_names(
        self,
        class_id: str,
    ) -> tuple[str, ...]:
        """
        Return canonical geometry attribute identifiers for a class.
        """

        return tuple(
            attribute.identifier
            for (
                attribute_class_id,
                _,
            ), attribute in self.metadata.attributes.items()
            if attribute_class_id == class_id
            and self._is_geometry_datatype(
                attribute.field_datatype,
            )
        )

    def _is_geometry_datatype(
        self,
        field_datatype: str | None,
    ) -> bool:
        """
        Return whether a metadata datatype represents geometry.
        """

        if field_datatype is None:
            return False

        return field_datatype.strip().lower() == "geometry"
