from django.urls import path
from . import views

app_name = 'casos'

urlpatterns = [
    path('',                                    views.lista_view,         name='lista'),
    path('nuevo/',                              views.crear_view,         name='crear'),
    path('<uuid:pk>/',                          views.detalle_view,       name='detalle'),
    path('<uuid:pk>/editar/',                   views.editar_view,        name='editar'),
    path('<uuid:pk>/cerrar/',                   views.cerrar_caso_view,   name='cerrar'),
    path('<uuid:pk>/notas/agregar/',            views.agregar_nota_view,  name='agregar_nota'),
    path('<uuid:pk>/notas/<uuid:nota_pk>/eliminar/', views.eliminar_nota_view, name='eliminar_nota'),
]
