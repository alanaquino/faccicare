from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.gestion_view, name='gestion'),
    path('nuevo/', views.nuevo_usuario_view, name='nuevo'),
    path('<uuid:pk>/editar/', views.editar_usuario_view, name='editar'),
    path('<uuid:pk>/toggle/', views.toggle_usuario_view, name='toggle'),
    path('roles/', views.roles_view, name='roles'),
    path('config/', views.configuracion_view, name='configuracion'),
    path('perfil/', views.perfil_view, name='perfil'),
]
