from django.urls import path
from Home.views import *
from django.conf.urls.static import static
from django.conf import settings


app_name = 'home'

urlpatterns = [
    path('', home_view, name='home-view'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
