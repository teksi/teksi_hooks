from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..models.canonical_object import (
    CanonicalIdentityMapping,
)
from ..models.mapping import (
    AttributeMapping,
    ClassMapping,
    FunctionMapping,
    ModelMapping,
    MappingDefaults,
    RelationMapping,
    ValueListMapping,
)


@dataclass(slots=True)
class ModelMappingParser:
    """
    Parse source-model to canonical-model mapping definitions.

    A mapping document may contain several named source models under
    ``models``.

    Model definitions may contain:

    - model-level defaults;
    - model inheritance;
    - class-level row projection functions;
    - class-level canonical identities;
    - direct attribute mappings;
    - source relation localisations;
    - value-list lookup definitions.

    This parser only converts YAML into mapping models. It does not:

    - inspect source-model classes;
    - apply conditional default attributes;
    - resolve explicit-before-implicit lookup precedence;
    - query value-list relations;
    - execute mapping functions;
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

        return self._select_model(
            mappings=mappings,
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
        data: Mapping[str, Any],
        *,
        model_id: str | None = None,
    ) -> ModelMapping:
        """
        Parse one model mapping from an already loaded YAML document.
        """

        mappings = self.parse_models_dict(
            data,
        )

        return self._select_model(
            mappings=mappings,
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

        classes = self._parse_classes(
            raw.get(
                "classes",
                {},
            ),
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

    def _parse_classes(
        self,
        raw: Any,
        *,
        path: str,
    ) -> dict[str, ClassMapping]:
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
                path=f"{path}.{class_id}",
            )
            for class_id, raw_class in raw_classes.items()
        }

    def _parse_class(
        self,
        *,
        class_id: str,
        raw: Mapping[str, Any],
        path: str,
    ) -> ClassMapping:
        """
        Parse one class mapping.

        Function-backed classes must not define declarative identities,
        attributes, or relations. Model defaults are not applied here.
        """

        function = self._parse_function(
            raw.get(
                "function",
            ),
            path=f"{path}.function",
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

        if function is not None:
            conflicting_sections = tuple(
                section
                for section, value in (
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
                    f"{path} defines a row-level function together "
                    f"with {', '.join(conflicting_sections)}. "
                    "A row-level function is authoritative for the "
                    "complete class mapping."
                )

            return ClassMapping(
                canonical_class_id=None,
                function=function,
                identities={},
                attributes={},
                relations={},
            )

        class_identity = CanonicalIdentityMapping(
            source_attribute=self._optional_string(
                raw.get(
                    "source_attribute",
                ),
                path=f"{path}.source_attribute",
                default="obj_id",
            ),
            canonical_attribute=self._optional_string(
                raw.get(
                    "target_attribute",
                ),
                path=f"{path}.target_attribute",
                default="obj_id",
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
            function=None,
            identities=identities,
            attributes=attributes,
            relations=relations,
        )

    def _parse_identities(
        self,
        raw: Any,
        *,
        default_identity: CanonicalIdentityMapping,
        path: str,
    ) -> dict[str, CanonicalIdentityMapping]:
        """
        Parse canonical target identities.

        A null or empty identity declaration inherits both source and target
        attributes from ``default_identity``.

        Example:

            identities:
              measure:

        resolves to:

            source_attribute = obj_id
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
        Multiple-target projections must use a row-level function mapping.
        """

        del attribute_name

        if "targets" in raw:
            raise ValueError(
                f"{path} uses obsolete `targets`. Use singular "
                "`target`, or use a function mapping when one source "
                "attribute produces several canonical effects."
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
        Parse a schema-qualified value-list lookup relation.

        The configured mapping attribute is compared with the source value.
        The canonical value is always read from the relation's `code` column.
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

        relation_parts = relation.split(
            ".",
        )

        if len(relation_parts) != 2:
            raise ValueError(
                f"{path}.value_list must be a schema-qualified "
                "relation in the form `schema.relation`, got "
                f"{relation!r}."
            )

        schema_name, relation_name = relation_parts

        if not schema_name or not relation_name:
            raise ValueError(
                f"{path}.value_list must define a non-empty schema and relation."
            )

        return ValueListMapping(
            relation=relation,
            mapping_attribute=self._required_string(
                mapping_attribute,
                path=f"{path}.mapping_attribute",
            ),
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

    def _parse_function(
        self,
        raw: Any,
        *,
        path: str,
    ) -> FunctionMapping | None:
        """
        Parse one row-level SQL projection function.
        """

        if raw is None:
            return None

        function_data = self._mapping(
            raw,
            path=path,
        )

        raw_parameters = self._mapping(
            function_data.get(
                "parameters",
                {},
            )
            or {},
            path=f"{path}.parameters",
        )

        parameters = {
            self._required_string(
                parameter,
                path=(f"{path}.parameters.<parameter>"),
            ): self._required_string(
                source,
                path=(f"{path}.parameters.{parameter}"),
            )
            for parameter, source in raw_parameters.items()
        }

        unknown_keys = set(
            function_data,
        ) - {
            "schema",
            "name",
            "parameters",
        }

        if unknown_keys:
            raise ValueError(
                f"{path} contains unsupported keys: {tuple(sorted(unknown_keys))!r}."
            )

        return FunctionMapping(
            schema=self._required_string(
                function_data.get(
                    "schema",
                ),
                path=f"{path}.schema",
            ),
            name=self._required_string(
                function_data.get(
                    "name",
                ),
                path=f"{path}.name",
            ),
            parameters=parameters,
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
