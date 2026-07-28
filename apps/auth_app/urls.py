from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('acceso/padres/', views.login_padres_view, name='login_padres'),
    path('acceso/recuperar/', views.recuperar_view, name='recuperar'),
]
