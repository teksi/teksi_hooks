from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID


class IntermediateDataCleanupCapability(
    Protocol,
):
    """
    Capability for deleting intermediate data associated with a diff snapshot.

    Intermediate data may include imported source-model tables, quarantine
    schemas, temporary files or other resources created while constructing a
    review job.

    Implementations must be idempotent. Repeating cleanup for the same
    snapshot must not fail merely because the intermediate data has already
    been deleted.

    The capability does not manage review-job status. The surrounding review
    workflow is responsible for deciding when cleanup may occur.
    """

    def cleanup(
        self,
        *,
        snapshot_id: UUID,
        metadata: Mapping[
            str,
            Any,
        ],
    ) -> None:
        """
        Delete intermediate data associated with one diff snapshot.

        Parameters
        ----------
        snapshot_id:
            Identifier of the immutable diff snapshot whose intermediate data
            must be deleted.

        metadata:
            Workflow metadata describing the intermediate resources associated
            with the snapshot. Implementations may use values such as import
            schema names, source files or model identifiers.

        Raises
        ------
        Exception
            If cleanup cannot be completed.

            Implementations should not fail when the requested resources have
            already been deleted.
        """

        ...
