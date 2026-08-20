from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from ..exceptions import Finding


class FindingTranslator(Protocol):
    """
    Translate findings for presentation.

    Implementations may use Qt translations, gettext, static dictionaries,
    or return the original finding message unchanged.
    """

    def translate(
        self,
        finding: Finding,
    ) -> str:
        """
        Return a localized presentation message for a finding.
        """


@dataclass(slots=True, frozen=True)
class DefaultFindingTranslator(FindingTranslator):
    """
    Return the untranslated fallback message stored on a finding.
    """

    def translate(
        self,
        finding: Finding,
    ) -> str:
        return finding.message
