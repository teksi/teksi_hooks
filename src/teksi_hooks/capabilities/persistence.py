# src/teksi_hooks/capabilities/persistence.py

from __future__ import annotations

from typing import Protocol

from ..models.persistence import (
    ChangePersistenceDocument,
    PersistenceResult,
)
from ..models.diff_snapshot import (
    DiffSnapshot,
)


class ChangePersistenceCapability(
    Protocol,
):
    """
    Capability for persisting one accepted diff snapshot.

    The snapshot represents the immutable state that was reviewed. The
    persistence document contains the object-level and attribute-level
    decisions made for that exact snapshot.
    """

    def persist_snapshot(
        self,
        snapshot: DiffSnapshot,
        decisions: ChangePersistenceDocument,
    ) -> PersistenceResult:
        """
        Persist one accepted diff snapshot atomically.

        Parameters
        ----------
        snapshot:
            Immutable reviewed snapshot.

        decisions:
            Persistence decisions associated with the reviewed snapshot.
            The document's snapshot identifier must equal
            ``snapshot.snapshot_id``.

        Returns
        -------
        PersistenceResult
            Aggregate result for the completed persistence operation.

        Raises
        ------
        Exception
            If the snapshot and decisions do not match, or if the complete
            snapshot cannot be persisted atomically.
        """

        ...
