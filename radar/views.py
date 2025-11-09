from rest_framework import generics, permissions, filters
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render
from .models import Opportunity, Subscription, Source
from .serializers import OpportunitySerializer, SubscriptionSerializer
from .permissions import IsSubscriberOrReadOnly
from .tasks import refresh_all

class OpportunityList(generics.ListAPIView):
    serializer_class = OpportunitySerializer
    queryset = Opportunity.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["country","category","is_scholarship"]
    search_fields = ["title","eligibility_tags","url","country"]
    ordering_fields = ["score","deadline","created_at"]
    ordering = ["-score"]

class SubscriptionCreate(generics.ListCreateAPIView):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsSubscriberOrReadOnly]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
def admin_refresh(request):
    # lance un refresh async
    refresh_all.delay()
    return Response({"status": "queued"})

def dashboard_page(request):
    return render(request, "dashboard/index.html")
