from datetime import UTC, datetime

import pytest

from teksi_hooks.capabilities.relation_lookup import InMemoryRelationLookupCapability
from teksi_hooks.exceptions import SnapshotValidationError
from teksi_hooks.models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)
from teksi_hooks.models.effects import (
    EffectDocument,
    EffectSource,
    UpdateAttributeEffect,
)
from teksi_hooks.services.diff_snapshot_builder import (
    DiffSnapshotBuilder,
)

DEFAULT_LAST_MODIFICATION = datetime(
    2026,
    1,
    1,
    tzinfo=UTC,
)


def _object(
    *,
    identity: CanonicalObjectIdentity,
    last_modification: datetime | None = DEFAULT_LAST_MODIFICATION,
) -> CanonicalObject:
    return CanonicalObject(
        identity=identity,
        values=dict(
            identity.attributes,
        ),
        last_modification=last_modification,
    )


def _lookup_obj(
    *objects: CanonicalObject,
) -> InMemoryRelationLookupCapability:
    return InMemoryRelationLookupCapability(
        objects=objects,
    )


def _lookup(
    *,
    identity: CanonicalObjectIdentity,
    last_modification: datetime | None = DEFAULT_LAST_MODIFICATION,
) -> InMemoryRelationLookupCapability:
    return InMemoryRelationLookupCapability(
        objects=(
            CanonicalObject(
                identity=identity,
                values={
                    "obj_id": identity.attributes.get("obj_id"),
                },
                last_modification=last_modification,
            ),
        ),
    )


def test_build_snapshot_from_single_effect() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )
    builder = DiffSnapshotBuilder(
        relation_lookup=_lookup(
            identity=identity,
        ),
    )
    document = EffectDocument(
        version=1,
        source=EffectSource(
            model="ag64",
            class_id="GepKnoten",
            object_id="ch123456AG987654",
        ),
        effects=(
            UpdateAttributeEffect(
                identity=identity,
                attribute_id="status",
                value=1234,
            ),
        ),
    )

    snapshot = builder.build(
        document,
    )

    assert (
        len(
            snapshot.objects,
        )
        == 1
    )

    assert snapshot.objects[0].identity == identity


def test_build_snapshot_groups_effects_by_object() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    builder = DiffSnapshotBuilder(
        relation_lookup=_lookup(
            identity=identity,
        ),
    )

    document = EffectDocument(
        version=1,
        source=EffectSource(
            model="ag64",
            class_id="GepKnoten",
            object_id="ch123456AG987654",
        ),
        effects=(
            UpdateAttributeEffect(
                identity=identity,
                attribute_id="status",
                value=1,
            ),
            UpdateAttributeEffect(
                identity=identity,
                attribute_id="remark",
                value="test",
            ),
        ),
    )

    snapshot = builder.build(
        document,
    )

    assert (
        len(
            snapshot.objects,
        )
        == 1
    )

    assert (
        len(
            snapshot.effects,
        )
        == 2
    )


def test_build_snapshot_keeps_distinct_objects() -> None:
    identity_1 = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "object_1",
        },
    )

    identity_2 = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "object_2",
        },
    )

    builder = DiffSnapshotBuilder(
        relation_lookup=_lookup_obj(
            _object(
                identity=identity_1,
            ),
            _object(
                identity=identity_2,
            ),
        ),
    )

    document = EffectDocument(
        version=1,
        source=EffectSource(
            model="ag64",
            class_id="GepKnoten",
            object_id="ch123456AG987654",
        ),
        effects=(
            UpdateAttributeEffect(
                identity=identity_1,
                attribute_id="status",
                value=1,
            ),
            UpdateAttributeEffect(
                identity=identity_2,
                attribute_id="status",
                value=1,
            ),
        ),
    )

    snapshot = builder.build(
        document,
    )

    assert (
        len(
            snapshot.objects,
        )
        == 2
    )

    assert {snapshot_object.identity.key() for snapshot_object in snapshot.objects} == {
        identity_1.key(),
        identity_2.key(),
    }


def test_build_snapshot_copies_metadata() -> None:
    builder = DiffSnapshotBuilder(
        relation_lookup=_lookup_obj(),
    )

    document = EffectDocument(
        version=1,
        source=EffectSource(
            model="ag64",
            class_id="GepKnoten",
            object_id="ch123456AG987654",
        ),
        effects=(),
    )

    snapshot = builder.build(
        document,
    )

    assert snapshot.metadata.source_model == "ag64"
    assert snapshot.metadata.source_class_id == "GepKnoten"
    assert snapshot.metadata.source_object_id == "ch123456AG987654"


def test_build_snapshot_copies_current_last_modification() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    last_modification = datetime(
        2026,
        2,
        3,
        4,
        5,
        6,
        tzinfo=UTC,
    )

    builder = DiffSnapshotBuilder(
        relation_lookup=_lookup_obj(
            _object(
                identity=identity,
                last_modification=last_modification,
            ),
        ),
    )

    document = EffectDocument(
        version=1,
        source=EffectSource(
            model="ag64",
            class_id="GepKnoten",
            object_id="ch123456AG987654",
        ),
        effects=(
            UpdateAttributeEffect(
                identity=identity,
                attribute_id="status",
                value="active",
            ),
        ),
    )

    snapshot = builder.build(
        document,
    )

    assert (
        len(
            snapshot.objects,
        )
        == 1
    )

    assert snapshot.objects[0].last_modification == last_modification


def test_build_snapshot_rejects_current_object_without_last_modification() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    builder = DiffSnapshotBuilder(
        relation_lookup=_lookup_obj(
            _object(
                identity=identity,
                last_modification=None,
            ),
        ),
    )

    document = EffectDocument(
        version=1,
        source=EffectSource(
            model="ag64",
            class_id="GepKnoten",
            object_id="ch123456AG987654",
        ),
        effects=(
            UpdateAttributeEffect(
                identity=identity,
                attribute_id="status",
                value="active",
            ),
        ),
    )

    with pytest.raises(
        SnapshotValidationError,
    ):
        builder.build(
            document,
        )
