from __future__ import annotations

from pathlib import Path
from typing import Protocol
from collections.abc import Mapping, Sequence

from ..models.validation import (
    Change,
)

from ..models.review import ReviewFeature

from teksi_hooks.models.review import (
    PreparedSource,
)


class ChangeObjectProvider(Protocol):
    """
    Provides canonical attribute and geometry values for changes.

    Implementations may read from:

    - live canonical tables
    - import quarantine schema
    - export quarantine schema
    - QGIS layers
    - later: canonical feature repository
    """

    def old_feature(
        self,
        change: Change,
    ) -> ReviewFeature | None:
        """
        Return the old/live feature for a change.
        Used mainly for deleted objects and diff context.
        """

    def new_feature(
        self,
        change: Change,
    ) -> ReviewFeature | None:
        """
        Return the new/projected feature for a change.
        Used mainly for created and altered objects.
        """


class ReviewArtifactWriter(Protocol):
    """
    Writes grouped review features to an artifact.

    The first implementation will write GeoPackages, but the service should
    not depend on that detail.
    """

    def write(
        self,
        path: Path,
        layers: Mapping[
            str,
            Sequence[ReviewFeature,],
        ],
    ) -> None:
        """
        Write layers to the given path.
        """


class SourcePreparer(Protocol):
    def prepare_source(
        self,
        *,
        job_id: str,
        source: PreparedSource,
    ) -> None:
        """
        Stage one prepared base source for a diff workflow.

        A previously prepared source for the same job identifier is replaced.
        No review job or review feature is persisted by this operation.
        """
        ...

    def prepared_source(
        self,
        *,
        job_id: str,
    ) -> PreparedSource:
        """
        Return the prepared base source for a diff workflow.

        Raises
        ------
        KeyError
            If no prepared source exists for the job identifier.
        """
        ...

    def clear_prepared_source(
        self,
        *,
        job_id: str,
    ) -> None:
        """
        Remove the prepared source for a completed diff workflow.

        Missing prepared sources are ignored so cleanup remains idempotent.
        """
        ...
