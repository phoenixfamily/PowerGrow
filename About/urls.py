from django.urls import path
from About.views import *


app_name = 'about'

urlpatterns = [
    path('', about_view, name='about-view'),
    path('api/', About.as_view({'post': 'create', 'get': 'list'}), name='about'),

]
