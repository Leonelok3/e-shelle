"""
AdGen — URLs
"""
from django.urls import path
from . import views
from . import studio_views
from audio_studio.views import DashboardView as AudioDashboardView

app_name = "adgen"

urlpatterns = [
    path("studio/audio/", AudioDashboardView.as_view(), name="studio_audio"),
    path("studio/abonnements/", studio_views.StudioPricingView.as_view(), name="studio_pricing"),
    path("<int:pk>/studio/media/", studio_views.StudioMediaView.as_view(), name="studio_media"),
    path("",                      views.DashboardView.as_view(),      name="dashboard"),
    path("create/",               views.CampaignCreateView.as_view(), name="create"),
    path("campaigns/",            views.CampaignListView.as_view(),   name="list"),
    path("<int:pk>/",             views.CampaignDetailView.as_view(), name="detail"),
    path("<int:pk>/generate/",    views.GenerateView.as_view(),       name="generate"),
    path("<int:pk>/export/",      views.ExportContentView.as_view(),  name="export"),
    path("<int:pk>/download-video/", views.DownloadVideoView.as_view(), name="download_video"),
    path("api/<int:pk>/generate/",views.GenerateAPIView.as_view(),    name="api_generate"),
    path("api/<int:pk>/generate-video/start/", studio_views.StudioRenderView.as_view(), name="api_generate_video_start"),
    path("api/<int:pk>/generate-video/sora/start/", studio_views.StudioSoraRetiredView.as_view(), name="api_generate_video_sora_start"),
    path("api/<int:pk>/generate-video/poll/",  views.PollAdVideoView.as_view(),  name="api_generate_video_poll"),
]
