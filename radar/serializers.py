from rest_framework import serializers
from .models import Opportunity, Subscription

class OpportunitySerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id","title","country","category","is_scholarship","url","deadline",
            "cost_min","cost_max","currency","eligibility_tags","score",
            "source","source_name","created_at","updated_at"
        ]

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["id","country_filter","category_filter","min_score","active"]
