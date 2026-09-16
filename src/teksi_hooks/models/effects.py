from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from enum import StrEnum

from .canonical_object import CanonicalObjectIdentity
from .validation import ValidationFinding


class EffectKind(StrEnum):
    UPDATE_ATTRIBUTE = "update_attribute"
    ENFORCE_EXISTS = "enforce_exists"
    ENFORCE_NOT_EXISTS = "enforce_not_exists"


@dataclass(slots=True, frozen=True)
class EffectDocument:
    source: EffectSource = field(
        metadata={"doc": ("Source object from which the effects were generated.")},
    )

    effects: tuple[Effect, ...] = field(
        default_factory=tuple,
        metadata={"doc": ("Effects generated from the source object.")},
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
        metadata={"doc": ("Timestamp when the effect document was created.")},
    )

    version: int = field(
        default=1,
        metadata={"doc": ("Version of the effect-document contract.")},
    )


@dataclass(slots=True, frozen=True)
class EffectSource:
    model: str = field(
        metadata={"doc": ("Source model identifier.")},
    )

    class_id: str = field(
        metadata={"doc": ("Source class identifier.")},
    )

    object_id: str = field(
        metadata={"doc": ("Source object identifier.")},
    )


@dataclass(slots=True, frozen=True)
class Effect:
    """
    Base effect model.
    """


@dataclass(slots=True, frozen=True)
class UpdateAttributeEffect(Effect):
    kind: EffectKind = field(
        default=EffectKind.UPDATE_ATTRIBUTE,
        init=False,
        metadata={"doc": ("Effect kind discriminator.")},
    )

    identity: CanonicalObjectIdentity = field(
        metadata={
            "doc": ("Canonical object identity used to locate the target object.")
        },
    )

    attribute_id: str = field(
        metadata={"doc": ("Canonical attribute identifier being updated.")},
    )

    value: Any = field(
        metadata={
            "doc": ("New value that should be assigned to the target attribute.")
        },
    )


@dataclass(slots=True, frozen=True)
class EnforceExistsEffect(Effect):
    kind: EffectKind = field(
        default=EffectKind.ENFORCE_EXISTS,
        init=False,
        metadata={"doc": ("Effect kind discriminator.")},
    )

    identity: CanonicalObjectIdentity = field(
        metadata={
            "doc": ("Canonical object identity used to locate the target object.")
        },
    )


@dataclass(slots=True, frozen=True)
class EnforceNotExistsEffect(Effect):
    kind: EffectKind = field(
        default=EffectKind.ENFORCE_NOT_EXISTS,
        init=False,
        metadata={"doc": ("Effect kind discriminator.")},
    )

    identity: CanonicalObjectIdentity = field(
        metadata={
            "doc": ("Canonical object identity used to locate the target object.")
        },
    )


class EffectEvaluationStatus(
    StrEnum,
):
    """
    Status resulting from evaluating one desired-state effect.

    An effect describes desired canonical state. Evaluation compares that
    desired state with the currently observed canonical state.

    ``SATISFIED``
        The desired state already holds and no persistence action is required.

    ``REMEDIABLE``
        The desired state does not currently hold, but persistence may safely
        reconcile it after review acceptance.

    ``BLOCKED``
        The desired state does not currently hold and cannot safely be
        reconciled without correcting the source data, live data, mapping or
        workflow context.
    """

    SATISFIED = "satisfied"
    REMEDIABLE = "remediable"
    BLOCKED = "blocked"


@dataclass(
    slots=True,
    frozen=True,
)
class EffectEvaluationResult:
    """
    Evaluation result for one desired-state effect.

    The result refers to an effect by its zero-based index in the corresponding
    effect document. It records whether the effect is already satisfied,
    requires an accepted persistence action, or is blocked.

    Evaluation results do not indicate that persistence has occurred.
    A remediable result means that the effect may be reconciled later by a
    persistence implementation.

    Blocking findings should explain why the effect cannot safely be applied.
    Remediable findings may explain which discrepancy will be resolved during
    persistence. Satisfied effects normally have no findings.
    """

    effect_index: int = field(
        metadata={
            "doc": (
                "Zero-based index of the evaluated effect in the corresponding "
                "EffectDocument.effects sequence."
            )
        },
    )

    status: EffectEvaluationStatus = field(
        metadata={
            "doc": (
                "Evaluation status describing whether the desired-state "
                "effect is satisfied, remediable through persistence, or "
                "blocked."
            )
        },
    )

    findings: tuple[
        ValidationFinding,
        ...,
    ] = field(
        default_factory=tuple,
        metadata={
            "doc": (
                "Ordered validation findings produced while evaluating the "
                "effect. Remediable findings describe discrepancies that may "
                "be reconciled during persistence. Blocking findings explain "
                "why the effect cannot safely be applied."
            )
        },
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
        compare=False,
        hash=False,
        metadata={
            "doc": (
                "Optional implementation-specific evaluation metadata. This "
                "may include observed canonical values, resolved identities, "
                "mapping provenance, target classifications or diagnostic "
                "context. Generic consumers must not assign semantics to "
                "these entries."
            )
        },
    )
