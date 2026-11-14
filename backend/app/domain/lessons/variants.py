"""Variant resolution: pick the entry of a `by variant` mapping through a `*VariantMap`."""

from collections.abc import Mapping

from app.domain.lessons.errors import LessonContentError

NO_VARIANT_KEY = "default"


def pick[T](
    options: Mapping[str, T],
    variant: str | None,
    variant_map: Mapping[str, str] | None = None,
) -> T:
    """The entry of `options` for the chosen variant.

    The variant (or `default` for lessons without variants) goes through `variant_map` when it
    has an entry (`both` -> `in_person`), else it is used as is. A key the content does not
    cover is an authoring error, not a user error.
    """
    key = variant if variant is not None else NO_VARIANT_KEY
    if variant_map is not None and key in variant_map:
        key = variant_map[key]
    if key not in options:
        raise LessonContentError(
            f"No entry for variant '{key}'", {"variant": key, "available": sorted(options)}
        )
    return options[key]
