from .models import SistemaConfiguracion

def sistema_configuracion(request):
    return {
        'sistema_config': SistemaConfiguracion.get_solo(),
    }
