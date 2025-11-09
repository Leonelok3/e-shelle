from rest_framework.routers import DefaultRouter
from .views import ProgramViewSet, SessionViewSet

router = DefaultRouter()
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'sessions', SessionViewSet, basename='session')

urlpatterns = router.urls
