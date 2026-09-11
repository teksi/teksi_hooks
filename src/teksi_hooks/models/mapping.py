from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .canonical_object import CanonicalIdentityMapping


@dataclass(slots=True, frozen=True)
class ValueMapping:
    """
    Map one source-model value to a canonical internal value.
    """

    canonical_value_id: int = field(
        metadata={
            "doc": (
                "Canonical value identifier. Corresponds to a value-list "
                "code or database value identifier."
            )
        },
    )
    value: str = field(
        metadata={
            "doc": (
                "Source-model value mapped to the canonical value. For a "
                "single-source-of-truth model, this may be the canonical "
                "English value associated with the canonical code."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ValueListMapping:
    """
    Describe a database-backed source-to-canonical value translation.
    """

    relation: str = field(
        metadata={
            "doc": (
                "Qualified database relation used for value translation. "
                "Example: "
                "`tww_vl.measure_category_import_rel_agxx`."
            )
        },
    )
    mapping_attribute: str = field(
        metadata={
            "doc": (
                "Relation attribute matched against the submitted "
                "source-model value. Example: `value_de`."
            )
        },
    )
    value_attribute: str = field(
        default="code",
        metadata={
            "doc": (
                "Relation attribute containing the resulting canonical "
                "value. Defaults to `code`."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ForeignKeyMapping:
    """
    Describe the canonical object referenced by a mapped attribute.

    This is used when the mapped canonical attribute stores a reference
    rather than a literal value.
    """

    referenced_class_id: str = field(
        metadata={
            "doc": (
                "Canonical identifier of the referenced class. Corresponds "
                "to a class or table in the internal semantic model."
            )
        },
    )
    referenced_attribute_id: str = field(
        default="obj_id",
        metadata={
            "doc": (
                "Canonical identifier of the referenced attribute. "
                "Defaults to the canonical object identifier `obj_id`."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class FunctionMapping:
    """
    Describe a database-backed mapping function.

    Function mappings handle source classes whose canonical effects cannot
    be represented by one-to-one attribute mappings.

    The configured function receives values from the source row and returns
    a complete canonical JSONB effect document. The result is authoritative
    and must not be supplemented with declarative attribute mappings.
    """

    schema: str = field(
        metadata={
            "doc": (
                "Database schema containing the mapping function. Example: `tww_app`."
            )
        },
    )
    name: str = field(
        metadata={
            "doc": (
                "Database function name implementing the mapping. Example: "
                "`fct_agxx_gepknoten_mapping_jsonb`."
            )
        },
    )
    parameters: Mapping[str, str] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Function parameter mappings keyed by database function "
                "parameter name. Values identify source-row expressions or "
                "source-model attributes. The special value `$row` passes "
                "the complete source row."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class AttributeMapping:
    """
    Map one source-model attribute to one canonical target attribute.

    Declarative attribute mappings intentionally support one canonical
    target. A source attribute requiring multiple canonical effects must use
    a function mapping instead.
    """

    canonical_class_id: str = field(
        metadata={
            "doc": ("Canonical class identifier containing the target attribute.")
        },
    )
    canonical_attr_id: str = field(
        metadata={
            "doc": ("Canonical attribute identifier receiving the mapped source value.")
        },
    )
    foreign_key: ForeignKeyMapping | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional reference metadata used when the canonical target "
                "attribute stores a foreign-key reference."
            )
        },
    )
    values: Mapping[str, ValueMapping] = field(
        default_factory=dict,
        metadata={
            "doc": ("Optional static value mappings keyed by source-model value.")
        },
    )
    value_list: ValueListMapping | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional database-backed value-list translation. The "
                "source value is matched using the configured mapping "
                "attribute and translated to the configured canonical "
                "value attribute."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class RelationMapping:
    """
    Map a canonical relation to a localized source-model relation.

    Canonical relation and target identifiers remain independent of the
    source-model language. Localized identifiers are exact executable
    source-model element identifiers and are not display labels.
    """

    referenced_class_id: str = field(
        metadata={
            "doc": (
                "Canonical identifier of the class referenced by the "
                "relation. Example: `organisation`."
            )
        },
    )
    referenced_attribute_id: str = field(
        default="obj_id",
        metadata={
            "doc": (
                "Canonical identifier of the referenced target attribute. "
                "Defaults to `obj_id`."
            )
        },
    )
    localisations: Mapping[str, str] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Exact source-model relation identifiers keyed by source "
                "language. Example: "
                "`{'de': 'DatenbewirtschafterRef'}`."
            )
        },
    )

    def source_identifier(
        self,
        language: str,
    ) -> str | None:
        """
        Return the exact source-model identifier for one language.
        """

        return self.localisations.get(
            language,
        )


@dataclass(slots=True, frozen=True)
class MappingDefaults:
    """
    Define mappings inherited by classes in one source model.
    """

    identity: CanonicalIdentityMapping = field(
        default_factory=lambda: CanonicalIdentityMapping(
            source_attribute="obj_id",
            canonical_attribute="obj_id",
        ),
        metadata={
            "doc": (
                "Default source-to-canonical identity mapping. Class-level "
                "target identities may override either attribute."
            )
        },
    )
    identities: Mapping[
        str,
        CanonicalIdentityMapping,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Default identity mappings keyed by canonical target class. "
                "An identity describes how effects address a target row and "
                "does not independently require that row to exist."
            )
        },
    )
    attributes: Mapping[str, AttributeMapping] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Default attribute mappings keyed by source-model runtime "
                "attribute identifier. A default mapping applies to a class "
                "only when that source class defines the source attribute."
            )
        },
    )
    relations: Mapping[str, RelationMapping] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Default canonical relation mappings keyed by stable "
                "canonical relation identifier."
            )
        },
    )
    inherit_from: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional source-model mapping identifier inherited by this "
                "model. Inherited defaults are resolved before local "
                "overrides. Mapping inheritance must be acyclic."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ClassMapping:
    """
    Map one source-model class to the canonical internal model.

    A class may use either a class-level function mapping or declarative
    attribute mappings. Function-backed mappings return a complete JSONB
    effect document.
    """

    canonical_class_id: str | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional primary canonical class identifier represented by "
                "the source class. This may be omitted for function-backed "
                "or extension-only mappings."
            )
        },
    )
    identity: CanonicalIdentityMapping | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional primary identity override for the class. Missing "
                "source or canonical identity attributes are inherited from "
                "the model defaults during mapping resolution."
            )
        },
    )
    identities: Mapping[
        str,
        CanonicalIdentityMapping | None,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Identity mappings keyed by canonical target class. A null "
                "mapping declares the target class while inheriting the "
                "complete model-default identity. A partial mapping may "
                "override the canonical or source identity attribute."
            )
        },
    )
    attributes: Mapping[str, AttributeMapping] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Declarative attribute mappings keyed by source runtime "
                "attribute identifier. For ili2pg imports this is the actual "
                "SQLAlchemy or ili2pg column name, which may differ from the "
                "original INTERLIS attribute name."
            )
        },
    )
    relations: Mapping[str, RelationMapping] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Class-specific canonical relation mappings keyed by stable "
                "canonical relation identifier. These mappings override "
                "model-default relations with the same identifier."
            )
        },
    )
    localisations: Mapping[str, str] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Exact source-model class identifiers keyed by source "
                "language. Values are executable model identifiers rather "
                "than translated display labels."
            )
        },
    )
    function: FunctionMapping | None = field(
        default=None,
        metadata={
            "doc": (
                "Optional database-backed class projection function. The "
                "function receives configured source-row values and returns "
                "the complete canonical JSONB effect document."
            )
        },
    )

    @property
    def is_function_backed(
        self,
    ) -> bool:
        """
        Return whether the class uses a database projection function.
        """

        return self.function is not None

    @property
    def is_attribute_backed(
        self,
    ) -> bool:
        """
        Return whether the class declares attribute mappings.
        """

        return bool(
            self.attributes,
        )

    def source_identifier(
        self,
        language: str,
    ) -> str | None:
        """
        Return the exact source-model class identifier for one language.
        """

        return self.localisations.get(
            language,
        )


@dataclass(slots=True, frozen=True)
class ModelMapping:
    """
    Describe how one source model maps to the canonical internal model.

    Source class, attribute and relation identifiers are scoped to this
    model and may be localized. Canonical class, attribute, relation and
    value identifiers remain independent of the source-model language.
    """

    defaults: MappingDefaults = field(
        default_factory=MappingDefaults,
        metadata={
            "doc": (
                "Default identities, attributes and relations inherited by "
                "classes in this source model."
            )
        },
    )
    classes: Mapping[str, ClassMapping] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Class mappings keyed by source-model class identifier or "
                "stable mapping identifier, according to the selected "
                "source-model mapping contract."
            )
        },
    )
    is_ssot: bool = field(
        default=False,
        metadata={
            "doc": (
                "Whether this model mapping describes a canonical "
                "single-source-of-truth model."
            )
        },
    )
    languages: frozenset[str] = field(
        default_factory=frozenset,
        metadata={
            "doc": (
                "Source languages explicitly supported by this model "
                "mapping. An unavailable requested language must not be "
                "silently replaced by another language."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ModelMappings:
    """
    Contain explicit mappings for all configured source models.
    """

    models: Mapping[str, ModelMapping] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Model mappings keyed by stable source-model mapping "
                "identifier. Example identifiers include `agxx`, "
                "`sia405_abwasser`, `dss` and `vsa_kek`."
            )
        },
    )


@dataclass(frozen=True)
class RelationContext:
    """
    Provide runtime context for one mapped relation.

    The context links a concrete SQLAlchemy ORM relation with the resolved
    semantic class mapping used by the diff and validation pipeline.
    """

    relation: type = field(
        metadata={"doc": ("SQLAlchemy ORM relation generated for the source model.")},
    )
    class_mapping: ClassMapping = field(
        metadata={
            "doc": (
                "Resolved mapping for the source-model class represented by "
                "the ORM relation."
            )
        },
    )
