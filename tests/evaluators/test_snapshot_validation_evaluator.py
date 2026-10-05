from datetime import UTC, datetime

from teksi_hooks.capabilities.relation_lookup import (
    InMemoryRelationLookupCapability,
)
from teksi_hooks.evaluators.snapshot import (
    SnapshotValidationEvaluator,
)
from teksi_hooks.models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)
from teksi_hooks.models.diff_snapshot import (
    DiffSnapshot,
    SnapshotMetadata,
    SnapshotObject,
    SnapshotState,
)


def _identity_key(
    identity: CanonicalObjectIdentity,
) -> tuple:
    return (
        identity.class_id,
        tuple(
            sorted(
                identity.attributes.items(),
            )
        ),
    )


def _snapshot(
    objects: tuple[SnapshotObject, ...],
) -> DiffSnapshot:
    return DiffSnapshot(
        metadata=SnapshotMetadata(
            created_at=datetime.now(
                UTC,
            ),
            source_model="ag64",
            source_class_id="GepKnoten",
            source_object_id="ch123456AG987654",
        ),
        objects=objects,
    )


def test_snapshot_validation_accepts_current_object() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    last_modification = (
        datetime(
            2025,
            1,
            1,
            tzinfo=UTC,
        ),
    )

    snapshot = _snapshot(
        objects=(
            SnapshotObject(
                identity=identity,
                last_modification=last_modification,
            ),
        ),
    )

    relation_lookup = InMemoryRelationLookupCapability(
        objects=(
            CanonicalObject(
                identity=identity,
                last_modification=last_modification,
            ),
        ),
    )

    evaluator = SnapshotValidationEvaluator(
        relation_lookup=relation_lookup,
    )

    findings = evaluator.validate(
        snapshot,
    )

    assert findings == ()


def test_snapshot_validation_detects_modified_object() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    snapshot = _snapshot(
        objects=(
            SnapshotObject(
                identity=identity,
                last_modification=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            ),
        ),
    )

    relation_lookup = InMemoryRelationLookupCapability(
        objects=(
            CanonicalObject(
                identity=identity,
                last_modification=datetime(
                    2025,
                    1,
                    2,
                    tzinfo=UTC,
                ),
            ),
        ),
    )

    evaluator = SnapshotValidationEvaluator(
        relation_lookup=relation_lookup,
    )

    findings = evaluator.validate(
        snapshot,
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].identity == identity

    assert findings[0].state == SnapshotState.MODIFIED


def test_snapshot_validation_detects_deleted_object() -> None:
    identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    snapshot = _snapshot(
        objects=(
            SnapshotObject(
                identity=identity,
                last_modification=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            ),
        ),
    )

    relation_lookup = InMemoryRelationLookupCapability()

    evaluator = SnapshotValidationEvaluator(
        relation_lookup=relation_lookup,
    )

    findings = evaluator.validate(
        snapshot,
    )

    assert (
        len(
            findings,
        )
        == 1
    )

    assert findings[0].identity == identity

    assert findings[0].state == SnapshotState.DELETED


def test_snapshot_validation_handles_multiple_objects() -> None:
    current_identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000001",
        },
    )

    modified_identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000002",
        },
    )

    deleted_identity = CanonicalObjectIdentity(
        class_id="wastewater_structure",
        attributes={
            "obj_id": "ch000000ws000003",
        },
    )

    snapshot = _snapshot(
        objects=(
            SnapshotObject(
                identity=current_identity,
                last_modification=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            ),
            SnapshotObject(
                identity=modified_identity,
                last_modification=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            ),
            SnapshotObject(
                identity=deleted_identity,
                last_modification=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            ),
        ),
    )

    relation_lookup = InMemoryRelationLookupCapability(
        objects=(
            CanonicalObject(
                identity=current_identity,
                last_modification=datetime(
                    2025,
                    1,
                    1,
                    tzinfo=UTC,
                ),
            ),
            CanonicalObject(
                identity=modified_identity,
                last_modification=datetime(
                    2025,
                    1,
                    2,
                    tzinfo=UTC,
                ),
            ),
        ),
    )

    evaluator = SnapshotValidationEvaluator(
        relation_lookup=relation_lookup,
    )

    findings = evaluator.validate(
        snapshot,
    )

    assert (
        len(
            findings,
        )
        == 2
    )

    states = {
        _identity_key(
            finding.identity,
        ): finding.state
        for finding in findings
    }

    assert (
        states[
            _identity_key(
                modified_identity,
            )
        ]
        == SnapshotState.MODIFIED
    )

    assert (
        states[
            _identity_key(
                deleted_identity,
            )
        ]
        == SnapshotState.DELETED
    )

    assert (
        _identity_key(
            current_identity,
        )
        not in states
    )
