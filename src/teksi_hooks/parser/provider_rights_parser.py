from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..models.oid import Oid

from ..models.provider import (
    Provider,
    ProviderPermission,
)
from ..exceptions import TeksiHookError


@dataclass(slots=True)
class ProviderRightsParser:
    oid_type: type[Oid]

    """
    Parser for provider privilege assignment YAML files.

    The parser converts YAML provider definitions into parsed Provider objects.
    It does not merge duplicate data-owner permissions. Merging belongs to the
    ProviderResolver.
    """

    def __post_init__(
        self,
    ) -> None:
        if not issubclass(
            self.oid_type,
            Oid,
        ):
            raise TeksiHookError.from_message(
                "Provided oid_type must inherit from Oid."
            )

    def parse_file(
        self,
        path: str | Path,
    ) -> tuple[Provider, ...]:
        with open(path, encoding="utf-8") as file:
            data = yaml.safe_load(file)

        return self._parse_dict(
            data or {},
        )

    def _parse_dict(
        self,
        data: dict[str, Any],
    ) -> tuple[Provider, ...]:
        return tuple(
            self._parse_provider(raw_provider)
            for raw_provider in data.get(
                "providers",
                [],
            )
        )

    def _parse_provider(
        self,
        raw: dict[str, Any],
    ) -> Provider:
        permissions = tuple(
            self._parse_permission(
                raw_permission,
            )
            for raw_permission in raw.get(
                "permissions",
                [],
            )
        )

        return Provider(
            name=raw["name"],
            organisation_oid=self.oid_type(
                raw["organisation_oid"],
            ),
            permissions=frozenset(
                permission for permission in permissions if permission.privileges
            ),
        )

    def _parse_permission(
        self,
        raw: dict[str, Any],
    ) -> ProviderPermission:
        return ProviderPermission(
            dataowner_oid=self.oid_type(
                raw["dataowner_oid"],
            ),
            privileges=self._parse_privileges(
                raw.get("privileges") or [],
            ),
        )

    def _parse_privileges(
        self,
        raw: list[str],
    ) -> frozenset:
        return frozenset(raw)
