from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..models.validation import (
    Change,
)
from ..models.persistence import (
    ChangePersistenceResult,
)


class ChangePersistenceCapability(
    Protocol,
):
    """
    Atomically persist accepted canonical changes.
    """

    def persist_changes(
        self,
        *,
        changes: Sequence[Change],
    ) -> ChangePersistenceResult:
        """
        Apply accepted canonical changes to live data.

        The operation must be atomic. If any change cannot be applied, no
        change may remain committed.
        """
