from apps.seguimiento.models import validar_fecha_proximo_seguimiento
from apps.seguimiento.models import SeguimientoPaciente
from apps.core.audit import registrar_actividad

def registrar_seguimiento(paciente, autor, *, estado_clinico, observaciones,
                          proxima_fecha_seguimiento, medico_seguimiento=None,
                          lugar_seguimiento=None, peso_kg=None, talla_cm=None,
                          temperatura_c=None, tension_arterial=''):
    validar_fecha_proximo_seguimiento(proxima_fecha_seguimiento)

    seguimiento = SeguimientoPaciente.objects.create(
        paciente=paciente,
        medico=autor,
        medico_seguimiento=medico_seguimiento,
        lugar_seguimiento=lugar_seguimiento,
        estado_clinico=estado_clinico,
        observaciones=observaciones or "Seguimiento clínico registrado.",
        proxima_fecha_seguimiento=proxima_fecha_seguimiento,
        peso_kg=peso_kg,
        talla_cm=talla_cm,
        temperatura_c=temperatura_c,
        tension_arterial=tension_arterial or '',
    )
    
    fecha_str = proxima_fecha_seguimiento.strftime("%d/%m/%Y %H:%M") if proxima_fecha_seguimiento else "sin fecha"
    registrar_actividad(
        usuario=autor,
        accion="Registrar Seguimiento",
        modelo="Paciente",
        objeto_id=str(paciente.id),
        objeto_repr=paciente.nombre_completo,
        descripcion=f'Seguimiento clínico registrado para {paciente.nombre_completo}. Próximo seguimiento: {fecha_str}',
    )
    return seguimiento
