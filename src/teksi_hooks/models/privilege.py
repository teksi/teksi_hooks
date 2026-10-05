from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from .canonical_object import LanguageCode

PrivilegeId = str
ALL_PRIVILEGES: PrivilegeId = "__all__"


@dataclass(frozen=True, slots=True)
class PrivilegeMetadata:
    """
    Human-readable metadata for a provider privilege.

    Labels are keyed by language code, for example:

        {
            "de": "Datenbewirtschafter Werkinformation",
            "fr": "Gestionnaire cadastral",
        }
    """

    labels: Mapping[
        LanguageCode,
        str,
    ] = field(
        default_factory=dict,
    )

    descriptions: Mapping[
        LanguageCode,
        str,
    ] = field(
        default_factory=dict,
    )

    def label(
        self,
        language: LanguageCode,
    ) -> str | None:
        return self.labels.get(
            language,
        ) or self.labels.get(
            "de",
        )

    def description(
        self,
        language: LanguageCode,
    ) -> str | None:
        return self.descriptions.get(
            language,
        ) or self.descriptions.get(
            "de",
        )
