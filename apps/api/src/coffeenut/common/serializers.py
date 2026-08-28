from typing import Any

from rest_framework import serializers


class OwnedModelSerializer(serializers.ModelSerializer):
    """Base for serializers over :class:`~coffeenut.common.models.OwnedModel`.

    ``owner`` is never writable. A client-supplied value is ignored rather than
    rejected, so the endpoint cannot be used to probe for valid user ids.
    """

    class Meta:
        read_only_fields = ("id", "owner", "share_token", "created_at", "updated_at")

    def create(self, validated_data: dict[str, Any]) -> Any:
        validated_data.pop("owner", None)
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance: Any, validated_data: dict[str, Any]) -> Any:
        validated_data.pop("owner", None)
        return super().update(instance, validated_data)
