import pytest

from teksi_hooks.capabilities.relation_lookup import InMemoryRelationLookupCapability
from teksi_hooks.models.canonical_object import CanonicalObject, CanonicalObjectIdentity


@pytest.fixture
def relation_lookup():
    """
    In-memory lookup preloaded for derived-right evaluator tests.
    """

    return InMemoryRelationLookupCapability(
        objects=(
            CanonicalObject(
                identity=CanonicalObjectIdentity(
                    class_id="wastewater_networkelement",
                    attributes={
                        "obj_id": "ch987654NE123456",
                    },
                ),
                values={
                    "fk_wastewater_structure": "ch000000ws000001",
                },
            ),
            CanonicalObject(
                identity=CanonicalObjectIdentity(
                    class_id="reach_point",
                    attributes={
                        "obj_id": "ch000000rp000001",
                    },
                ),
                values={},
            ),
            CanonicalObject(
                identity=CanonicalObjectIdentity(
                    class_id="wastewater_structure",
                    attributes={
                        "obj_id": "ch000000ws000001",
                    },
                ),
                values={
                    "status": "other.planned",
                },
            ),
            CanonicalObject(
                identity=CanonicalObjectIdentity(
                    class_id="reach",
                    attributes={
                        "obj_id": "ch000000re000001",
                    },
                ),
                values={
                    "fk_reach_point_from": "ch000000rp000001",
                    "fk_wastewater_structure": "ch000000ws000001",
                },
            ),
            CanonicalObject(
                identity=CanonicalObjectIdentity(
                    class_id="reach",
                    attributes={
                        "obj_id": "ch000000re000002",
                    },
                ),
                values={
                    "fk_reach_point_to": "ch000000rp000001",
                    "fk_wastewater_structure": "ch000000ws000001",
                },
            ),
        ),
    )
