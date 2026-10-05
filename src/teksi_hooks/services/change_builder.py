from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.canonical_object import (
    CanonicalObject,
)
from ..models.effects import (
    Effect,
    EnforceExistsEffect,
    EnforceNotExistsEffect,
    UpdateAttributeEffect,
)
from ..models.validation import (
    Change,
    ChangeOperation,
)


@dataclass(slots=True)
class ChangeBuilder:
    """
    Builds canonical changes from effects applied to a current object.
    """

    def build(
        self,
        *,
        current_object: CanonicalObject | None,
        effects: tuple[Effect, ...],
    ) -> Change:
        if not effects:
            raise ValueError("At least one effect is required.")

        reference = effects[0].identity

        old_values: dict[
            str,
            Any,
        ] = (
            {}
            if current_object is None
            else dict(
                current_object.values,
            )
        )

        new_values = dict(
            old_values,
        )

        for effect in effects:
            self._apply_effect(
                new_values,
                effect,
            )

        operation = (
            ChangeOperation.INSERT if current_object is None else ChangeOperation.UPDATE
        )

        return Change(
            table_name=reference.class_id,
            object_id=self._object_id(
                reference.attributes,
            ),
            operation=operation,
            old_values=old_values,
            new_values=new_values,
        )

    def _apply_effect(
        self,
        values: dict[str, Any],
        effect: Effect,
    ) -> None:
        match effect:
            case UpdateAttributeEffect():
                values[effect.attribute_id] = effect.value

            case EnforceExistsEffect():
                return

            case EnforceNotExistsEffect():
                return

            case _:
                raise TypeError(f"Unsupported effect type: {type(effect)!r}")

    def _object_id(
        self,
        identity: dict[str, Any],
    ) -> str:
        if "obj_id" in identity:
            return str(
                identity["obj_id"],
            )

        if len(identity) == 1:
            return str(next(iter(identity.values())))

        raise ValueError("Cannot derive object_id from identity.")
