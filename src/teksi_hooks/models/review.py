from __future__ import annotations


from dataclasses import dataclass, field
from typing import Any
from collections.abc import Mapping, Sequence
from enum import StrEnum
from uuid import UUID

from .persistence import (
    PersistenceResult,
)


@dataclass(slots=True)
class ReviewFeature:
    """
    Feature prepared for review artifact export.

    A ReviewFeature is not necessarily a database row. It is a review/export
    representation of a classified change.

    A review writer may turn this into any geospatial storage type that can
    hold its corresponding geometry types
    """

    class_id: str = field(
        metadata={
            "doc": ("Canonical class identifier represented by this review feature.")
        },
    )

    object_id: str = field(
        metadata={
            "doc": ("Canonical object identifier represented by this review feature.")
        },
    )

    attributes: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Canonical attribute values and review metadata attributes "
                "to be exported for this feature."
            )
        },
    )

    geometries: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Geometry values keyed by canonical geometry attribute name. "
                "Multiple geometry attributes are supported because some "
                "canonical classes may expose more than one geometry."
            )
        },
    )


class DiffReviewDecision(
    StrEnum,
):
    """
    Decision taken for a pending diff review job.
    """

    ACCEPT = "accept"
    REJECT = "reject"


class DiffReviewJobStatus(
    StrEnum,
):
    """
    Status of a diff review job after a decision.
    """

    APPLIED = "applied"
    REJECTED = "rejected"


@dataclass(
    frozen=True,
    slots=True,
)
class DiffReviewDecisionResult:
    """
    Result of accepting or rejecting a diff review job.

    An accepted decision includes the result returned by the canonical
    persistence capability. A rejected decision does not invoke persistence
    and therefore has no persistence result.
    """

    job_id: str = field(
        metadata={
            "doc": ("Logical identifier of the diff review job that was resolved.")
        },
    )

    snapshot_id: UUID = field(
        metadata={
            "doc": (
                "Identifier of the immutable diff snapshot to which the "
                "decision was applied."
            )
        },
    )

    decision: DiffReviewDecision = field(
        metadata={"doc": ("Decision taken for the pending review job.")},
    )

    job_status: DiffReviewJobStatus = field(
        metadata={"doc": ("Resulting lifecycle status of the diff review job.")},
    )

    persistence_result: PersistenceResult | None = field(
        default=None,
        metadata={
            "doc": (
                "Aggregate result of persisting accepted canonical changes. "
                "This is None when the review job was rejected."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DiffReviewJob:
    """
    Stored state required to inspect and resolve one diff review job.

    A review job combines job-level lifecycle and validation information with
    the review features generated for the corresponding canonical changes.

    The job is an application-level representation of the data persisted in
    ``tww_diff``. It does not define how accepted changes are physically
    applied to live data.

    Attributes
    ----------
    job_db_id:
        Database-generated identifier of the job metadata row.

        Review-feature rows may use this value as their foreign key to the job
        metadata table.

    job_id:
        Stable external identifier of the review job.

        This identifier is supplied by the calling workflow and is used when
        retrieving, accepting, rejecting or replacing a review job.

    job_status:
        Current lifecycle status of the review job.

        Expected values include ``pending``, ``rejected`` and ``applied``.
        Services resolving the job must reject unsupported transitions.

    validation_success:
        Whether validation of the imported data completed successfully before
        the review job was created.

        A false value indicates that the job must not be applied to live data.

    metadata:
        Workflow and model-specific metadata associated with the review job.

        This may include source-model identifiers, source-file paths, import
        and live schema names, provider and data-owner identifiers, incremental
        import information, mapping provenance and snapshot identifiers.

        Generic review logic must not assign semantics to model-specific
        entries.

    features_by_class:
        Review features grouped by canonical class identifier.

        Each key is a canonical class identifier and each value contains the
        ordered review features stored for that class and job. The features
        contain the reviewed canonical values, imported values, changed
        attributes, findings and review geometries needed by subsequent
        decision and persistence workflows.
    """

    job_db_id: int = field(
        metadata={
            "doc": (
                "Database-generated identifier of the review-job metadata "
                "row. Review-feature rows may reference this value through "
                "their job foreign key."
            )
        },
    )

    job_id: str = field(
        metadata={
            "doc": (
                "Stable external identifier used to retrieve, replace, "
                "accept or reject the review job."
            )
        },
    )

    job_status: str = field(
        metadata={
            "doc": (
                "Current lifecycle status of the review job, such as "
                "'pending', 'rejected' or 'applied'."
            )
        },
    )

    validation_success: bool = field(
        metadata={
            "doc": (
                "Whether validation of the imported data completed "
                "successfully before the review job was created."
            )
        },
    )

    metadata: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Workflow and model-specific metadata associated with the "
                "review job. This may include source models, source files, "
                "schema names, provider context, mapping provenance and "
                "snapshot identifiers."
            )
        },
    )

    features_by_class: Mapping[
        str,
        Sequence[ReviewFeature,],
    ] = field(
        default_factory=dict,
        metadata={
            "doc": (
                "Review features grouped by canonical class identifier. "
                "Feature ordering within each class is preserved."
            )
        },
    )


@dataclass(
    frozen=True,
    slots=True,
)
class DiffSchemaWriteResult:
    """
    Result of writing one diff review job into the ``tww_diff`` schema.

    The result identifies the newly written job and reports the total number
    of review-feature rows persisted across all canonical class tables.

    It does not contain the review features themselves and does not indicate
    that any accepted changes have been applied to live data.

    Attributes
    ----------
    job_db_id:
        Database-generated identifier of the inserted job metadata row.

        This identifier is used internally by review-feature rows as their
        reference to the job.

    job_id:
        Stable external identifier supplied by the review workflow.

        This may be used by callers to retrieve or resolve the stored review
        job without depending on its database-generated identifier.

    row_count:
        Total number of review-feature rows written across all canonical
        class tables for the job.

        The metadata row itself is not included in this count.
    """

    job_db_id: int = field(
        metadata={
            "doc": (
                "Database-generated identifier of the inserted review-job metadata row."
            )
        },
    )

    job_id: str = field(
        metadata={"doc": ("Stable external identifier of the written review job.")},
    )

    row_count: int = field(
        metadata={
            "doc": (
                "Total number of review-feature rows written across all "
                "canonical class tables. The metadata row is not included."
            )
        },
    )
