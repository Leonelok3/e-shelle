from django.urls import include, path

urlpatterns = [
    path("canada/", include("canada_resume.journey_urls")),
    path('prep/', include('preparation_tests.urls')),
    path('canada-cv/', include('canada_resume.urls')),
    path('jobs/', include('jobs.urls')),
]
