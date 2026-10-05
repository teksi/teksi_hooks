from __future__ import annotations

from dataclasses import dataclass

from ..capabilities.relation_lookup import RelationLookupCapability
from ..exceptions import SnapshotValidationError
from ..models.diff_snapshot import (
    DiffSnapshot,
    SnapshotMetadata,
    SnapshotObject,
)
from ..models.effects import EffectDocument


@dataclass(slots=True)
class DiffSnapshotBuilder:
    """
    Builds diff snapshots from effect documents.
    """

    relation_lookup: RelationLookupCapability

    def build(
        self,
        document: EffectDocument,
    ) -> DiffSnapshot:
        objects: dict[
            tuple,
            SnapshotObject,
        ] = {}

        for effect in document.effects:
            key = effect.identity.key()

            if key not in objects:
                current_object = self.relation_lookup.current_object(
                    effect.identity,
                )

                if current_object is None:
                    raise SnapshotValidationError.from_message(
                        "Current object not found."
                    )

                if current_object.last_modification is None:
                    raise SnapshotValidationError.from_message(
                        "Current object is missing last_modification."
                    )

                objects[key] = SnapshotObject(
                    identity=effect.identity,
                    last_modification=current_object.last_modification,
                )

        metadata = SnapshotMetadata(
            created_at=document.created_at,
            source_model=document.source.model,
            source_class_id=document.source.class_id,
            source_object_id=document.source.object_id,
        )

        return DiffSnapshot(
            metadata=metadata,
            objects=tuple(
                objects.values(),
            ),
            effects=document.effects,
        )
