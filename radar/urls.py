from django.urls import path
from .views import OpportunityList, SubscriptionCreate, admin_refresh, dashboard_page

urlpatterns = [
    path("opportunities/", OpportunityList.as_view(), name="opportunities"),
    path("subscriptions/", SubscriptionCreate.as_view(), name="subscriptions"),
    path("admin-refresh/", admin_refresh, name="admin_refresh"),
]
