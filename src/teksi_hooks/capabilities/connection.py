# src/teksi_hooks/capabilities/database.py

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol


class DatabaseConnectionFactory(
    Protocol,
):
    """
    Factory for managed database connections.

    The framework does not prescribe a database driver or connection type.
    Implementations determine transaction and cleanup behavior.
    """

    def connection(
        self,
        *,
        autocommit: bool = False,
    ) -> AbstractContextManager[Any]:
        """
            Return a managed database connection.

        commit`` is false, the connection context should commit on
            successful exit and roll back when an exception leaves the context.
        """

        ...
