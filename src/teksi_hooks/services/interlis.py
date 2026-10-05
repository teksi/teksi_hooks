import abc
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class InterlisContext:
    """
    Minimal context for an INTERLIS import/export operation.

    The generic INTERLIS service should not know the usage type of a schema.
    That meaning belongs to the calling domain.
    """

    schema: str


class InterlisService(abc.ABC):
    """
    Abstract interface for INTERLIS import/export services.

    Concrete implementations may be QGIS-bound today and headless later.
    """

    @abc.abstractmethod
    def import_xtf(
        self,
        xtf_file: Path,
        context: InterlisContext,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def export_xtf(
        self,
        xtf_file: Path | None,
        export_models: Sequence[str],
        context: InterlisContext,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def find_models(
        self,
        xtf_file: Path,
    ):
        raise NotImplementedError


@dataclass(slots=True)
class InterlisCapability:
    """
    Capability exposing an INTERLIS service implementation to hooks.
    """

    service: InterlisService
