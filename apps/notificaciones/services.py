from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.core.audit import registrar_actividad

from .models import Notificacion


def _usuario_valido(usuario):
    return bool(usuario and getattr(usuario, 'pk', None) and getattr(usuario, 'is_active', True))


def _usuarios_unicos(*usuarios):
    vistos = set()
    resultado = []
    for usuario in usuarios:
        if not _usuario_valido(usuario):
            continue
        key = str(usuario.pk)
        if key in vistos:
            continue
        vistos.add(key)
        resultado.append(usuario)
    return resultado


def usuarios_del_paciente(paciente, incluir_tutor=True, incluir_medico=True, incluir_creador=True):
    if not paciente:
        return []
    tutor_usuario = None
    if incluir_tutor and getattr(paciente, 'padre_tutor_id', None):
        tutor_usuario = getattr(paciente.padre_tutor, 'usuario', None)
    return _usuarios_unicos(
        tutor_usuario,
        getattr(paciente, 'medico_asignado', None) if incluir_medico else None,
        getattr(paciente, 'creado_por', None) if incluir_creador else None,
    )


def reverse_or_path(url_name, *args, **kwargs):
    if not url_name:
        return ''
    if url_name.startswith('/') or url_name.startswith('http://') or url_name.startswith('https://'):
        return url_name
    try:
        return reverse(url_name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return url_name


def _objeto_generico(objeto):
    if not objeto or not getattr(objeto, 'pk', None):
        return {}
    return {
        'content_type': ContentType.objects.get_for_model(objeto, for_concrete_model=False),
        'objeto_id': str(objeto.pk),
    }


def _auditar_notificacion(usuario, accion, notificacion, descripcion=''):
    try:
        registrar_actividad(
            usuario=usuario,
            accion=accion,
            modelo='Notificacion',
            modulo='Notificaciones',
            objeto_id=str(notificacion.pk),
            objeto_repr=notificacion.titulo,
            descripcion=descripcion or notificacion.mensaje[:240],
            dedupe_seconds=0,
        )
    except Exception:
        # La notificacion no debe fallar por auditoria auxiliar.
        return None


def crear_notificacion(
    *,
    usuario,
    titulo,
    mensaje,
    tipo=Notificacion.TipoNotificacion.SISTEMA,
    modulo='',
    prioridad=Notificacion.Prioridad.MEDIA,
    accion_url='',
    accion_texto='',
    objeto=None,
    icono_nombre='',
    clave_dedupe='',
    leida=False,
):
    if not _usuario_valido(usuario):
        return None

    datos = {
        'usuario': usuario,
        'tipo': tipo,
        'modulo': modulo,
        'prioridad': prioridad,
        'titulo': titulo[:180],
        'mensaje': mensaje,
        'accion_url': accion_url or '',
        'accion_texto': accion_texto or '',
        'icono_nombre': icono_nombre or '',
        'leida': leida,
        'fecha_lectura': timezone.now() if leida else None,
        **_objeto_generico(objeto),
    }

    with transaction.atomic():
        if clave_dedupe:
            notificacion, creada = Notificacion.objects.select_for_update().get_or_create(
                clave_dedupe=clave_dedupe,
                defaults=datos,
            )
            if not creada:
                campos = []
                for campo, valor in datos.items():
                    if campo in {'usuario', 'leida', 'fecha_lectura'}:
                        continue
                    if getattr(notificacion, campo) != valor:
                        setattr(notificacion, campo, valor)
                        campos.append(campo)
                if campos:
                    notificacion.save(update_fields=campos + ['updated_at'])
                return notificacion
        else:
            notificacion = Notificacion.objects.create(**datos)
            creada = True

    return notificacion


def marcar_notificacion_leida(notificacion, usuario=None, auditar=True):
    cambio = notificacion.marcar_como_leida()
    if cambio and auditar:
        _auditar_notificacion(usuario or notificacion.usuario, 'Notificacion leida', notificacion)
    return cambio


def marcar_notificacion_no_leida(notificacion, usuario=None, auditar=True):
    cambio = notificacion.marcar_como_no_leida()
    if cambio and auditar:
        _auditar_notificacion(usuario or notificacion.usuario, 'Notificacion marcada como no leida', notificacion)
    return cambio


def marcar_todas_leidas(usuario, queryset=None):
    qs = queryset if queryset is not None else Notificacion.objects.filter(usuario=usuario, archivada=False)
    ahora = timezone.now()
    total = qs.filter(leida=False).update(leida=True, fecha_lectura=ahora, updated_at=ahora)
    if total:
        try:
            registrar_actividad(
                usuario=usuario,
                accion='Marcar todas las notificaciones como leidas',
                modelo='Notificacion',
                modulo='Notificaciones',
                descripcion=f'{total} notificaciones marcadas como leidas.',
                dedupe_seconds=0,
            )
        except Exception:
            pass
    return total


def archivar_notificacion(notificacion, usuario=None):
    if notificacion.archivada:
        return False
    notificacion.archivada = True
    notificacion.save(update_fields=['archivada', 'updated_at'])
    _auditar_notificacion(usuario or notificacion.usuario, 'Notificacion archivada', notificacion)
    return True


def registrar_apertura(notificacion, usuario=None):
    marcar_notificacion_leida(notificacion, usuario=usuario)
    _auditar_notificacion(usuario or notificacion.usuario, 'Apertura de notificacion', notificacion)


def _marcar_dedupe_leida(usuario, clave_dedupe):
    ahora = timezone.now()
    return Notificacion.objects.filter(
        usuario=usuario,
        clave_dedupe=clave_dedupe,
        leida=False,
    ).update(leida=True, fecha_lectura=ahora, updated_at=ahora)


def _sync_parent(usuario):
    from apps.documentos.models import SolicitudDocumento
    from apps.pacientes.models import Paciente
    from apps.seguimiento.models import IndicacionMedica

    pacientes = Paciente.objects.filter(padre_tutor__usuario=usuario).select_related('padre_tutor')
    for solicitud in SolicitudDocumento.objects.filter(paciente__in=pacientes).select_related('paciente'):
        clave = f'solicitud:{solicitud.pk}:padre:{usuario.pk}'
        if solicitud.estado in [
            SolicitudDocumento.EstadoSolicitud.PENDIENTE,
            SolicitudDocumento.EstadoSolicitud.CORRECCION,
        ]:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.TipoNotificacion.ALERTA,
                modulo='Documentos',
                prioridad=Notificacion.Prioridad.ALTA if solicitud.estado == SolicitudDocumento.EstadoSolicitud.CORRECCION else Notificacion.Prioridad.MEDIA,
                titulo=f'Estudio Solicitado: {solicitud.titulo}',
                mensaje=(
                    f'El medico ha solicitado "{solicitud.titulo}" para '
                    f'{solicitud.paciente.nombres}. Suba el resultado cuando este disponible.'
                ),
                accion_url=f'/padres/documentos/subir/{solicitud.pk}/',
                accion_texto='Subir resultado',
                objeto=solicitud,
                clave_dedupe=clave,
            )
        else:
            _marcar_dedupe_leida(usuario, clave)

    for indicacion in IndicacionMedica.objects.filter(paciente__in=pacientes).select_related('paciente'):
        clave = f'indicacion:{indicacion.pk}:padre:{usuario.pk}'
        if indicacion.activa:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.TipoNotificacion.SEGUIMIENTO,
                modulo='Seguimiento',
                prioridad=Notificacion.Prioridad.ALTA if indicacion.prioridad == IndicacionMedica.Prioridad.ALTA else Notificacion.Prioridad.MEDIA,
                titulo=f'Nueva indicacion: {indicacion.titulo}',
                mensaje=f'Hay una indicacion activa para {indicacion.paciente.nombres}: {indicacion.descripcion}',
                accion_url=f'/padres/indicaciones/?id={indicacion.pk}',
                accion_texto='Ver indicacion',
                objeto=indicacion,
                clave_dedupe=clave,
            )
        else:
            _marcar_dedupe_leida(usuario, clave)

def _pacientes_scope_personal(usuario):
    from apps.auth_app.models import CustomUser
    from apps.pacientes.models import Paciente

    if usuario.rol == CustomUser.Rol.ADMIN:
        return Paciente.objects.all()
    if usuario.rol in [CustomUser.Rol.PERSONAL_FACCI, CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
        return Paciente.objects.filter(medico_asignado=usuario)
    if usuario.rol == CustomUser.Rol.ONCOLOGO:
        return Paciente.objects.filter(referencias__especialista_destino=usuario).distinct()
    return Paciente.objects.none()


def _sync_personal(usuario):
    from apps.dashboard.models import AlertaClinica
    from apps.documentos.models import SolicitudDocumento
    from apps.padres.models import ReporteSintoma
    from apps.referencias.models import ReferenciaMedica

    pacientes = _pacientes_scope_personal(usuario)

    for reporte in ReporteSintoma.objects.filter(paciente__in=pacientes).select_related('paciente'):
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.SINTOMAS,
            modulo='Pacientes',
            prioridad=Notificacion.Prioridad.ALTA if reporte.gravedad == ReporteSintoma.Gravedad.SEVERA else Notificacion.Prioridad.MEDIA,
            titulo=f'Reporte de sintomas: {reporte.paciente.nombre_completo}',
            mensaje=f'Gravedad: {reporte.gravedad}. Sintomas: {reporte.sintomas_str}. {reporte.descripcion}',
            accion_url=reverse_or_path('pacientes:expediente', pk=reporte.paciente_id),
            accion_texto='Ver expediente',
            objeto=reporte,
            clave_dedupe=f'reporte-sintoma:{reporte.pk}:personal:{usuario.pk}',
        )

    for solicitud in SolicitudDocumento.objects.filter(paciente__in=pacientes).select_related('paciente'):
        clave = f'solicitud:{solicitud.pk}:resultado:{usuario.pk}'
        if solicitud.estado == SolicitudDocumento.EstadoSolicitud.SUBIDO:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.TipoNotificacion.DOCUMENTO,
                modulo='Documentos',
                prioridad=Notificacion.Prioridad.MEDIA,
                titulo=f'Resultado cargado: {solicitud.paciente.nombre_completo}',
                mensaje=f'El resultado para "{solicitud.titulo}" fue cargado y requiere revision.',
                accion_url=reverse_or_path('pacientes:expediente', pk=solicitud.paciente_id),
                accion_texto='Revisar estudio',
                objeto=solicitud,
                clave_dedupe=clave,
            )
        else:
            _marcar_dedupe_leida(usuario, clave)

    abiertas = [AlertaClinica.Estado.PENDIENTE, AlertaClinica.Estado.REVISADA]
    alertas = AlertaClinica.objects.filter(
        paciente__in=pacientes,
        estado__in=abiertas,
        prioridad__in=[AlertaClinica.Prioridad.ALTA, AlertaClinica.Prioridad.CRITICA],
    ).select_related('paciente')
    for alerta in alertas:
        prioridad = (
            Notificacion.Prioridad.CRITICA
            if alerta.prioridad == AlertaClinica.Prioridad.CRITICA
            else Notificacion.Prioridad.ALTA
        )
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.ALERTA_CLINICA,
            modulo='Alertas',
            prioridad=prioridad,
            titulo=alerta.titulo,
            mensaje=alerta.descripcion,
            accion_url=alerta.url_detalle,
            accion_texto='Ver alerta',
            objeto=alerta,
            icono_nombre=alerta.icono,
            clave_dedupe=f'alerta:{alerta.pk}:personal:{usuario.pk}',
        )

    from django.db.models import Q
    from apps.auth_app.models import CustomUser as _CU

    referencias_q = Q(
        especialista_destino=usuario,
        estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
    )
    if usuario.rol in [_CU.Rol.ADMIN, _CU.Rol.ONCOLOGO]:
        referencias_q |= Q(
            especialista_destino__isnull=True,
            estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
            prioridad__in=[ReferenciaMedica.Prioridad.URGENTE, ReferenciaMedica.Prioridad.ALTA],
        )

    referencias = ReferenciaMedica.objects.filter(referencias_q).distinct().select_related('paciente')
    for referencia in referencias:
        es_urgente = referencia.prioridad == ReferenciaMedica.Prioridad.URGENTE
        sin_asignar = not referencia.especialista_destino_id
        prioridad = (
            Notificacion.Prioridad.CRITICA if es_urgente
            else Notificacion.Prioridad.ALTA if referencia.prioridad == ReferenciaMedica.Prioridad.ALTA
            else Notificacion.Prioridad.MEDIA
        )
        titulo = (
            f'{"URGENTE — " if es_urgente else ""}Referencia sin asignar: {referencia.paciente.nombre_completo}'
            if sin_asignar
            else f'{"URGENTE — " if es_urgente else ""}Referencia recibida - {referencia.paciente.nombre_completo}'
        )
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.REFERENCIA,
            modulo='Referencias',
            prioridad=prioridad,
            titulo=titulo,
            mensaje=f'Referencia {referencia.codigo} pendiente hacia {referencia.hospital_destino or "destino sin asignar"}.',
            accion_url=reverse_or_path('referencias:detalle', pk=referencia.pk),
            accion_texto='Ver referencia',
            objeto=referencia,
            icono_nombre='emergency' if es_urgente else '',
            clave_dedupe=f'referencia:{referencia.pk}:{"broadcast" if sin_asignar else "recibida"}:{usuario.pk}',
        )

def sincronizar_notificaciones_usuario(usuario):
    from apps.auth_app.models import CustomUser

    if not _usuario_valido(usuario):
        return
    if usuario.rol == CustomUser.Rol.PADRE_TUTOR:
        _sync_parent(usuario)
    elif usuario.rol in [
        CustomUser.Rol.ADMIN,
        CustomUser.Rol.MEDICO,
        CustomUser.Rol.PEDIATRA,
        CustomUser.Rol.ONCOLOGO,
        CustomUser.Rol.PERSONAL_FACCI,
    ]:
        _sync_personal(usuario)
