from typing import Protocol

from ..models.canonical_object import (
    CanonicalModelMetadata,
)
from ..models.effects import (
    EffectDocument,
)
from ..capabilities.review import (
    ChangeObjectProvider,
)


class QuarantineEffectProjector(Protocol):
    """
    Protocol for projecting imported quarantine data into canonical effects.

    Implementations read an ili2pg quarantine schema, apply the effective
    source-model mapping and produce an EffectDocument.
    """

    def effect_document_from_quarantine(
        self,
        *,
        schema: str,
        source_model: str,
        canonical_metadata: CanonicalModelMetadata,
    ) -> EffectDocument:
        """
        Project one populated quarantine schema into canonical effects.
        """


class ChangeObjectProviderFactory(Protocol):
    """
    Factory protocol for creating a canonical object provider used during
    review-feature generation.
    """

    def change_object_provider(
        self,
        *,
        live_schema: str,
        import_schema: str,
        canonical_metadata: CanonicalModelMetadata,
    ) -> ChangeObjectProvider:
        """
        Return a ChangeObjectProvider implementation.
        """
