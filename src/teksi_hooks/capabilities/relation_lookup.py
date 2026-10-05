from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)


class RelationLookupCapability(Protocol):
    """
    Capability providing canonical object relationship lookups.

    Implementations may use SQL, ORM models, in-memory objects, test fixtures,
    or plugin-specific adapters.

    RightsEvaluator only depends on this abstraction and remains
    implementation-independent.
    """

    def canonical_objects(
        self,
        *,
        local_class_id: str,
        related_class_id: str,
        local_attribute: str,
        related_attribute: str,
        value: Any,
    ) -> Sequence[CanonicalObjectIdentity]:
        """
        Return related objects matching the supplied join condition.

        Conceptually evaluates:

            local.<local_attribute>
                =
            related.<related_attribute>
        """

    def current_object(
        self,
        identity: CanonicalObjectIdentity,
    ) -> CanonicalObject | None:
        """
        Return the current canonical object or None if it no longer exists.
        """


@dataclass(slots=True, frozen=True)
class InMemoryRelationLookupCapability(RelationLookupCapability):
    """
    In-memory relation lookup implementation.

    This implementation is intended for tests, examples and small offline
    scenarios.

    All objects live in one object pool. This is important for recursive
    relation traversal, because an object found as the related object in one
    hop may become the local object in the next hop.

    Example:

        reach_point
            -> reach
                -> wastewater_structure

    In this chain, `reach` is first a related object, then a local object.
    """

    objects: tuple[CanonicalObject, ...] = field(
        default_factory=tuple,
        metadata={"doc": ("Canonical objects available for lookup.")},
    )

    @classmethod
    def from_sides(
        cls,
        *,
        local_objects: Sequence[CanonicalObject] = (),
        related_objects: Sequence[CanonicalObject] = (),
    ) -> InMemoryRelationLookupCapability:
        """
        Convenience constructor for tests that want to express local and
        related sides explicitly.

        The resulting lookup still uses one combined object pool so recursive
        relation traversal works correctly.
        """

        objects_by_identity = {
            cls._identity_key_static(
                obj.identity,
            ): obj
            for obj in (
                *local_objects,
                *related_objects,
            )
        }

        return cls(
            objects=tuple(
                objects_by_identity.values(),
            )
        )

    def canonical_objects(
        self,
        *,
        local_class_id: str,
        related_class_id: str,
        local_attribute: str,
        related_attribute: str,
        value: Any,
    ) -> Sequence[CanonicalObjectIdentity]:
        """
        Return related object identities matching the configured join.

        The local side must exist in the in-memory object pool. If no local
        object matches the supplied local class and local attribute value, no
        related objects are returned.
        """

        local_match_exists = any(
            obj.identity.class_id == local_class_id
            and self._attribute_value(
                obj,
                local_attribute,
            )
            == value
            for obj in self.objects
        )

        if not local_match_exists:
            return ()

        return tuple(
            obj.identity
            for obj in self.objects
            if obj.identity.class_id == related_class_id
            and self._attribute_value(
                obj,
                related_attribute,
            )
            == value
        )

    def current_object(
        self,
        identity: CanonicalObjectIdentity,
    ) -> CanonicalObject | None:
        """
        Return the current canonical object or None if it no longer exists.
        """

        expected_key = self._identity_key(
            identity,
        )

        for obj in self.objects:
            if (
                self._identity_key(
                    obj.identity,
                )
                == expected_key
            ):
                return obj

        return None

    def _attribute_value(
        self,
        obj: CanonicalObject,
        attribute_name: str,
    ) -> Any:
        """
        Return an attribute value from object values or identity attributes.

        Values are checked first because normal object attributes should
        override identity metadata where both exist.
        """

        if attribute_name in obj.values:
            return obj.values[attribute_name]

        return obj.identity.attributes.get(
            attribute_name,
        )

    def _identity_key(
        self,
        identity: CanonicalObjectIdentity,
    ) -> tuple:
        """
        Return a hashable identity key.
        """

        return self._identity_key_static(
            identity,
        )

    @staticmethod
    def _identity_key_static(
        identity: CanonicalObjectIdentity,
    ) -> tuple:
        """
        Return a hashable identity key.
        """

        return (
            identity.class_id,
            tuple(
                sorted(
                    identity.attributes.items(),
                )
            ),
        )
