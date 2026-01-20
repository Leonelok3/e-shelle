from rest_framework import serializers
from .models import Session


class SessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ["id", "locale", "source", "created_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Session.objects.create(user=user, **validated_data)


class AnswersPatchSerializer(serializers.Serializer):
    # payload libre clé->valeur
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Payload must be a JSON object.")
        return data


class ScoreSerializer(serializers.Serializer):
    country = serializers.CharField(required=False, allow_blank=True)
