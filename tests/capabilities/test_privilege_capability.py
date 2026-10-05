from teksi_hooks.capabilities.privilege import ResolvedProviderCapability
from teksi_hooks.models.oid import Standardoid


def test_provider_capability_returns_privileges(
    resolved_providers,
) -> None:
    provider = resolved_providers[Standardoid("ch000000geping01")]

    capability = ResolvedProviderCapability(
        provider=provider,
    )

    assert capability.privileges_for(
        Standardoid("ch000000awgde001"),
    ) == frozenset(
        {
            "DBW_WI",
            "DBW_GEP",
        }
    )


def test_provider_capability_checks_privilege(
    resolved_providers,
) -> None:
    provider = resolved_providers[Standardoid("ch000000geping01")]

    capability = ResolvedProviderCapability(
        provider=provider,
    )

    assert capability.has_privilege(
        Standardoid("ch000000awgde001"),
        "DBW_GEP",
    )


def test_provider_capability_returns_empty_for_unknown_dataowner(
    resolved_providers,
) -> None:
    provider = resolved_providers[Standardoid("ch000000geping01")]

    capability = ResolvedProviderCapability(
        provider=provider,
    )

    assert (
        capability.privileges_for(
            Standardoid("ch999999unknown0"),
        )
        == frozenset()
    )
