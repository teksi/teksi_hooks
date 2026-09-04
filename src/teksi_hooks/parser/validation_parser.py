from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..exceptions import (
    Severity,
)
from ..models.validation import (
    AttributeValidation,
    ChangeOperation,
    ClassValidationDefinition,
    ObjectValidation,
    ValidationDefinition,
)


@dataclass(
    slots=True,
)
class ValidationParser:
    """
    Parse canonical validation YAML definitions.

    The parser handles:

    - default mandatory attributes;
    - default attribute validation rules;
    - default object validation rules;
    - class-specific mandatory attributes;
    - class-specific attribute validation rules;
    - class-specific object validation rules.

    It does not parse rights, privileges, CRUD rules, conditions, ownership
    rules, derived rights or state-transition privileges.
    """

    def parse_text(
        self,
        text: str,
    ) -> ValidationDefinition:
        """
        Parse validation configuration from YAML text.
        """

        data = yaml.safe_load(
            text,
        )

        return self._parse_dict(
            self._mapping(
                data,
                location="validation document",
            ),
        )

    def parse_file(
        self,
        path: str | Path,
    ) -> ValidationDefinition:
        """
        Parse validation configuration from a YAML file.
        """

        with open(
            path,
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(
                file,
            )

        return self._parse_dict(
            self._mapping(
                data,
                location=str(
                    path,
                ),
            ),
        )

    def _parse_dict(
        self,
        data: Mapping[
            str,
            Any,
        ],
    ) -> ValidationDefinition:
        """
        Parse the root validation configuration.
        """

        defaults = self._mapping(
            data.get(
                "defaults",
                {},
            ),
            location="defaults",
        )

        classes = self._parse_classes(
            data.get(
                "classes",
                (),
            ),
        )

        return ValidationDefinition(
            mandatory_attributes=(
                self._parse_mandatory_attributes(
                    defaults.get(
                        "mandatory",
                        (),
                    ),
                    location="defaults.mandatory",
                )
            ),
            attribute_validations=(
                self._parse_attribute_validation_groups(
                    defaults.get(
                        "validation_rules",
                        {},
                    ),
                    location=("defaults.validation_rules"),
                )
            ),
            object_validations=(
                self._parse_object_validation_groups(
                    defaults.get(
                        "object_validation_rules",
                        {},
                    ),
                    location=("defaults.object_validation_rules"),
                )
            ),
            classes={
                class_definition.class_id: (class_definition)
                for class_definition in classes
            },
        )

    def _parse_class(
        self,
        raw: Mapping[
            str,
            Any,
        ],
        *,
        index: int,
    ) -> ClassValidationDefinition:
        """
        Parse one class-specific validation definition.
        """

        location = f"classes[{index}]"

        class_id = raw.get(
            "id",
        )

        if (
            not isinstance(
                class_id,
                str,
            )
            or not class_id
        ):
            raise ValueError(f"{location}.id must be a non-empty string.")

        return ClassValidationDefinition(
            class_id=class_id,
            mandatory_attributes=(
                self._parse_mandatory_attributes(
                    raw.get(
                        "mandatory",
                        (),
                    ),
                    location=(f"{location}.mandatory"),
                )
            ),
            attribute_validations=(
                self._parse_attribute_validation_groups(
                    raw.get(
                        "validation_rules",
                        {},
                    ),
                    location=(f"{location}.validation_rules"),
                )
            ),
            object_validations=(
                self._parse_object_validation_groups(
                    raw.get(
                        "object_validation_rules",
                        {},
                    ),
                    location=(f"{location}.object_validation_rules"),
                )
            ),
        )

    def _parse_classes(
        self,
        raw_classes: Any,
    ) -> tuple[
        ClassValidationDefinition,
        ...,
    ]:
        """
        Parse class-specific validation definitions.
        """

        classes = self._sequence(
            raw_classes,
            location="classes",
        )

        parsed_classes = tuple(
            self._parse_class(
                self._mapping(
                    raw_class,
                    location=f"classes[{index}]",
                ),
                index=index,
            )
            for index, raw_class in enumerate(
                classes,
            )
        )

        class_ids = [class_definition.class_id for class_definition in parsed_classes]

        duplicate_class_ids = {
            class_id
            for class_id in class_ids
            if class_ids.count(
                class_id,
            )
            > 1
        }

        if duplicate_class_ids:
            raise ValueError(
                "Validation configuration contains duplicate "
                "class definitions: "
                f"{sorted(duplicate_class_ids)}"
            )

        return parsed_classes

    def _parse_mandatory_attributes(
        self,
        raw: Any,
        *,
        location: str,
    ) -> frozenset[str]:
        """
        Parse mandatory canonical attribute identifiers.
        """

        values = self._sequence(
            raw,
            location=location,
        )

        mandatory_attributes = []

        for index, value in enumerate(
            values,
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise TypeError(f"{location}[{index}] must be a non-empty string.")

            mandatory_attributes.append(
                value,
            )

        return frozenset(
            mandatory_attributes,
        )

    def _parse_attribute_validation_groups(
        self,
        raw: Any,
        *,
        location: str,
    ) -> dict[
        str,
        tuple[
            AttributeValidation,
            ...,
        ],
    ]:
        """
        Parse attribute validation groups keyed by attribute identifier.
        """

        groups = self._mapping(
            raw,
            location=location,
        )

        return {
            attribute_id: (
                self._parse_attribute_validations(
                    self._group_rules(
                        raw_group,
                        location=(f"{location}.{attribute_id}"),
                    ),
                    location=(f"{location}.{attribute_id}.rules"),
                )
            )
            for attribute_id, raw_group in groups.items()
        }

    def _parse_object_validation_groups(
        self,
        raw: Any,
        *,
        location: str,
    ) -> dict[
        str,
        tuple[
            ObjectValidation,
            ...,
        ],
    ]:
        """
        Parse object validation groups keyed by configuration identifier.
        """

        groups = self._mapping(
            raw,
            location=location,
        )

        return {
            group_id: (
                self._parse_object_validations(
                    self._group_rules(
                        raw_group,
                        location=(f"{location}.{group_id}"),
                    ),
                    location=(f"{location}.{group_id}.rules"),
                )
            )
            for group_id, raw_group in groups.items()
        }

    def _group_rules(
        self,
        raw_group: Any,
        *,
        location: str,
    ) -> Sequence[Any,]:
        """
        Return the raw rules contained in one validation group.
        """

        group = self._mapping(
            raw_group,
            location=location,
        )

        return self._sequence(
            group.get(
                "rules",
                (),
            ),
            location=f"{location}.rules",
        )

    def _parse_attribute_validations(
        self,
        raw_validations: Sequence[Any,],
        *,
        location: str,
    ) -> tuple[
        AttributeValidation,
        ...,
    ]:
        """
        Parse attribute-level validation rules.
        """

        return tuple(
            self._parse_attribute_validation(
                self._mapping(
                    raw_validation,
                    location=(f"{location}[{index}]"),
                ),
                location=(f"{location}[{index}]"),
            )
            for index, raw_validation in enumerate(
                raw_validations,
            )
        )

    def _parse_attribute_validation(
        self,
        data: Mapping[
            str,
            Any,
        ],
        *,
        location: str,
    ) -> AttributeValidation:
        """
        Parse one attribute-level validation rule.
        """

        return AttributeValidation(
            id=self._validation_id(
                data,
                location=location,
            ),
            level=self._severity(
                data,
                location=location,
            ),
            operations=self._operations(
                data,
                default=tuple(
                    ChangeOperation,
                ),
                location=location,
            ),
            context_value=self._optional_string(
                data.get(
                    "context_value",
                ),
                location=(f"{location}.context_value"),
            ),
            parameters=self._parameters(
                data.get(
                    "parameters",
                    {},
                ),
                location=f"{location}.parameters",
            ),
        )

    def _parse_object_validations(
        self,
        raw_validations: Sequence[Any,],
        *,
        location: str,
    ) -> tuple[
        ObjectValidation,
        ...,
    ]:
        """
        Parse object-level validation rules.
        """

        return tuple(
            self._parse_object_validation(
                self._mapping(
                    raw_validation,
                    location=(f"{location}[{index}]"),
                ),
                location=(f"{location}[{index}]"),
            )
            for index, raw_validation in enumerate(
                raw_validations,
            )
        )

    def _parse_object_validation(
        self,
        data: Mapping[
            str,
            Any,
        ],
        *,
        location: str,
    ) -> ObjectValidation:
        """
        Parse one object-level validation rule.
        """

        return ObjectValidation(
            id=self._validation_id(
                data,
                location=location,
            ),
            level=self._severity(
                data,
                location=location,
            ),
            operations=self._operations(
                data,
                default=(
                    ChangeOperation.INSERT,
                    ChangeOperation.UPDATE,
                ),
                location=location,
            ),
            parameters=self._parameters(
                data.get(
                    "parameters",
                    {},
                ),
                location=f"{location}.parameters",
            ),
        )

    def _validation_id(
        self,
        data: Mapping[
            str,
            Any,
        ],
        *,
        location: str,
    ) -> str:
        """
        Return and validate a validation identifier.
        """

        validation_id = data.get(
            "id",
        )

        if (
            not isinstance(
                validation_id,
                str,
            )
            or not validation_id
        ):
            raise ValueError(f"{location}.id must be a non-empty string.")

        return validation_id

    def _severity(
        self,
        data: Mapping[
            str,
            Any,
        ],
        *,
        location: str,
    ) -> Severity:
        """
        Parse a validation finding severity.
        """

        try:
            return Severity(
                data.get(
                    "level",
                    "error",
                )
            )
        except ValueError as exception:
            raise ValueError(
                f"{location}.level contains an unsupported "
                f"severity: {data.get('level')!r}."
            ) from exception

    def _operations(
        self,
        data: Mapping[
            str,
            Any,
        ],
        *,
        default: tuple[
            ChangeOperation,
            ...,
        ],
        location: str,
    ) -> tuple[
        ChangeOperation,
        ...,
    ]:
        """
        Parse applicable change operations.
        """

        raw_operations = data.get(
            "operations",
            tuple(operation.value for operation in default),
        )

        operation_values = self._sequence(
            raw_operations,
            location=f"{location}.operations",
        )

        try:
            return tuple(
                ChangeOperation(
                    operation,
                )
                for operation in operation_values
            )
        except ValueError as exception:
            raise ValueError(
                f"{location}.operations contains an unsupported change operation."
            ) from exception

    def _parameters(
        self,
        raw: Any,
        *,
        location: str,
    ) -> dict[
        str,
        Any,
    ]:
        """
        Parse validation-specific parameters.

        The ``attributes`` parameter is normalized to a tuple of canonical
        attribute identifiers.
        """

        parameters = dict(
            self._mapping(
                raw,
                location=location,
            )
        )

        if "attributes" in parameters:
            raw_attributes = self._sequence(
                parameters["attributes"],
                location=f"{location}.attributes",
            )

            attributes = []

            for index, attribute_id in enumerate(
                raw_attributes,
            ):
                if (
                    not isinstance(
                        attribute_id,
                        str,
                    )
                    or not attribute_id
                ):
                    raise TypeError(
                        f"{location}.attributes[{index}] must be a non-empty string."
                    )

                attributes.append(
                    attribute_id,
                )

            parameters["attributes"] = tuple(
                attributes,
            )

        return parameters

    def _mapping(
        self,
        value: Any,
        *,
        location: str,
    ) -> Mapping[
        str,
        Any,
    ]:
        """
        Return a mapping or raise a configuration error.
        """

        if value is None:
            return {}

        if not isinstance(
            value,
            Mapping,
        ):
            raise TypeError(
                f"Expected mapping at {location}, got {type(value).__name__}."
            )

        return value

    def _sequence(
        self,
        value: Any,
        *,
        location: str,
    ) -> Sequence[Any,]:
        """
        Return a non-string sequence or raise a configuration error.
        """

        if value is None:
            return ()

        if isinstance(
            value,
            (
                str,
                bytes,
                bytearray,
            ),
        ) or not isinstance(
            value,
            Sequence,
        ):
            raise TypeError(
                f"Expected sequence at {location}, got {type(value).__name__}."
            )

        return value

    def _optional_string(
        self,
        value: Any,
        *,
        location: str,
    ) -> str | None:
        """
        Return an optional non-empty string.
        """

        if value is None:
            return None

        if (
            not isinstance(
                value,
                str,
            )
            or not value
        ):
            raise TypeError(f"{location} must be a non-empty string or null.")

        return value
