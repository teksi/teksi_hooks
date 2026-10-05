from collections.abc import Mapping
from dataclasses import dataclass, field

from .oid import Oid
from .privilege import PrivilegeId


@dataclass(slots=True, frozen=True)
class ProviderPermission:
    """
    Describes the privileges granted to a provider for one data owner.

    Multiple permissions for the same data owner may exist in the parsed
    model. The provider resolver is responsible for merging them into a
    single permission entry per data owner.
    """

    dataowner_oid: Oid = field(
        metadata={
            "doc": ("Identifier of the data owner for which the privileges apply.")
        },
    )

    privileges: frozenset[PrivilegeId] = field(
        metadata={
            "doc": (
                "PrivilegeIds granted to the provider for the corresponding data owner."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class Provider:
    """
    Parsed provider definition.

    A provider represents one organization submitting or maintaining data.
    Its permissions may contain several entries for the same data owner.
    These entries are merged by the provider resolver.
    """

    name: str = field(
        metadata={"doc": ("Human-readable provider name.")},
    )

    organisation_oid: Oid = field(
        metadata={"doc": ("Canonical organization identifier of the provider.")},
    )

    permissions: frozenset[ProviderPermission] = field(
        metadata={
            "doc": (
                "Provider permissions before resolution. Multiple entries "
                "for the same data owner are allowed and are merged during "
                "provider resolution."
            )
        },
    )


@dataclass(slots=True, frozen=True)
class ResolvedProvider:
    """
    Resolved provider definition optimized for runtime privilege checks.

    The resolver groups permissions by data owner and merges privileges for
    duplicate data-owner entries. Runtime code should use this model instead
    of scanning the parsed provider roles directly.
    """

    name: str = field(
        metadata={"doc": ("Human-readable provider name.")},
    )

    organisation_oid: Oid = field(
        metadata={"doc": ("Canonical organization identifier of the provider.")},
    )

    permissions: Mapping[
        Oid,
        frozenset[PrivilegeId],
    ] = field(
        metadata={
            "doc": (
                "Resolved permissions keyed by data-owner identifier. Each "
                "data owner appears at most once."
            )
        },
    )
