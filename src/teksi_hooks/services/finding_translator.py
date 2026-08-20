from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Protocol

from ..exceptions import Finding


FINDING_MESSAGE_TEMPLATES: Mapping[
    str,
    str,
] = {
    "missing_context_value": ("Required context value '{context_value}' is missing."),
    "permission_denied": ("The requested change is not permitted."),
    "unsupported_change_operation": (
        "The change operation '{operation}' is not supported."
    ),
    "unsupported_effect_document_version": (
        "Effect document version '{version}' is not supported."
    ),
    "missing_effect_identity_class": (
        "The effect identity is missing its canonical class identifier."
    ),
    "missing_effect_identity_attributes": (
        "The effect identity does not contain identity attributes."
    ),
    "missing_effect_attribute": (
        "The update effect is missing its canonical attribute identifier."
    ),
    "unsupported_effect_type": ("The effect type '{effect_type}' is not supported."),
    "contradicting_existence_effects": (
        "An object cannot simultaneously be required to exist "
        "and required not to exist."
    ),
    "contradicting_update_and_not_exists_effects": (
        "An object cannot be updated while also being required not to exist."
    ),
    "invalid_transition": (
        "Transition from '{old_value}' to '{new_value}' is not allowed."
    ),
}


class FindingTranslator(Protocol):
    """
    Translate findings for presentation.

    Implementations may use Qt translations, gettext, static dictionaries,
    or the untranslated fallback message stored on the finding.
    """

    def translate(
        self,
        finding: Finding,
    ) -> str:
        """
        Return the presentation message for a finding.
        """


@dataclass(slots=True, frozen=True)
class DefaultFindingTranslator:
    """
    Render finding messages from stable finding codes and structured details.

    The default implementation uses the framework's English message catalog.
    Additional templates may be supplied by adapters or plugins.
    """

    templates: Mapping[
        str,
        str,
    ] = field(
        default_factory=lambda: FINDING_MESSAGE_TEMPLATES,
    )

    def translate(
        self,
        finding: Finding,
    ) -> str:
        """
        Return the rendered message for a finding.

        The finding's fallback message is returned when no template exists or
        when the template cannot be formatted with the available details.
        """

        code = getattr(
            finding,
            "code",
            None,
        )

        if code is None:
            return finding.message

        template = self.templates.get(
            code,
        )

        if template is None:
            return finding.message

        try:
            return template.format(
                **finding.details,
            )
        except (
            KeyError,
            IndexError,
            ValueError,
        ):
            return finding.message
