from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..models.canonical_object import (
    CanonicalIdentityMapping,
)
from ..models.mapping import (
    AttributeMapping,
    CanonicalViewMapping,
    CanonicalViewProjectionMapping,
    ClassMapping,
    MappingDefaults,
    ModelMapping,
    ProjectionReferenceDiscriminator,
    ProjectionReferenceMapping,
    RelationMapping,
    ValueListMapping,
)
from ..resolver.model_mapping_resolver import ModelMappingInheritanceResolver


@dataclass(slots=True)
class ModelMappingParser:
    """
    Parse source-model to canonical-model mapping definitions.

    A mapping document may contain several named source models under
    ``models``.

    Model definitions may contain:

    - model-level defaults;
    - model inheritance;
    - class-level canonical view projections;
    - class-level canonical identities;
    - direct attribute mappings;
    - source relation localisations;
    - value-list lookup definitions.

    This parser only converts YAML into mapping models. It does not:

    - inspect source-model classes;
    - apply conditional default attributes;
    - resolve explicit-before-implicit lookup precedence;
    - query value-list relations;
    - execute mapping modules;
    - produce canonical effects.

    Conditional defaults, such as mappings for ``letzte_aenderung_wi`` and
    ``letzte_aenderung_gep``, are retained in ``ModelMapping.defaults``.
    A later resolver applies them only to source classes containing the
    corresponding source attributes.
    """

    def parse_file(
        self,
        path: str | Path,
        *,
        model_id: str | None = None,
    ) -> ModelMapping:
        """
        Parse one model mapping from a YAML file.

        ``model_id`` may be omitted only when the file contains exactly one
        model.
        """

        mappings = self.parse_models_file(
            path,
        )
        resolved_mappings = ModelMappingInheritanceResolver(
            mappings=mappings
        ).resolve_all()

        return self._select_model(
            mappings=resolved_mappings,
            model_id=model_id,
        )

    def parse_models_file(
        self,
        path: str | Path,
    ) -> dict[str, ModelMapping]:
        """
        Parse all model mappings from a YAML file.
        """

        with open(
            path,
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(
                file,
            )

        return self.parse_models_dict(
            data or {},
        )

    def parse_dict(
        self,
        data: Mapping[
            str,
            Any,
        ],
        *,
        model_id: str | None = None,
    ) -> ModelMapping:
        """
        Parse and resolve one model mapping from a loaded YAML document.
        """

        mappings = self.parse_models_dict(
            data,
        )

        resolved_mappings = ModelMappingInheritanceResolver(
            mappings=mappings,
        ).resolve_all()

        return self._select_model(
            mappings=resolved_mappings,
            model_id=model_id,
        )

    def parse_models_dict(
        self,
        data: Mapping[str, Any],
    ) -> dict[str, ModelMapping]:
        """
        Parse every model mapping from an already loaded YAML document.
        """

        root = self._mapping(
            data,
            path="<root>",
        )

        raw_models = self._mapping(
            root.get(
                "models",
                {},
            ),
            path="models",
        )

        if not raw_models:
            raise ValueError(
                "Mapping document must define at least one model under `models`."
            )

        parsed = {
            self._string(
                model_id,
                path="models.<model_id>",
            ): self._parse_model(
                model_id=self._string(
                    model_id,
                    path="models.<model_id>",
                ),
                raw=self._mapping(
                    raw_model or {},
                    path=f"models.{model_id}",
                ),
            )
            for model_id, raw_model in raw_models.items()
        }

        self._validate_inheritance(
            mappings=parsed,
        )

        return parsed

    def _select_model(
        self,
        *,
        mappings: Mapping[str, ModelMapping],
        model_id: str | None,
    ) -> ModelMapping:
        """
        Select one parsed model mapping.
        """

        if model_id is not None:
            try:
                return mappings[model_id]
            except KeyError as exception:
                raise KeyError(
                    f"Unknown model mapping {model_id!r}. "
                    f"Available models: "
                    f"{tuple(sorted(mappings))!r}."
                ) from exception

        if len(mappings) == 1:
            return next(
                iter(
                    mappings.values(),
                )
            )

        raise ValueError(
            "model_id is required when the mapping file contains "
            f"multiple models. Available models: "
            f"{tuple(sorted(mappings))!r}."
        )

    def _parse_model(
        self,
        *,
        model_id: str,
        raw: Mapping[str, Any],
    ) -> ModelMapping:
        """
        Parse one model without resolving inheritance or defaults.
        """

        path = f"models.{model_id}"

        defaults = self._parse_defaults(
            raw.get(
                "defaults",
                {},
            ),
            path=f"{path}.defaults",
        )

        (
            projection_reference_defaults,
            projection_value_attribute_default,
            projection_mapping_attribute_default,
        ) = self._parse_projection_defaults(
            raw.get(
                "projection_defaults",
                {},
            ),
            path=f"{path}.projection_defaults",
        )

        classes = self._parse_classes(
            raw.get(
                "classes",
                {},
            ),
            default_identity=defaults.identity,
            projection_reference_defaults=(projection_reference_defaults),
            projection_value_attribute_default=(projection_value_attribute_default),
            projection_mapping_attribute_default=(projection_mapping_attribute_default),
            path=f"{path}.classes",
        )

        return ModelMapping(
            classes=classes,
            defaults=defaults,
            is_ssot=self._boolean(
                raw.get(
                    "is_ssot",
                    False,
                ),
                path=f"{path}.is_ssot",
            ),
        )

    def _parse_defaults(
        self,
        raw: Any,
        *,
        path: str,
    ) -> MappingDefaults:
        """
        Parse model-level defaults.

        Empty identity declarations inherit ``source_attribute`` and
        ``target_attribute`` from these defaults.
        """

        raw = self._mapping(
            raw or {},
            path=path,
        )

        source_attribute = self._optional_string(
            raw.get(
                "source_attribute",
            ),
            path=f"{path}.source_attribute",
            default="obj_id",
        )

        target_attribute = self._optional_string(
            raw.get(
                "target_attribute",
            ),
            path=f"{path}.target_attribute",
            default="obj_id",
        )

        default_identity = CanonicalIdentityMapping(
            source_attribute=source_attribute,
            canonical_attribute=target_attribute,
        )

        return MappingDefaults(
            inherit_from=self._optional_string(
                raw.get(
                    "inherit_from",
                ),
                path=f"{path}.inherit_from",
            ),
            identity=default_identity,
            identities=self._parse_identities(
                raw.get(
                    "identities",
                    {},
                ),
                default_identity=default_identity,
                path=f"{path}.identities",
            ),
            attributes=self._parse_attributes(
                raw.get(
                    "attributes",
                    {},
                ),
                path=f"{path}.attributes",
            ),
            relations=self._parse_relations(
                raw.get(
                    "relations",
                    {},
                ),
                default_target_attribute=target_attribute,
                path=f"{path}.relations",
            ),
        )

    def _parse_projection_defaults(
        self,
        raw: Any,
        *,
        path: str,
    ) -> tuple[
        dict[
            str,
            ProjectionReferenceMapping,
        ],
        str,
        str,
    ]:
        """
        Parse model-local defaults for projection-backed mappings.

        The returned defaults are applied while parsing the model's class
        projections. They are independent of declarative identities, attributes,
        and relations.

        Returns:

        - default projection references;
        - default canonical value attribute;
        - default lookup/mapping attribute.
        """

        defaults_data = self._mapping(
            raw or {},
            path=path,
        )

        unknown_keys = set(
            defaults_data,
        ) - {
            "references",
            "value_lists",
        }

        if unknown_keys:
            raise ValueError(
                f"{path} contains unsupported keys: {tuple(sorted(unknown_keys))!r}."
            )

        references = self._parse_projection_references(
            defaults_data.get(
                "references",
                {},
            ),
            path=f"{path}.references",
        )

        value_list_data = self._mapping(
            defaults_data.get(
                "value_lists",
                {},
            )
            or {},
            path=f"{path}.value_lists",
        )

        value_list_unknown_keys = set(
            value_list_data,
        ) - {
            "defaults",
        }

        if value_list_unknown_keys:
            raise ValueError(
                f"{path}.value_lists contains unsupported keys: "
                f"{tuple(sorted(value_list_unknown_keys))!r}."
            )

        lookup_defaults = self._mapping(
            value_list_data.get(
                "defaults",
                {},
            )
            or {},
            path=f"{path}.value_lists.defaults",
        )

        lookup_unknown_keys = set(
            lookup_defaults,
        ) - {
            "canonical_value_attribute",
            "lookup_value_attribute",
        }

        if lookup_unknown_keys:
            raise ValueError(
                f"{path}.value_lists.defaults contains unsupported "
                "keys: "
                f"{tuple(sorted(lookup_unknown_keys))!r}."
            )

        canonical_value_attribute = self._optional_string(
            lookup_defaults.get(
                "canonical_value_attribute",
            ),
            path=(f"{path}.value_lists.defaults.canonical_value_attribute"),
            default="code",
        )

        lookup_value_attribute = self._optional_string(
            lookup_defaults.get(
                "lookup_value_attribute",
            ),
            path=(f"{path}.value_lists.defaults.lookup_value_attribute"),
            default="value_de",
        )

        if canonical_value_attribute is None:
            raise ValueError(
                f"{path}.value_lists.defaults."
                "canonical_value_attribute must not be null."
            )

        if lookup_value_attribute is None:
            raise ValueError(
                f"{path}.value_lists.defaults.lookup_value_attribute must not be null."
            )

        return (
            references,
            canonical_value_attribute,
            lookup_value_attribute,
        )

    def _parse_classes(
        self,
        raw: Any,
        *,
        default_identity: CanonicalIdentityMapping,
        projection_reference_defaults: Mapping[
            str,
            ProjectionReferenceMapping,
        ],
        projection_value_attribute_default: str,
        projection_mapping_attribute_default: str,
        path: str,
    ) -> dict[
        str,
        ClassMapping,
    ]:
        """
        Parse source-class mappings.
        """

        raw_classes = self._mapping(
            raw or {},
            path=path,
        )

        return {
            self._string(
                class_id,
                path=f"{path}.<class_id>",
            ): self._parse_class(
                class_id=self._string(
                    class_id,
                    path=f"{path}.<class_id>",
                ),
                raw=self._mapping(
                    raw_class or {},
                    path=f"{path}.{class_id}",
                ),
                default_identity=default_identity,
                projection_reference_defaults=(projection_reference_defaults),
                projection_value_attribute_default=(projection_value_attribute_default),
                projection_mapping_attribute_default=(
                    projection_mapping_attribute_default
                ),
                path=f"{path}.{class_id}",
            )
            for (
                class_id,
                raw_class,
            ) in raw_classes.items()
        }

    def _parse_class(
        self,
        *,
        class_id: str,
        raw: Mapping[
            str,
            Any,
        ],
        default_identity: CanonicalIdentityMapping,
        projection_reference_defaults: Mapping[
            str,
            ProjectionReferenceMapping,
        ],
        projection_value_attribute_default: str,
        projection_mapping_attribute_default: str,
        path: str,
    ) -> ClassMapping:
        """
        Parse one class mapping.

        Projection-backed classes must not define declarative identities,
        attributes, or relations. A canonical-view projection is authoritative
        for the complete semantic mapping of the class.

        Class localisations remain valid for both declarative and
        projection-backed mappings because they identify the corresponding
        runtime source class.
        """

        del class_id

        projection = self._parse_projection(
            raw.get(
                "projection",
            ),
            reference_defaults=(projection_reference_defaults),
            value_attribute_default=(projection_value_attribute_default),
            mapping_attribute_default=(projection_mapping_attribute_default),
            path=f"{path}.projection",
        )

        raw_identities = self._mapping(
            raw.get(
                "identities",
                {},
            )
            or {},
            path=f"{path}.identities",
        )

        raw_attributes = self._mapping(
            raw.get(
                "attributes",
                {},
            )
            or {},
            path=f"{path}.attributes",
        )

        raw_relations = self._mapping(
            raw.get(
                "relations",
                {},
            )
            or {},
            path=f"{path}.relations",
        )

        localisations = self._parse_localisations(
            raw.get(
                "localisations",
                {},
            ),
            path=f"{path}.localisations",
        )

        if projection is not None:
            conflicting_sections = tuple(
                section
                for (
                    section,
                    value,
                ) in (
                    (
                        "identities",
                        raw_identities,
                    ),
                    (
                        "attributes",
                        raw_attributes,
                    ),
                    (
                        "relations",
                        raw_relations,
                    ),
                )
                if value
            )

            if conflicting_sections:
                raise ValueError(
                    f"{path} defines a canonical-view projection "
                    "together with "
                    f"{', '.join(conflicting_sections)}. "
                    "A canonical-view projection is authoritative "
                    "for the complete class mapping."
                )

            unsupported_projection_keys = set(
                raw,
            ) & {
                "class",
                "source_attribute",
                "target_attribute",
            }

            if unsupported_projection_keys:
                raise ValueError(
                    f"{path} defines a canonical-view projection "
                    "together with declarative class keys "
                    f"{tuple(sorted(unsupported_projection_keys))!r}."
                )

            return ClassMapping(
                canonical_class_id=None,
                identity=None,
                identities={},
                attributes={},
                relations={},
                localisations=localisations,
                projection=projection,
            )

        class_identity = CanonicalIdentityMapping(
            source_attribute=self._optional_string(
                raw.get(
                    "source_attribute",
                ),
                path=f"{path}.source_attribute",
                default=(default_identity.source_attribute or "obj_id"),
            ),
            canonical_attribute=self._optional_string(
                raw.get(
                    "target_attribute",
                ),
                path=f"{path}.target_attribute",
                default=(default_identity.canonical_attribute or "obj_id"),
            ),
        )

        identities = self._parse_identities(
            raw_identities,
            default_identity=class_identity,
            path=f"{path}.identities",
        )

        attributes = self._parse_attributes(
            raw_attributes,
            path=f"{path}.attributes",
        )

        relations = self._parse_relations(
            raw_relations,
            default_target_attribute=(class_identity.canonical_attribute),
            path=f"{path}.relations",
        )

        target_classes = frozenset(
            attribute.canonical_class_id
            for attribute in attributes.values()
            if attribute.canonical_class_id is not None
        )

        missing_identities = target_classes - identities.keys()

        if missing_identities:
            raise ValueError(
                f"{path} maps attributes to canonical classes "
                "without class-level identity declarations: "
                f"{tuple(sorted(missing_identities))!r}."
            )

        canonical_class_id = self._optional_string(
            raw.get(
                "class",
            ),
            path=f"{path}.class",
        )

        if canonical_class_id is not None and canonical_class_id not in identities:
            raise ValueError(
                f"{path}.class refers to canonical class "
                f"{canonical_class_id!r}, but no identity is "
                "declared for that class."
            )

        return ClassMapping(
            canonical_class_id=canonical_class_id,
            identity=class_identity,
            identities=identities,
            attributes=attributes,
            relations=relations,
            localisations=localisations,
            projection=None,
        )

    def _parse_identities(
        self,
        raw: Any,
        *,
        default_identity: CanonicalIdentityMapping,
        path: str,
    ) -> dict[
        str,
        CanonicalIdentityMapping,
    ]:
        """
        Parse canonical target identities.

        A null or empty identity declaration inherits both source and canonical
        attributes from ``default_identity``.

        For example, with model defaults:

            source_attribute: t_ili_tid
            target_attribute: obj_id

        this declaration:

            identities:
            measure:

        resolves to:

            source_attribute = t_ili_tid
            canonical_attribute = obj_id
        """

        raw_identities = self._mapping(
            raw or {},
            path=path,
        )

        identities: dict[
            str,
            CanonicalIdentityMapping,
        ] = {}

        for target_class_id, raw_identity in raw_identities.items():
            target_class_id = self._string(
                target_class_id,
                path=f"{path}.<target_class_id>",
            )

            identity_path = f"{path}.{target_class_id}"

            identity_data = self._mapping(
                raw_identity or {},
                path=identity_path,
            )

            source_attribute = self._optional_string(
                identity_data.get(
                    "source_attribute",
                ),
                path=(f"{identity_path}.source_attribute"),
                default=(default_identity.source_attribute),
            )

            target_attribute = self._optional_string(
                identity_data.get(
                    "target_attribute",
                ),
                path=(f"{identity_path}.target_attribute"),
                default=(default_identity.canonical_attribute),
            )

            identities[target_class_id] = CanonicalIdentityMapping(
                source_attribute=source_attribute,
                canonical_attribute=target_attribute,
            )

        return identities

    def _parse_attributes(
        self,
        raw: Any,
        *,
        path: str,
    ) -> dict[str, AttributeMapping]:
        """
        Parse singular direct attribute mappings.
        """

        raw_attributes = self._mapping(
            raw or {},
            path=path,
        )

        return {
            self._string(
                attribute_name,
                path=f"{path}.<attribute_name>",
            ): self._parse_attribute(
                attribute_name=self._string(
                    attribute_name,
                    path=f"{path}.<attribute_name>",
                ),
                raw=self._mapping(
                    raw_attribute or {},
                    path=(f"{path}.{attribute_name}"),
                ),
                path=(f"{path}.{attribute_name}"),
            )
            for attribute_name, raw_attribute in raw_attributes.items()
        }

    def _parse_attribute(
        self,
        *,
        attribute_name: str,
        raw: Mapping[str, Any],
        path: str,
    ) -> AttributeMapping:
        """
        Parse one source attribute mapping.

        Declarative attributes support exactly one canonical target.
        Multiple-target or structural projections must use a class-level
        canonical-view projection.
        """

        del attribute_name

        if "targets" in raw:
            raise ValueError(
                f"{path} uses obsolete `targets`. Use singular "
                "`target`, or use a class-level canonical-view "
                "projection when one source attribute produces "
                "several canonical effects."
            )

        target = self._mapping(
            raw.get(
                "target",
            ),
            path=f"{path}.target",
        )

        if not target:
            raise ValueError(f"{path} must define a non-empty `target`.")

        canonical_class_id = self._required_string(
            target.get(
                "class",
            ),
            path=f"{path}.target.class",
        )

        canonical_attribute_id = self._required_string(
            target.get(
                "attribute",
            ),
            path=f"{path}.target.attribute",
        )

        value_list = self._parse_value_list(
            raw=target.get(
                "value_list",
            ),
            mapping_attribute=target.get(
                "mapping_attribute",
            ),
            path=f"{path}.target",
        )

        known_keys = {
            "class",
            "attribute",
            "value_list",
            "mapping_attribute",
        }

        unknown_keys = (
            set(
                target,
            )
            - known_keys
        )

        if unknown_keys:
            raise ValueError(
                f"{path}.target contains unsupported keys: "
                f"{tuple(sorted(unknown_keys))!r}."
            )

        return AttributeMapping(
            canonical_class_id=canonical_class_id,
            canonical_attr_id=(canonical_attribute_id),
            value_list=value_list,
        )

    def _parse_value_list(
        self,
        *,
        raw: Any,
        mapping_attribute: Any,
        path: str,
    ) -> ValueListMapping | None:
        """
        Parse a declarative schema-qualified value-list lookup.
        """

        if raw is None:
            if mapping_attribute is not None:
                raise ValueError(
                    f"{path}.mapping_attribute requires {path}.value_list."
                )

            return None

        relation = self._required_string(
            raw,
            path=f"{path}.value_list",
        )

        self._validate_schema_qualified_relation(
            relation,
            path=f"{path}.value_list",
        )

        return ValueListMapping(
            relation=relation,
            mapping_attribute=self._required_string(
                mapping_attribute,
                path=f"{path}.mapping_attribute",
            ),
            value_attribute="code",
            ignored_values=(),
        )

    def _parse_relations(
        self,
        raw: Any,
        *,
        default_target_attribute: str,
        path: str,
    ) -> dict[str, RelationMapping]:
        """
        Parse canonical relation definitions and source localisations.
        """

        raw_relations = self._mapping(
            raw or {},
            path=path,
        )

        relations: dict[
            str,
            RelationMapping,
        ] = {}

        for local_attribute, raw_relation in raw_relations.items():
            local_attribute = self._string(
                local_attribute,
                path=f"{path}.<local_attribute>",
            )

            relation_path = f"{path}.{local_attribute}"

            relation_data = self._mapping(
                raw_relation or {},
                path=relation_path,
            )

            target = self._mapping(
                relation_data.get(
                    "target",
                ),
                path=f"{relation_path}.target",
            )

            if not target:
                raise ValueError(f"{relation_path} must define a non-empty `target`.")

            target_class_id = self._required_string(
                target.get(
                    "class",
                ),
                path=(f"{relation_path}.target.class"),
            )

            target_attribute_id = self._optional_string(
                target.get(
                    "attribute",
                ),
                path=(f"{relation_path}.target.attribute"),
                default=(default_target_attribute),
            )

            target_unknown_keys = set(
                target,
            ) - {
                "class",
                "attribute",
            }

            if target_unknown_keys:
                raise ValueError(
                    f"{relation_path}.target contains "
                    "unsupported keys: "
                    f"{tuple(sorted(target_unknown_keys))!r}."
                )

            localisations = self._parse_localisations(
                relation_data.get(
                    "localisations",
                    {},
                ),
                path=(f"{relation_path}.localisations"),
            )

            relation_unknown_keys = set(
                relation_data,
            ) - {
                "target",
                "localisations",
            }

            if relation_unknown_keys:
                raise ValueError(
                    f"{relation_path} contains unsupported keys: "
                    f"{tuple(sorted(relation_unknown_keys))!r}."
                )

            relations[local_attribute] = RelationMapping(
                referenced_class_id=target_class_id,
                referenced_attribute_id=target_attribute_id,
                localisations=localisations,
            )

        return relations

    def _parse_localisations(
        self,
        raw: Any,
        *,
        path: str,
    ) -> dict[str, str]:
        """
        Parse exact source-model identifiers keyed by language.
        """

        raw_localisations = self._mapping(
            raw or {},
            path=path,
        )

        localisations: dict[
            str,
            str,
        ] = {}

        for language, source_identifier in raw_localisations.items():
            language = self._required_string(
                language,
                path=f"{path}.<language>",
            )

            localisations[language] = self._required_string(
                source_identifier,
                path=f"{path}.{language}",
            )

        return localisations

    def _parse_projection(
        self,
        raw: Any,
        *,
        reference_defaults: Mapping[
            str,
            ProjectionReferenceMapping,
        ],
        value_attribute_default: str,
        mapping_attribute_default: str,
        path: str,
    ) -> CanonicalViewProjectionMapping | None:
        """
        Parse one class-level semantic projection.

        Model-level projection references are inherited by source attribute.
        Class-level references with the same source attribute override them.

        Value-list column defaults are materialized into each parsed
        ``ValueListMapping``.
        """

        if raw is None:
            return None

        projection_data = self._mapping(
            raw,
            path=path,
        )

        kind = self._required_string(
            projection_data.get(
                "kind",
            ),
            path=f"{path}.kind",
        )

        if kind != "canonical_view":
            raise ValueError(f"{path}.kind must be 'canonical_view', got {kind!r}.")

        canonical_view = self._parse_canonical_view(
            projection_data.get(
                "canonical_view",
            ),
            path=f"{path}.canonical_view",
        )

        local_references = self._parse_projection_references(
            projection_data.get(
                "references",
                {},
            ),
            path=f"{path}.references",
        )

        references = {
            **reference_defaults,
            **local_references,
        }

        value_lists = self._parse_projection_value_lists(
            projection_data.get(
                "value_lists",
                {},
            ),
            value_attribute_default=(value_attribute_default),
            mapping_attribute_default=(mapping_attribute_default),
            path=f"{path}.value_lists",
        )

        unknown_keys = set(
            projection_data,
        ) - {
            "kind",
            "canonical_view",
            "references",
            "value_lists",
        }

        if unknown_keys:
            raise ValueError(
                f"{path} contains unsupported keys: {tuple(sorted(unknown_keys))!r}."
            )

        return CanonicalViewProjectionMapping(
            canonical_view=canonical_view,
            references=references,
            value_lists=value_lists,
            kind="canonical_view",
        )

    def _parse_projection_references(
        self,
        raw: Any,
        *,
        path: str,
    ) -> dict[
        str,
        ProjectionReferenceMapping,
    ]:
        """
        Parse source-model references required by a projection.

        References resolve internal source identifiers such as ili2pg ``t_id``
        values to external source identities. They do not describe canonical
        target classes or target attributes.
        """

        raw_references = self._mapping(
            raw or {},
            path=path,
        )

        references: dict[
            str,
            ProjectionReferenceMapping,
        ] = {}

        for (
            source_attribute,
            raw_reference,
        ) in raw_references.items():
            source_attribute = self._string(
                source_attribute,
                path=f"{path}.<source_attribute>",
            )

            reference_path = f"{path}.{source_attribute}"

            reference_data = self._mapping(
                raw_reference,
                path=reference_path,
            )

            unknown_reference_keys = set(
                reference_data,
            ) - {
                "source",
            }

            if unknown_reference_keys:
                raise ValueError(
                    f"{reference_path} contains unsupported keys: "
                    f"{tuple(sorted(unknown_reference_keys))!r}."
                )

            source_data = self._mapping(
                reference_data.get(
                    "source",
                ),
                path=f"{reference_path}.source",
            )

            unknown_source_keys = set(
                source_data,
            ) - {
                "class",
                "identity_attribute",
                "discriminator",
            }

            if unknown_source_keys:
                raise ValueError(
                    f"{reference_path}.source contains unsupported "
                    "keys: "
                    f"{tuple(sorted(unknown_source_keys))!r}."
                )

            identity_attribute = self._optional_string(
                source_data.get(
                    "identity_attribute",
                ),
                path=(f"{reference_path}.source.identity_attribute"),
                default="t_ili_tid",
            )

            if identity_attribute is None:
                raise ValueError(
                    f"{reference_path}.source.identity_attribute must not be null."
                )

            references[source_attribute] = ProjectionReferenceMapping(
                source_class_id=self._required_string(
                    source_data.get(
                        "class",
                    ),
                    path=(f"{reference_path}.source.class"),
                ),
                identity_attribute=identity_attribute,
                discriminator=(
                    self._parse_projection_reference_discriminator(
                        source_data.get(
                            "discriminator",
                        ),
                        path=(f"{reference_path}.source.discriminator"),
                    )
                ),
            )

        return references

    def _parse_projection_reference_discriminator(
        self,
        raw: Any,
        *,
        path: str,
    ) -> ProjectionReferenceDiscriminator | None:
        """
        Parse an optional source-reference discriminator.

        The discriminator restricts reference resolution when multiple logical
        source classes share one physical source relation.

        It is structured mapping metadata, not a SQL expression.
        """

        if raw is None:
            return None

        discriminator_data = self._mapping(
            raw,
            path=path,
        )

        unknown_keys = set(
            discriminator_data,
        ) - {
            "attribute",
            "value",
        }

        if unknown_keys:
            raise ValueError(
                f"{path} contains unsupported keys: {tuple(sorted(unknown_keys))!r}."
            )

        if "value" not in discriminator_data:
            raise ValueError(f"{path} must define `value`.")

        return ProjectionReferenceDiscriminator(
            attribute=self._required_string(
                discriminator_data.get(
                    "attribute",
                ),
                path=f"{path}.attribute",
            ),
            value=discriminator_data["value"],
        )

    def _parse_projection_value_lists(
        self,
        raw: Any,
        *,
        value_attribute_default: str,
        mapping_attribute_default: str,
        path: str,
    ) -> dict[
        str,
        ValueListMapping,
    ]:
        """
        Parse value-list lookups required by a projection.

        Unlike declarative attribute mappings, these lookups do not determine
        canonical effect targets. They only prepare mapped values and candidate
        metadata for the semantic projector.
        """

        raw_value_lists = self._mapping(
            raw or {},
            path=path,
        )

        value_lists: dict[
            str,
            ValueListMapping,
        ] = {}

        for (
            source_attribute,
            raw_value_list,
        ) in raw_value_lists.items():
            source_attribute = self._string(
                source_attribute,
                path=f"{path}.<source_attribute>",
            )

            value_list_path = f"{path}.{source_attribute}"

            value_list_data = self._mapping(
                raw_value_list,
                path=value_list_path,
            )

            unknown_keys = set(
                value_list_data,
            ) - {
                "relation",
                "mapping_attribute",
                "value_attribute",
                "ignore",
            }

            if unknown_keys:
                raise ValueError(
                    f"{value_list_path} contains unsupported "
                    "keys: "
                    f"{tuple(sorted(unknown_keys))!r}."
                )

            relation = self._required_string(
                value_list_data.get(
                    "relation",
                ),
                path=f"{value_list_path}.relation",
            )

            self._validate_schema_qualified_relation(
                relation,
                path=f"{value_list_path}.relation",
            )

            mapping_attribute = self._optional_string(
                value_list_data.get(
                    "mapping_attribute",
                ),
                path=(f"{value_list_path}.mapping_attribute"),
                default=mapping_attribute_default,
            )

            value_attribute = self._optional_string(
                value_list_data.get(
                    "value_attribute",
                ),
                path=(f"{value_list_path}.value_attribute"),
                default=value_attribute_default,
            )

            if mapping_attribute is None:
                raise ValueError(
                    f"{value_list_path}.mapping_attribute must not be null."
                )

            if value_attribute is None:
                raise ValueError(f"{value_list_path}.value_attribute must not be null.")

            ignored_values = self._sequence(
                value_list_data.get(
                    "ignore",
                    (),
                )
                or (),
                path=f"{value_list_path}.ignore",
            )

            value_lists[source_attribute] = ValueListMapping(
                relation=relation,
                mapping_attribute=mapping_attribute,
                value_attribute=value_attribute,
                ignored_values=tuple(
                    ignored_values,
                ),
            )

        return value_lists

    def _parse_canonical_view(
        self,
        raw: Any,
        *,
        path: str,
    ) -> CanonicalViewMapping:
        """
        Parse one read-only canonical comparison view.
        """

        view_data = self._mapping(
            raw,
            path=path,
        )

        unknown_keys = set(
            view_data,
        ) - {
            "schema",
            "name",
            "identity_attribute",
        }

        if unknown_keys:
            raise ValueError(
                f"{path} contains unsupported keys: {tuple(sorted(unknown_keys))!r}."
            )

        identity_attribute = self._optional_string(
            view_data.get(
                "identity_attribute",
            ),
            path=f"{path}.identity_attribute",
            default="obj_id",
        )

        if identity_attribute is None:
            raise ValueError(f"{path}.identity_attribute must not be null.")

        return CanonicalViewMapping(
            schema=self._required_string(
                view_data.get(
                    "schema",
                ),
                path=f"{path}.schema",
            ),
            name=self._required_string(
                view_data.get(
                    "name",
                ),
                path=f"{path}.name",
            ),
            identity_attribute=identity_attribute,
        )

    def _validate_inheritance(
        self,
        *,
        mappings: Mapping[str, ModelMapping],
    ) -> None:
        """
        Validate model inheritance references and reject cycles.

        Inheritance is resolved later because source-class metadata is needed
        to apply conditional default attributes correctly.
        """

        for model_id, mapping in mappings.items():
            parent_id = (
                mapping.defaults.inherit_from if mapping.defaults is not None else None
            )

            if parent_id is not None and parent_id not in mappings:
                raise KeyError(
                    f"Model mapping {model_id!r} inherits unknown model {parent_id!r}."
                )

        visited: set[str] = set()
        visiting: list[str] = []

        def visit(
            model_id: str,
        ) -> None:
            if model_id in visited:
                return

            if model_id in visiting:
                cycle_start = visiting.index(
                    model_id,
                )

                cycle = (
                    *visiting[cycle_start:],
                    model_id,
                )

                raise ValueError(
                    "Model mapping inheritance cycle: "
                    + " -> ".join(
                        cycle,
                    )
                )

            visiting.append(
                model_id,
            )

            mapping = mappings[model_id]
            parent_id = (
                mapping.defaults.inherit_from if mapping.defaults is not None else None
            )

            if parent_id is not None:
                visit(
                    parent_id,
                )

            visiting.pop()
            visited.add(
                model_id,
            )

        for model_id in mappings:
            visit(
                model_id,
            )

    def _validate_schema_qualified_relation(
        self,
        relation: str,
        *,
        path: str,
    ) -> None:
        """
        Require a schema-qualified database relation.
        """

        relation_parts = relation.split(
            ".",
        )

        if (
            len(
                relation_parts,
            )
            != 2
        ):
            raise ValueError(
                f"{path} must be a schema-qualified relation "
                "in the form `schema.relation`, got "
                f"{relation!r}."
            )

        (
            schema_name,
            relation_name,
        ) = relation_parts

        if not schema_name or not relation_name:
            raise ValueError(f"{path} must define a non-empty schema and relation.")

    def _mapping(
        self,
        value: Any,
        *,
        path: str,
    ) -> Mapping[str, Any]:
        """
        Validate and return a mapping value.
        """

        if not isinstance(
            value,
            Mapping,
        ):
            raise TypeError(f"{path} must be a mapping, got {type(value)!r}.")

        return value

    def _required_string(
        self,
        value: Any,
        *,
        path: str,
    ) -> str:
        """
        Validate and return a non-empty string.
        """

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(f"{path} must be a string.")

        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{path} must not be empty.")

        return normalized

    def _optional_string(
        self,
        value: Any,
        *,
        path: str,
        default: str | None = None,
    ) -> str | None:
        """
        Validate and return an optional string.
        """

        if value is None:
            return default

        return self._required_string(
            value,
            path=path,
        )

    def _string(
        self,
        value: Any,
        *,
        path: str,
    ) -> str:
        """
        Validate a mapping key as a non-empty string.
        """

        return self._required_string(
            value,
            path=path,
        )

    def _boolean(
        self,
        value: Any,
        *,
        path: str,
    ) -> bool:
        """
        Validate and return a boolean.
        """

        if not isinstance(
            value,
            bool,
        ):
            raise TypeError(f"{path} must be a boolean.")

        return value

    def _sequence(
        self,
        value: Any,
        *,
        path: str,
    ) -> Sequence[Any,]:
        """
        Validate and return a non-string sequence.
        """

        if isinstance(
            value,
            str,
        ) or not isinstance(
            value,
            Sequence,
        ):
            raise TypeError(f"{path} must be a sequence, got {type(value)!r}.")

        return value
