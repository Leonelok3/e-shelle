from django.urls import include, path

urlpatterns = [
    path('prep/', include('preparation_tests.urls')),
    path('canada-cv/', include('canada_resume.urls')),
    path('jobs/', include('jobs.urls')),
]
