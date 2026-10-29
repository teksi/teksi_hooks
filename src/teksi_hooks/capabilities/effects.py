# teksi_hooks/capabilities/effects.py

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from ..models.canonical_object import (
    CanonicalObject,
    CanonicalObjectIdentity,
)
from ..models.effects import (
    Effect,
    EffectDocument,
    EffectEvaluationResult,
    EffectProjectionResult,
)
from ..models.mapping import (
    CanonicalViewMapping,
    CanonicalViewProjectionMapping,
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


class CanonicalViewLookupCapability(
    Protocol,
):
    """
    Resolve read-only canonical comparison views.

    Implementations expose ORM classes for querying current canonical state
    using source-model semantics.
    """

    def rows_by_identity(
        self,
        *,
        session: Any,
        view: CanonicalViewMapping,
        identities: Sequence[str,],
    ) -> Mapping[
        str,
        Any,
    ]:
        """
        Return canonical-view rows indexed by configured view identity.

        The result must contain at most one row per requested identity.
        """


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


@runtime_checkable
class CanonicalViewEffectProjector(
    Protocol,
):
    """
    Project a complete source class against a canonical comparison view.

    Implementations are expected to load canonical-view rows in batches and
    return exactly one effect document for every supplied source object.

    The supplied sessions are caller-owned. Implementations must not commit,
    roll back or close either session.
    """

    def project_effects(
        self,
        *,
        source_model: str,
        source_class_id: str,
        source_rows: Sequence[Any,],
        quarantine_session: Any,
        live_session: Any,
        projection: CanonicalViewProjectionMapping,
    ) -> EffectProjectionResult:
        """
        Project all supplied source objects to canonical effects.

        Parameters
        ----------
        source_model:
            External source model containing the source class.

        source_class_id:
            Model-qualified or otherwise unambiguous source-class identifier.

        source_rows:
            Ordered source objects to project.

        quarantine_session:
            Caller-owned session used to resolve quarantine-side references.

        live_session:
            Caller-owned session used to read current canonical state.

        projection:
            Canonical-view projection configuration for the source class.

        Returns
        -------
        EffectProjectionResult
            Effect documents and corresponding source objects in the same
            order as ``source_rows``.

        Raises
        ------
        Exception
            Implementations should raise an explicit error when projection
            configuration is invalid, identities are ambiguous or projection
            cannot produce exactly one document per supplied source object.
        """

        ...


@runtime_checkable
class QuarantineEffectProjectorCapability(
    Protocol,
):
    """
    Project selected quarantine source classes to effect documents.

    Implementations coordinate the projection mechanisms required by a
    quarantine model. This may include declarative attribute mappings,
    canonical-view projections or model-specific projection logic.

    The returned source objects and effect documents must remain positionally
    aligned. Implementations must return exactly one effect document for every
    projected source object.

    Source-class selection belongs to the caller. Implementations must project
    only the supplied source classes and must preserve their supplied order.
    """

    def project_effects(
        self,
        *,
        source_model: str,
        source_class_ids: Sequence[str,],
    ) -> EffectProjectionResult:
        """
        Project selected quarantine source classes to canonical effects.

        Parameters
        ----------
        source_model:
            External source model whose quarantine objects are being
            projected.

        source_class_ids:
            Ordered source-class identifiers to project.

            Each identifier must resolve unambiguously within
            ``source_model``. Implementations must process classes in the
            supplied order.

        Returns
        -------
        EffectProjectionResult
            Effect documents and their corresponding source objects.

            ``documents`` and ``source_objects`` must have equal lengths and
            be positionally aligned. Documents belonging to an earlier source
            class must precede documents belonging to a later source class.

        Raises
        ------
        Exception
            Implementations should raise an explicit error when the source
            model is unsupported, a source-class identifier cannot be
            resolved, projection configuration is missing or projection
            cannot produce exactly one document per source object.
        """

        ...
