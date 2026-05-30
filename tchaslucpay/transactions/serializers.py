from rest_framework import serializers

from django.core.exceptions import ValidationError as DjangoValidationError

from tchaslucpay.accounts.models import ClientProfile

from .models import AccountBalance, Transaction, TransactionType
from .services import creer_transaction, deposit, withdraw


class AccountBalanceSerializer(serializers.ModelSerializer):
    total_balance = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = AccountBalance
        fields = ("id", "user", "available_balance", "locked_balance", "total_balance", "currency", "updated_at")
        read_only_fields = fields


class TransactionSerializer(serializers.ModelSerializer):
    amount_display = serializers.CharField(read_only=True)

    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = (
            "id",
            "trid",
            "status",
            "balance_before",
            "balance_after",
            "posted_at",
            "created_at",
            "reversed_transaction",
        )


class PostTransactionSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    transaction_type = serializers.ChoiceField(choices=[TransactionType.DEPOSIT, TransactionType.WITHDRAWAL])
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
    external_reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    metadata = serializers.JSONField(required=False)

    def create(self, validated_data):
        from django.contrib.auth import get_user_model

        account = get_user_model().objects.get(pk=validated_data["account_id"])
        service = deposit if validated_data["transaction_type"] == TransactionType.DEPOSIT else withdraw
        return service(
            account=account,
            amount=validated_data["amount"],
            created_by=self.context["request"].user,
            collector=self.context["request"].user,
            description=validated_data.get("description", ""),
            external_reference=validated_data.get("external_reference", ""),
            metadata=validated_data.get("metadata", {}),
        ).transaction


class CreerTransactionSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    collecteur_id = serializers.IntegerField()
    type_op = serializers.ChoiceField(choices=("DEPOT",))
    montant = serializers.DecimalField(max_digits=18, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)

    def validate_montant(self, value):
        if value < 500:
            raise serializers.ValidationError("Alerte impossible : le depot minimum est de 500 XAF.")
        return value

    def create(self, validated_data):
        # Delegue toute la logique comptable critique au service atomique.
        return creer_transaction(
            client_id=validated_data["client_id"],
            collecteur_id=validated_data["collecteur_id"],
            type_op=validated_data["type_op"],
            montant=validated_data["montant"],
            note=validated_data.get("note"),
        )


class CollecteurTransactionSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    montant = serializers.DecimalField(max_digits=18, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)

    def __init__(self, *args, type_op=None, **kwargs):
        self.type_op = type_op
        super().__init__(*args, **kwargs)

    def validate_client_id(self, value):
        request = self.context["request"]
        collecteur = getattr(request.user, "collecteur_profile", None)
        if collecteur is None:
            raise serializers.ValidationError("Profil collecteur introuvable.")
        if not ClientProfile.objects.filter(pk=value, trusted_collecteur=collecteur).exists():
            raise serializers.ValidationError("Ce client n'est pas assigne a ce collecteur.")
        return value

    def validate_montant(self, value):
        if value < 500:
            raise serializers.ValidationError("Alerte impossible : le depot minimum est de 500 XAF.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return creer_transaction(
                client_id=validated_data["client_id"],
                collecteur_id=request.user.collecteur_profile.pk,
                type_op=self.type_op,
                montant=validated_data["montant"],
                note=validated_data.get("note"),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
