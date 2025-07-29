from django.urls import path, include
from rest_framework.routers import DefaultRouter

from Home.views import *
from django.conf.urls.static import static
from django.conf import settings


app_name = 'home'


router = DefaultRouter()
router.register(r'sliders', SliderViewSet, basename='slider')

urlpatterns = [
    path('', home_view, name='home-view'),
    path('api/', include(router.urls)),  # ایندفعه درست!


]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
