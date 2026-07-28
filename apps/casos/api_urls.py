from rest_framework.routers import DefaultRouter
from .api_views import CasoClinicoViewSet

router = DefaultRouter()
router.register(r'casos', CasoClinicoViewSet, basename='caso')

urlpatterns = router.urls
