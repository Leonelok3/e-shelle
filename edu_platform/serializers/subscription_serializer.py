"""
Sérialiseurs DRF pour l'API EduCam Pro.
"""
try:
    from rest_framework import serializers
    from edu_platform.models import SubscriptionPlan, AccessCode, PaymentTransaction

    class SubscriptionPlanSerializer(serializers.ModelSerializer):
        price_formatted = serializers.ReadOnlyField()
        duration_label = serializers.ReadOnlyField()

        class Meta:
            model = SubscriptionPlan
            fields = ['id', 'name', 'plan_type', 'price_xaf', 'price_formatted',
                      'duration_days', 'duration_label', 'features', 'is_active']

    class AccessCodeSerializer(serializers.ModelSerializer):
        plan = SubscriptionPlanSerializer(read_only=True)
        is_expired = serializers.ReadOnlyField()

        class Meta:
            model = AccessCode
            fields = ['code', 'plan', 'status', 'activated_at', 'expires_at', 'is_expired']

    class PaymentTransactionSerializer(serializers.ModelSerializer):
        amount_formatted = serializers.ReadOnlyField()
        provider_display = serializers.CharField(source='get_provider_display', read_only=True)
        status_display = serializers.CharField(source='get_status_display', read_only=True)

        class Meta:
            model = PaymentTransaction
            fields = ['transaction_id', 'provider', 'provider_display', 'phone_number',
                      'amount_xaf', 'amount_formatted', 'status', 'status_display', 'created_at']

except ImportError:
    pass  # DRF non installé — les sérialiseurs ne sont pas disponibles
