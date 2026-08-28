"""``?expand=`` support.

A brew list that returns only ids costs a mobile client one request per related
row. ``?expand=bag.coffee.roaster`` inlines them instead. Responses return ids
by default, so the cheap shape stays the default and the expensive one is opted
into.

Serializers declare what may be expanded; anything else is rejected rather than
ignored, so a typo surfaces as a 400 instead of silently returning ids.
"""

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

# Depth cap. Each level is another join, and nothing in this API is meaningfully
# nested beyond brew -> bag -> coffee -> roaster.
MAX_EXPAND_DEPTH = 4

if TYPE_CHECKING:
    # The mixin is only ever combined with a GenericAPIView. Declaring that
    # for the type checker beats scattering ignores over request/get_serializer.
    from rest_framework.generics import GenericAPIView

    _ViewBase = GenericAPIView
else:
    _ViewBase = object


def parse_expand(raw: str | None) -> set[str]:
    if not raw:
        return set()
    paths = {part.strip() for part in raw.split(",") if part.strip()}
    for path in paths:
        if len(path.split(".")) > MAX_EXPAND_DEPTH:
            raise ValidationError(
                {"expand": f"{path!r} is nested deeper than {MAX_EXPAND_DEPTH} levels."}
            )
    return paths


class ExpandableSerializer(serializers.ModelSerializer):
    """Swaps declared relations for nested serializers on request.

    ``expandable_fields`` maps a field name to a zero-argument factory, so that
    serializers can reference each other without import cycles::

        expandable_fields = {"coffee": lambda: CoffeeSerializer}
    """

    expandable_fields: dict[str, Callable[[], type[serializers.BaseSerializer]]] = {}

    def __init__(self, *args: Any, expand: Iterable[str] | None = None, **kwargs: Any) -> None:
        self._expand = set(expand or ())
        super().__init__(*args, **kwargs)

    def validate_expand_paths(self) -> None:
        """Raise on anything this serializer cannot expand.

        Called once from the viewset against the root serializer; nested levels
        validate themselves as they are constructed.
        """
        for name in {path.split(".")[0] for path in self._expand}:
            if name not in self.expandable_fields:
                allowed = ", ".join(sorted(self.expandable_fields)) or "nothing"
                raise ValidationError(
                    {"expand": f"Cannot expand {name!r} here. Expandable: {allowed}."}
                )

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        direct = {path.split(".")[0] for path in self._expand}

        for name, factory in self.expandable_fields.items():
            if name not in direct or name not in fields:
                continue
            nested = {path.split(".", 1)[1] for path in self._expand if path.startswith(f"{name}.")}
            serializer_class = factory()
            many = isinstance(fields[name], serializers.ManyRelatedField)

            # Read-only: writes always take an id. Accepting a nested object on
            # write would bypass the scoped relation fields that stop one user
            # attaching another user's row.
            child: serializers.BaseSerializer
            if issubclass(serializer_class, ExpandableSerializer):
                child = serializer_class(expand=nested, many=many, read_only=True)
                # many=True wraps the child in a ListSerializer.
                target = getattr(child, "child", child)
                if isinstance(target, ExpandableSerializer):
                    target.validate_expand_paths()
            else:
                if nested:
                    raise ValidationError(
                        {"expand": f"{name!r} has no expandable relations of its own."}
                    )
                child = serializer_class(many=many, read_only=True)
            fields[name] = child

        return fields


class ExpandableViewSetMixin(_ViewBase):
    """Feeds ``?expand=`` into the serializer and validates it."""

    def get_serializer(self, *args: Any, **kwargs: Any) -> Any:
        if "expand" not in kwargs:
            kwargs["expand"] = parse_expand(self.request.query_params.get("expand"))
        serializer = super().get_serializer(*args, **kwargs)
        root = getattr(serializer, "child", serializer)
        if isinstance(root, ExpandableSerializer):
            root.validate_expand_paths()
        return serializer
