from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('admin/', views.admin_view, name='admin'),
    path('medico/', views.medico_view, name='medico'),
    path('oncologo/', views.oncologo_view, name='oncologo'),
    path('padre/', views.padre_view, name='padre'),
]
