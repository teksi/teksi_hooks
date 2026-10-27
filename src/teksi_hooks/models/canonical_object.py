from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, NewType
from uuid import UUID, uuid5


class TeksiModelNamespaces(Enum):
    """
    Stable identifiers for canonical infrastructure models.

    Member names are Python identifiers. The tuple contains the stable
    external model key and its persisted UUID.
    """

    WASTEWATER = (
        "wastewater",
        UUID(
            "37215468-fbf1-463b-be5b-38f95f39e52e",
        ),
    )
    PROTECTION_TUBE = (
        "protection_tube",
        UUID(
            "7c3d0a0e-3808-4a66-b9dc-3a98951fb626",
        ),
    )
    CABLE = (
        "cable",
        UUID(
            "e1f6dd3b-8c31-4cd2-8ca1-d5688c81926c",
        ),
    )

    def __init__(
        self,
        identifier: str,
        model_uuid: UUID,
    ) -> None:
        self.identifier = identifier
        self.model_uuid = model_uuid

    @classmethod
    def from_identifier(
        cls,
        identifier: str,
    ) -> TeksiModelNamespaces:
        """
        Return the canonical model matching an external identifier.
        """

        for model in cls:
            if model.identifier == identifier:
                return model

        raise ValueError(f"Unknown canonical model identifier: {identifier!r}.")


class CanonicalGeometryFamily(
    StrEnum,
):
    """
    Broad geometry families supported by review artifacts.

    The family describes the storage and rendering category, not the exact
    geometry subtype. For example, ``LINESTRING``, ``CIRCULARSTRING``,
    ``COMPOUNDCURVE``, and ``MULTICURVE`` as well as their counterparts
    with Z or M values all belong to ``LINE``. Module-specific interpreters
    may limit the allowed inputs by i.e. dropping M support.
    """

    POINT = "point"

    LINE = "line"

    POLYGON = "polygon"


@dataclass(slots=True, frozen=True)
class CanonicalObjectIdentity:
    """
    Canonical identity of an object.
    """

    class_id: str = field(
        metadata={"doc": ("Canonical class identifier.")},
    )

    attributes: Mapping[str, Any] = field(
        metadata={"doc": ("Attributes uniquely identifying the object.")},
    )

    def class_uid(
        self,
        namespace: TeksiModelNamespaces,
    ) -> UUID:
        """
        Return the stable semantic UUID of the canonical class.

        The namespace must be registered in TeksiModelNamespaces.
        """

        return uuid5(
            namespace.model_uuid,
            f"class:{self.class_id}",
        )

    def key(self) -> tuple:
        """
        Return the a tuple of class ID and attribute mapping items.
        """
        return (
            self.class_id,
            tuple(
                sorted(
                    self.attributes.items(),
                )
            ),
        )


@dataclass(slots=True, frozen=True)
class CanonicalObject:
    identity: CanonicalObjectIdentity = field(
        metadata={"doc": ("Canonical object identity.")},
    )

    values: Mapping[str, Any] = field(
        default_factory=dict,
        metadata={"doc": ("Canonical attribute values.")},
    )

    last_modification: datetime | None = field(
        default=None,
        metadata={"doc": ("Last modification snapshot.")},
    )


@dataclass(slots=True, frozen=True)
class CanonicalIdentityMapping:
    """
    Mapping from source object identity to canonical object identity.
    """

    source_attribute: str = field(
        metadata={"doc": ("Source object identity.")},
    )
    canonical_attribute: str = field(
        metadata={"doc": ("Canonical object identity.")},
    )


LanguageCode = NewType(
    "LanguageCode",
    str,
)
"""
BCP-style or application-supported language code.

Examples:
    LanguageCode("de")
    LanguageCode("fr")
"""


@dataclass(slots=True, frozen=True)
class LocalizedMetadata:
    """
    Generic localized metadata.

    This model is intentionally reusable for classes, attributes and values.
    """

    names: dict[
        str,
        str,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Localized technical names keyed by language code. "
                "Examples: {'de': 'Absperr_Drosselorgan'}, "
                "{'fr': '...'}."
            )
        },
    )

    display_names: dict[
        str,
        str,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Localized technical names keyed by language code. "
                "Examples: {'de': 'Absperr_Drosselorgan'}, "
                "{'fr': '...'}."
            )
        },
    )

    def name(
        self,
        language: str,
    ) -> str | None:
        """
        Return the localized technical name for a language.
        """

        return self.names.get(
            language,
        )

    def display_name(
        self,
        language: str,
    ) -> str | None:
        """
        Return the localized display name for a language.
        Defaults to technical name if no display name is found.
        """

        name = self.display_names.get(
            language,
        )

        if not name:
            name = self.names.get(
                language,
            )
        return name


@dataclass(slots=True, frozen=True)
class CanonicalModelElementMetadata:
    """
    Base metadata for a canonical TEKSI Wastewater model element.

    The concrete subclass determines the element level:

    - class
    - attribute
    - value-list value
    """

    source_id: int = field(
        metadata={
            "doc": (
                "Numeric source identifier, i.e. from the corresponding "
                "sys dictionary table. The meaning is scoped by the "
                "concrete metadata level."
            )
        },
    )

    identifier: str = field(
        metadata={
            "doc": (
                "Canonical string identifier for this model element. The "
                "meaning is scoped by the concrete metadata level."
            )
        },
    )

    localized: LocalizedMetadata = field(
        default_factory=LocalizedMetadata,
        metadata={"doc": ("Localized technical names for this model element.")},
    )


@dataclass(slots=True, frozen=True)
class CanonicalClassMetadata(CanonicalModelElementMetadata):
    """
    Canonical metadata for a TEKSI class/table.

    source_id:
        table.id

    identifier:
        txx_sys.dictionary_od_table.tablename
    """


@dataclass(slots=True, frozen=True)
class CanonicalAttributeMetadata(CanonicalModelElementMetadata):
    """
    Canonical metadata for a TEKSI attribute/field.

    source_id:
        txx_sys.dictionary_od_field.attribute_id

    identifier:
        txx_sys.dictionary_od_field.field_name
    """

    field_datatype: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Source field datatype from canonical metadata. For TEKSI "
                "Wastewater dictionary metadata this corresponds to "
                "txx_sys.dictionary_od_field.field_datatype. Geometry "
                "attributes are identified with field_datatype='geometry'."
            )
        },
    )


@dataclass(slots=True, frozen=True, kw_only=True)
class CanonicalGeometryMetadata(
    CanonicalAttributeMetadata,
):
    """
    Canonical metadata for one physical geometry attribute.

    The metadata describes the executable geometry column exposed by the
    canonical model. Its identifier is the physical canonical attribute name,
    such as ``area_geometry`` or ``progression_geometry``.

    Semantic and localized metadata may originate from a canonical dictionary.
    Physical geometry properties normally originate from database reflection
    or the PostGIS ``geometry_columns`` metadata view.
    """

    geometry_type: str = field(
        metadata={
            "doc": (
                "Declared geometry subtype, such as POINT, LINESTRING, "
                "COMPOUNDCURVE, POLYGON, or CURVEPOLYGON. Coordinate "
                "dimension is represented separately."
            )
        },
    )

    family: CanonicalGeometryFamily = field(
        metadata={
            "doc": (
                "Broad point, line, or polygon family of the geometry. "
                "The family is independent of the exact geometry subtype "
                "and coordinate dimension."
            )
        },
    )

    coordinate_dimension: int = field(
        metadata={
            "doc": (
                "Declared coordinate dimension reported by the canonical "
                "spatial database metadata."
            )
        },
    )

    srid: int = field(
        metadata={
            "doc": (
                "Spatial reference identifier declared for the canonical "
                "geometry attribute."
            )
        },
    )

    def __post_init__(
        self,
    ) -> None:
        """
        Validate and normalize geometry metadata.
        """

        if (
            not isinstance(
                self.geometry_type,
                str,
            )
            or not self.geometry_type.strip()
        ):
            raise ValueError("Canonical geometry type must be a non-empty string.")

        object.__setattr__(
            self,
            "geometry_type",
            self.geometry_type.strip().upper(),
        )

        if not isinstance(
            self.family,
            CanonicalGeometryFamily,
        ):
            try:
                family = CanonicalGeometryFamily(
                    self.family,
                )

            except (
                TypeError,
                ValueError,
            ) as exception:
                raise ValueError(
                    f"Unsupported canonical geometry family {self.family!r}."
                ) from exception

            object.__setattr__(
                self,
                "family",
                family,
            )

        if (
            not isinstance(
                self.coordinate_dimension,
                int,
            )
            or self.coordinate_dimension <= 0
        ):
            raise ValueError(
                "Canonical geometry coordinate dimension must be a positive integer."
            )

        if not isinstance(
            self.srid,
            int,
        ):
            raise TypeError("Canonical geometry SRID must be an integer.")

        expected_datatype = f"geometry({self.geometry_type.lower()})"

        if self.field_datatype is None:
            object.__setattr__(
                self,
                "field_datatype",
                expected_datatype,
            )


@dataclass(slots=True, frozen=True)
class CanonicalValueMetadata(CanonicalModelElementMetadata):
    """
    Canonical metadata for a TEKSI value-list value.

    source_id:
        txx_sys.dictionary_od_values.value_id

    identifier:
        txx_sys.dictionary_od_values.value_name
    """


@dataclass(slots=True, frozen=True)
class CanonicalModelMetadata:
    """
    Aggregate canonical metadata for TEKSI classes, attributes and
    values.

    This is intentionally a data-only model. Lookup behavior belongs to
    CanonicalModelCapability implementations.
    """

    classes: dict[
        str,
        CanonicalClassMetadata,
    ] = field(
        default_factory=dict,
        metadata={"doc": ("Class metadata keyed by canonical class_id.")},
    )

    attributes: dict[
        tuple[
            str,
            str,
        ],
        CanonicalAttributeMetadata,
    ] = field(
        default_factory=dict,
        metadata={"doc": ("Attribute metadata keyed by (class_id, attribute_id).")},
    )

    values: dict[
        tuple[
            str,
            str,
            str,
        ],
        CanonicalValueMetadata,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": ("Value metadata keyed by (class_id, attribute_id, value_id).")
        },
    )
