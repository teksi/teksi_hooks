from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..evaluators.effects import EffectDocumentValidator
from ..models.canonical_object import CanonicalObjectIdentity
from ..models.effects import (
    Effect,
    EffectDocument,
    EffectSource,
    EnforceExistsEffect,
    EnforceNotExistsEffect,
    UpdateAttributeEffect,
)


@dataclass(slots=True)
class EffectParser:
    """
    Parser for JSONB effect documents.

    Converts JSON effect documents into strongly typed effect models.
    """

    validator: EffectDocumentValidator = field(
        default_factory=EffectDocumentValidator,
    )

    SUPPORTED_VERSION = 1

    def parse_file(
        self,
        path: str | Path,
    ) -> EffectDocument:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)

        return self._parse_dict(
            data,
        )

    def parse_json(
        self,
        document: str,
    ) -> EffectDocument:
        return self._parse_dict(
            json.loads(document),
        )

    def _parse_dict(
        self,
        data: dict[str, Any],
    ) -> EffectDocument:
        document = EffectDocument(
            version=data["version"],
            source=self._parse_source(
                data["source"],
            ),
            effects=tuple(
                self._parse_effect(
                    effect,
                )
                for effect in data["effects"]
            ),
        )

        self.validator.validate_or_raise(
            document,
        )

        return document

    def _parse_source(
        self,
        data: dict[str, Any],
    ) -> EffectSource:
        return EffectSource(
            model=data["model"],
            class_id=data["class_id"],
            object_id=data["object_id"],
        )

    def _parse_identity(
        self,
        data: dict[str, Any],
    ) -> CanonicalObjectIdentity:
        identity = data["identity"]

        return CanonicalObjectIdentity(
            class_id=identity["class_id"],
            attributes=identity["attributes"],
        )

    def _parse_effect(
        self,
        data: dict[str, Any],
    ) -> Effect:
        kind = data["kind"]

        if kind == "update_attribute":
            return UpdateAttributeEffect(
                identity=self._parse_identity(
                    data,
                ),
                attribute_id=data["attribute_id"],
                value=data.get(
                    "value",
                ),
            )

        if kind == "enforce_exists":
            return EnforceExistsEffect(
                identity=self._parse_identity(
                    data,
                ),
            )

        if kind == "enforce_not_exists":
            return EnforceNotExistsEffect(
                identity=self._parse_identity(
                    data,
                ),
            )

        raise ValueError(f"Unsupported effect kind: {kind!r}")
