from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..capabilities.review import (
    ChangeObjectProvider,
    ReviewGeometryConverter,
)
from ..models.canonical_object import (
    CanonicalObject,
)
from ..models.review import (
    ReviewFeature,
    ReviewGeometry,
)
from ..models.validation import (
    Change,
    ChangeOperation,
    ClassifiedChange,
    ClassifiedChanges,
)


@dataclass(slots=True)
class ChangeReviewExportService:
    """
    Prepare classified changes as review features.

    This service is hook-side and storage-format independent.

    It converts ClassifiedChanges into ReviewFeature objects grouped by
    canonical class. Plugin-side services can then persist those features
    into a storage backend.

    Geometry attributes are metadata-driven through
    geometry_attribute_names_by_class.
    """

    object_provider: ChangeObjectProvider

    geometry_converter: ReviewGeometryConverter

    geometry_attribute_names_by_class: Mapping[
        str,
        Sequence[str],
    ] = field(
        default_factory=dict,
    )

    def export(
        self,
        classified: ClassifiedChanges,
    ) -> dict[
        str,
        list[ReviewFeature],
    ]:
        """
        Build review features grouped by canonical class.
        """

        features_by_class: dict[
            str,
            list[ReviewFeature],
        ] = {}

        for classified_change in self._classified_changes(
            classified,
        ):
            feature = self._feature_for_classified_change(
                classified_change,
            )

            features_by_class.setdefault(
                feature.class_id,
                [],
            ).append(
                feature,
            )

        return features_by_class

    def _classified_changes(
        self,
        classified: ClassifiedChanges,
    ) -> tuple[ClassifiedChange, ...]:
        return (
            *classified.created_objects,
            *classified.altered_objects,
            *classified.deleted_objects,
            *classified.unpermitted_changes,
        )

    def _feature_for_classified_change(
        self,
        classified_change: ClassifiedChange,
    ) -> ReviewFeature:
        change = classified_change.change

        old_object = self.object_provider.old_object(
            change,
        )

        new_object = self.object_provider.new_object(
            change,
        )

        attributes = self._review_attributes(
            classified_change=classified_change,
        )

        geometries = self._review_geometries(
            change=change,
            old_object=old_object,
            new_object=new_object,
        )

        self._add_geometry_changed_flags(
            change=change,
            attributes=attributes,
        )

        return ReviewFeature(
            class_id=change.table_name,
            object_id=change.object_id,
            attributes=attributes,
            geometries=geometries,
        )

    def _review_attributes(
        self,
        classified_change: ClassifiedChange,
    ) -> dict[
        str,
        Any,
    ]:
        change = classified_change.change

        return {
            "identity": self._identity(
                change,
            ),
            "is_created": self._is_created(
                change,
            ),
            "is_altered": self._is_altered(
                change,
            ),
            "is_deleted": self._is_deleted(
                change,
            ),
            "import_values": self._import_values(
                change,
            ),
            "canonical_values": self._canonical_values(
                change,
            ),
            "changed_attributes": self._changed_attributes_payload(
                change,
            ),
            "unpermitted_values": self._unpermitted_values(
                classified_change,
            ),
            "permission_findings": tuple(
                classified_change.metadata.permission_findings,
            ),
            "validation_findings": tuple(
                classified_change.metadata.validation_findings,
            ),
        }

    def _import_values(
        self,
        change: Change,
    ) -> dict[
        str,
        Any,
    ]:
        """
        Return non-geometry imported values for review persistence.
        """

        if self._is_deleted(
            change,
        ):
            return {}

        return self._non_geometry_values(
            class_id=change.table_name,
            values=change.new_values,
        )

    def _canonical_values(
        self,
        change: Change,
    ) -> dict[
        str,
        Any,
    ]:
        """
        Return non-geometry canonical values for review persistence.
        """

        if self._is_created(
            change,
        ):
            return self._non_geometry_values(
                class_id=change.table_name,
                values=change.new_values,
            )

        if self._is_deleted(
            change,
        ):
            return self._non_geometry_values(
                class_id=change.table_name,
                values=change.old_values,
            )

        values = dict(
            change.old_values,
        )

        values.update(
            change.new_values,
        )

        return self._non_geometry_values(
            class_id=change.table_name,
            values=values,
        )

    def _unpermitted_values(
        self,
        classified_change: ClassifiedChange,
    ) -> dict[
        str,
        Any,
    ]:
        """
        Return unpermitted non-geometry values.

        Geometry findings remain represented through geometry change flags and
        finding metadata. The geometry payload itself is stored in
        ``ReviewFeature.geometries``.
        """

        change = classified_change.change

        geometry_attribute_names = set(
            self._geometry_attribute_names(
                change.table_name,
            )
        )

        attribute_names = {
            finding.attribute_name
            for finding in classified_change.metadata.findings
            if (
                finding.attribute_name is not None
                and finding.attribute_name not in geometry_attribute_names
            )
        }

        values: dict[
            str,
            Any,
        ] = {}

        for attribute_name in attribute_names:
            if attribute_name in change.new_values:
                values[attribute_name] = change.new_values[attribute_name]

                continue

            if attribute_name in change.old_values:
                values[attribute_name] = change.old_values[attribute_name]

        return values

    def _changed_attributes_payload(
        self,
        change: Change,
    ) -> tuple[
        dict[
            str,
            Any,
        ],
        ...,
    ]:
        """
        Return changed-attribute metadata without embedding geometry payloads.
        """

        geometry_attribute_names = set(
            self._geometry_attribute_names(
                change.table_name,
            )
        )

        payload: list[
            dict[
                str,
                Any,
            ],
        ] = []

        for attribute in change.changed_attributes:
            attribute_name = attribute.attribute_name

            if attribute_name in geometry_attribute_names:
                payload.append(
                    {
                        "attribute_name": (attribute_name),
                        "is_geometry": True,
                    }
                )

                continue

            payload.append(
                {
                    "attribute_name": (attribute_name),
                    "old_value": (
                        change.old_values.get(
                            attribute_name,
                        )
                    ),
                    "new_value": (
                        change.new_values.get(
                            attribute_name,
                        )
                    ),
                    "is_geometry": False,
                }
            )

        return tuple(
            payload,
        )

    def _review_geometries(
        self,
        *,
        change: Change,
        old_object: CanonicalObject | None,
        new_object: CanonicalObject | None,
    ) -> dict[
        str,
        ReviewGeometry,
    ]:
        """
        Return the review geometries applicable to one change.

        Created and altered objects use their new geometry where available.
        Deleted objects use their old geometry.
        """

        if self._is_created(
            change,
        ):
            return self._new_geometries(
                change=change,
                new_object=new_object,
            )

        if self._is_deleted(
            change,
        ):
            return self._old_geometries(
                change=change,
                old_object=old_object,
            )

        geometries: dict[
            str,
            ReviewGeometry,
        ] = {}

        geometries.update(
            self._old_geometries(
                change=change,
                old_object=old_object,
            )
        )

        geometries.update(
            self._new_geometries(
                change=change,
                new_object=new_object,
            )
        )

        return geometries

    def _old_geometries(
        self,
        *,
        change: Change,
        old_object: CanonicalObject | None,
    ) -> dict[
        str,
        ReviewGeometry,
    ]:
        """
        Return converted geometries representing the old object state.
        """

        values = old_object.values if old_object is not None else change.old_values

        return self._geometry_values_from_mapping(
            class_id=change.table_name,
            values=values,
        )

    def _new_geometries(
        self,
        *,
        change: Change,
        new_object: CanonicalObject | None,
    ) -> dict[
        str,
        ReviewGeometry,
    ]:
        """
        Return converted geometries representing the new object state.
        """

        values = new_object.values if new_object is not None else change.new_values

        return self._geometry_values_from_mapping(
            class_id=change.table_name,
            values=values,
        )

    def _geometry_values_from_mapping(
        self,
        *,
        class_id: str,
        values: Mapping[
            str,
            Any,
        ],
    ) -> dict[
        str,
        ReviewGeometry,
    ]:
        """
        Return configured geometry values as portable review geometries.

        Values already represented as ``ReviewGeometry`` are retained. Other
        provider-specific geometry values are passed through the configured
        geometry converter.
        """

        geometry_attribute_names = set(
            self._geometry_attribute_names(
                class_id,
            )
        )

        geometries: dict[
            str,
            ReviewGeometry,
        ] = {}

        for (
            attribute_id,
            value,
        ) in values.items():
            if attribute_id not in geometry_attribute_names:
                continue

            if value is None:
                continue

            if isinstance(
                value,
                ReviewGeometry,
            ):
                geometry = value

            else:
                geometry = self.geometry_converter.review_geometry(
                    class_id=class_id,
                    attribute_id=attribute_id,
                    value=value,
                )

            if not isinstance(
                geometry,
                ReviewGeometry,
            ):
                raise TypeError(
                    "Review geometry conversion returned "
                    f"{type(geometry)!r} for "
                    f"{class_id!r}.{attribute_id!r}; "
                    "expected ReviewGeometry."
                )

            geometries[attribute_id] = geometry

        return geometries

    def _add_geometry_changed_flags(
        self,
        *,
        change: Change,
        attributes: dict[
            str,
            Any,
        ],
    ) -> None:
        changed_geometry_names = set(
            self._changed_geometry_attributes(
                change,
            )
        )

        for geometry_attribute_name in self._geometry_attribute_names(
            change.table_name,
        ):
            attributes[f"{geometry_attribute_name}_changed"] = (
                geometry_attribute_name in changed_geometry_names
            )

            attributes[f"{geometry_attribute_name}_changed_without_permission"] = (
                geometry_attribute_name in changed_geometry_names
                and bool(
                    attributes["permission_findings"]
                    or attributes["validation_findings"]
                )
            )

    def _changed_geometry_attributes(
        self,
        change: Change,
    ) -> tuple[str, ...]:
        geometry_attribute_names = set(
            self._geometry_attribute_names(
                change.table_name,
            )
        )

        return tuple(
            attribute.attribute_name
            for attribute in change.changed_attributes
            if attribute.attribute_name in geometry_attribute_names
        )

    def _non_geometry_values(
        self,
        *,
        class_id: str,
        values: Mapping[
            str,
            Any,
        ],
    ) -> dict[
        str,
        Any,
    ]:
        """
        Return values excluding configured geometry attributes.
        """

        geometry_attribute_names = set(
            self._geometry_attribute_names(
                class_id,
            )
        )

        return {
            attribute_name: value
            for (
                attribute_name,
                value,
            ) in values.items()
            if attribute_name not in geometry_attribute_names
        }

    def _geometry_attribute_names(
        self,
        class_id: str,
    ) -> tuple[str, ...]:
        return tuple(
            self.geometry_attribute_names_by_class.get(
                class_id,
                (),
            )
        )

    def _identity(
        self,
        change: Change,
    ) -> dict[
        str,
        Any,
    ]:
        """
        Return the complete canonical identity as structured data.
        """

        return {
            "class_id": change.identity.class_id,
            "attributes": dict(
                change.identity.attributes,
            ),
        }

    def _is_created(
        self,
        change: Change,
    ) -> bool:
        return change.operation == ChangeOperation.INSERT

    def _is_altered(
        self,
        change: Change,
    ) -> bool:
        return change.operation == ChangeOperation.UPDATE

    def _is_deleted(
        self,
        change: Change,
    ) -> bool:
        return change.operation == ChangeOperation.DELETE
