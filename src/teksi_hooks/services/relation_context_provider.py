from collections.abc import Iterable
from typing import Protocol


class RelationContextProvider(Protocol):
    """
    Provides relation contexts for a concrete source model and schema setup.

    Implementations may use SQLAlchemy, INTERLIS model mappings, QGIS-bound
    importer/exporter structures or any other backend. ChangeLoader should not
    know where the contexts come from.
    """

    def relation_contexts(
        self,
    ) -> Iterable: ...
