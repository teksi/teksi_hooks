from dataclasses import dataclass, field

from ..models.oid import Oid
from ..models.privilege import PrivilegeId
from ..models.provider import (
    Provider,
    ResolvedProvider,
)


@dataclass(slots=True)
class ResolvedProviderCapability:
    """
    Runtime lookup capability for provider privileges.

    This capability wraps a `ResolvedProvider` and provides convenience
    methods for checking which privileges the provider has for a given
    data owner.

    The wrapped provider should already be resolved, meaning that duplicate
    permission entries for the same data owner have been merged.
    """

    provider: ResolvedProvider = field(
        metadata={
            "doc": (
                "Resolved provider definition containing permissions grouped "
                "by data-owner identifier."
            )
        },
    )

    def privileges_for(
        self,
        dataowner_oid: Oid,
    ) -> frozenset:
        """
        Return all privileges granted to this provider for a data owner.

        Parameters
        ----------
        dataowner_oid:
            Identifier of the data owner for which privileges should be
            retrieved.

        Returns
        -------
        frozenset[PrivilegeId]
            Privileges granted to the provider for the given data owner.
            Returns an empty set if the provider has no permissions for that
            data owner.
        """

        return self.provider.permissions.get(
            dataowner_oid,
            frozenset(),
        )

    def has_privilege(
        self,
        dataowner_oid: Oid,
        privilege: PrivilegeId,
    ) -> bool:
        """
        Check whether this provider has a specific privilege for a data owner.

        Parameters
        ----------
        dataowner_oid:
            Identifier of the data owner.

        privilege:
            Privilege to check.

        Returns
        -------
        bool
            True if the provider has the privilege for the given data owner,
            otherwise False.
        """

        return privilege in self.privileges_for(
            dataowner_oid,
        )


class ProviderResolver:
    """
    Resolves parsed provider definitions into runtime lookup structures.

    The parsed provider model may contain multiple permission entries for the
    same data owner. The resolver merges those entries into a single privilege
    set per data owner so runtime privilege checks can be performed with a
    direct dictionary lookup.
    """

    def resolve(
        self,
        provider: Provider,
    ) -> ResolvedProvider:
        """
        Resolve a provider into a runtime-optimized provider definition.

        Parameters
        ----------
        provider:
            Parsed provider definition.

        Returns
        -------
        ResolvedProvider
            Provider definition with permissions grouped by data owner and
            duplicate privilege entries merged.
        """

        permissions: dict[
            Oid,
            set[PrivilegeId],
        ] = {}

        for permission in provider.permissions:
            permissions.setdefault(
                permission.dataowner_oid,
                set(),
            ).update(
                permission.privileges,
            )

        return ResolvedProvider(
            name=provider.name,
            organisation_oid=provider.organisation_oid,
            permissions={
                oid: frozenset(privileges) for oid, privileges in permissions.items()
            },
        )
