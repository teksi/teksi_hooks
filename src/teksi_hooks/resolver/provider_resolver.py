from dataclasses import dataclass

from ..models.oid import Oid
from ..models.privilege import PrivilegeId
from ..models.provider import (
    Provider,
    ResolvedProvider,
)


@dataclass(slots=True)
class ProviderResolver:
    """
    Resolves parsed provider definitions into runtime lookup structures.

    Parsed providers may contain multiple permission entries for the same
    data owner. The resolver merges those entries into one privilege set per
    data owner.
    """

    def resolve(
        self,
        provider: Provider,
    ) -> ResolvedProvider:
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
                dataowner_oid: frozenset(privileges)
                for dataowner_oid, privileges in permissions.items()
            },
        )

    def resolve_all(
        self,
        providers: tuple[Provider, ...],
    ) -> dict[Oid, ResolvedProvider]:
        return {
            provider.organisation_oid: self.resolve(
                provider,
            )
            for provider in providers
        }
