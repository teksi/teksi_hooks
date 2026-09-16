# teksi_hooks/capabilities/effects.py

from __future__ import annotations

from typing import Protocol

from ..models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)
from ..models.effects import (
    Effect,
    EffectDocument,
    EffectEvaluationResult,
)


class CanonicalObjectLookupCapability(
    Protocol,
):
    """
    Provide read access to current canonical object state.

    Implementations may read from a database, an in-memory object collection,
    a snapshot or another canonical state provider.
    """

    def canonical_object(
        self,
        identity: CanonicalObjectIdentity,
    ) -> CanonicalObject | None:
        """
        Return the current canonical object for an identity.

        Parameters
        ----------
        identity:
            Canonical identity of the requested object.

        Returns
        -------
        CanonicalObject | None
            The matching canonical object, or None if the object does not
            currently exist.

        Raises
        ------
        Exception
            Implementations should raise an explicit error when the identity
            is invalid or resolves ambiguously. An ambiguous identity must not
            be represented as a missing object.
        """

        ...


class EffectEvaluationPolicy(
    Protocol,
):
    """
    Classify unsatisfied desired-state effects.

    The generic evaluator can determine whether an effect is currently
    satisfied. This policy determines whether an unsatisfied effect may be
    reconciled by the active persistence workflow or must be blocked.

    Implementations may use model-specific class ownership, creation and
    deletion rules, source context or other persistence constraints.
    """

    def unsatisfied_status(
        self,
        *,
        effect: Effect,
        current_object: CanonicalObject | None,
    ) -> EffectEvaluationResult:
        """
        Classify one unsatisfied effect as remediable or blocked.

        The returned result's effect_index may be a placeholder because the
        document evaluator assigns the authoritative document index.
        """

        ...


class EffectEvaluatorCapability(
    Protocol,
):
    """
    Evaluate desired-state effects against current canonical state.
    """

    def evaluate(
        self,
        document: EffectDocument,
    ) -> tuple[
        EffectEvaluationResult,
        ...,
    ]:
        """
        Evaluate every effect in document order.

        The result sequence must contain exactly one result for every effect
        in ``document.effects``. Each result must refer to the effect's
        zero-based index in that sequence.
        """

        ...
