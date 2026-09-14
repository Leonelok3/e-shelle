from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path('rencontres/', include('rencontres.urls')),
    path('accounts/', include(([path('login/', lambda request: HttpResponse('Login'), name='login')], 'accounts'))),
]
