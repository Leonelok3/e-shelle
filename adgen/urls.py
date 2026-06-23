"""
AdGen — URLs
"""
from django.urls import path
from . import views

app_name = "adgen"

urlpatterns = [
    path("",                      views.DashboardView.as_view(),      name="dashboard"),
    path("create/",               views.CampaignCreateView.as_view(), name="create"),
    path("campaigns/",            views.CampaignListView.as_view(),   name="list"),
    path("<int:pk>/",             views.CampaignDetailView.as_view(), name="detail"),
    path("<int:pk>/generate/",    views.GenerateView.as_view(),       name="generate"),
    path("<int:pk>/export/",      views.ExportContentView.as_view(),  name="export"),
    path("api/<int:pk>/generate/",views.GenerateAPIView.as_view(),    name="api_generate"),
    path("api/<int:pk>/generate-video/start/", views.StartAdVideoView.as_view(), name="api_generate_video_start"),
    path("api/<int:pk>/generate-video/poll/",  views.PollAdVideoView.as_view(),  name="api_generate_video_poll"),
]
