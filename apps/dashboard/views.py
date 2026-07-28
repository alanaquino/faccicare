from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.core.decorators import solo_personal, roles_requeridos, requiere_acceso
from apps.core.models import CentroSalud, LogActividad
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaMedica
from apps.reportes.models import ReporteGenerado
from apps.seguimiento.models import SeguimientoPaciente
from apps.auth_app.models import CustomUser

from .models import AlertaClinica
from .matrices_services import (
    build_matrices_report,
    matrices_pdf_filename,
    render_matrices_csv,
    render_matrices_pdf,
)
from .services import ESTADOS_ABIERTOS, generar_alertas_pendientes, resumen_alertas


def _centros_salud_data():
    return CentroSalud.objects.all().order_by('nombre')


def _alertas_queryset(user=None):
    alertas_qs = AlertaClinica.objects.select_related(
        'paciente',
        'cribado',
        'referencia',
        'seguimiento',
        'documento',
        'solicitud_documento',
        'revisado_por',
    )

    if user and user.is_authenticated:
        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            alertas_qs = alertas_qs.filter(
                Q(paciente__medico_asignado=user) |
                Q(paciente__creado_por=user) |
                Q(referencia__medico_referente=user) |
                Q(seguimiento__medico=user) |
                Q(documento__subido_por=user) |
                Q(solicitud_documento__medico_solicitante=user)
            )
        elif user.rol == CustomUser.Rol.ONCOLOGO:
            alertas_qs = alertas_qs.filter(
                Q(referencia__especialista_destino=user) |
                Q(paciente__referencias__especialista_destino=user) |
                Q(seguimiento__medico=user)
            ).distinct()
    return alertas_qs.distinct()


def _alertas_data(user=None):
    return _alertas_queryset(user).filter(estado__in=ESTADOS_ABIERTOS).order_by('-fecha_creacion')


def _dashboard_data(user=None):
    hoy = timezone.localdate()
    generar_alertas_pendientes()
    alertas_qs = _alertas_queryset(user)
    alertas_resumen = resumen_alertas(alertas_qs)

    pacientes_qs = Paciente.objects.all()
    referencias_qs = ReferenciaMedica.objects.all()
    seguimientos_qs = SeguimientoPaciente.objects.all()

    if user and user.is_authenticated:
        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ENFERMERA]:
            pacientes_qs = pacientes_qs.filter(
                Q(medico_asignado=user) | Q(creado_por=user)
            )
            referencias_qs = referencias_qs.filter(
                Q(medico_referente=user) |
                Q(paciente__medico_asignado=user) |
                Q(paciente__creado_por=user)
            )
            seguimientos_qs = seguimientos_qs.filter(
                Q(paciente__medico_asignado=user) | Q(paciente__creado_por=user)
            )
        elif user.rol == CustomUser.Rol.ONCOLOGO:
            pacientes_qs = pacientes_qs.filter(
                referencias__especialista_destino=user
            ).distinct()
            referencias_qs = referencias_qs.filter(especialista_destino=user)
            seguimientos_qs = seguimientos_qs.filter(
                paciente__referencias__especialista_destino=user
            ).distinct()

    referencias_pendientes = referencias_qs.filter(
        estado=ReferenciaMedica.EstadoReferencia.PENDIENTE
    ).count()
    referencias_criticas = referencias_qs.filter(
        prioridad__in=[ReferenciaMedica.Prioridad.ALTA, ReferenciaMedica.Prioridad.URGENTE]
    ).count()
    casos_criticos = seguimientos_qs.filter(requiere_hospitalizacion=True).count()

    return {
        'total_pacientes': pacientes_qs.count(),
        'pacientes_activos': pacientes_qs.exclude(
            estado_actual__in=[
                Paciente.EstadoPaciente.FINALIZADO,
                Paciente.EstadoPaciente.DESCARTADO,
            ]
        ).count(),
        'total_centros_salud': CentroSalud.objects.count(),
        'total_referencias': referencias_qs.count(),
        'referencias_pendientes': referencias_pendientes,
        'referencias_criticas': referencias_criticas,
        'total_seguimientos': seguimientos_qs.count(),
        'casos_criticos': casos_criticos,
        'seguimientos_hoy': seguimientos_qs.filter(
            fecha_seguimiento__date=hoy
        ).count(),
        'total_alertas': alertas_resumen['abiertas'],
        'alertas_pendientes': alertas_resumen['pendientes'],
        'alertas_criticas_pendientes': alertas_resumen['criticas'],
        'alertas_alta_prioridad': alertas_resumen['alta'],
        'alertas_vencidas': alertas_resumen['vencidas'],
    }


def _build_datos_grafica(user):
    """Calcula distribución de pacientes por provincia con porcentaje relativo al máximo."""
    qs = Paciente.objects.all()
    if hasattr(user, 'rol'):
        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ENFERMERA]:
            qs = qs.filter(Q(medico_asignado=user) | Q(creado_por=user))
        elif user.rol == CustomUser.Rol.ONCOLOGO:
            qs = qs.filter(referencias__especialista_destino=user).distinct()
    prov = list(qs.values('provincia').annotate(casos=Count('id')).order_by('-casos')[:6])
    if not prov:
        return []
    max_c = prov[0]['casos'] or 1
    return [
        {
            'provincia': p['provincia'],
            'casos': p['casos'],
            'porcentaje': max(5, round(p['casos'] / max_c * 100)),
            'alpha': f"{p['casos'] / max_c * 0.7 + 0.3:.2f}",
        }
        for p in prov
    ]


def _get_top_provincia(user):
    """Retorna el nombre de la provincia con más pacientes."""
    qs = Paciente.objects.all()
    if hasattr(user, 'rol'):
        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            qs = qs.filter(Q(medico_asignado=user) | Q(creado_por=user))
    row = qs.values('provincia').annotate(casos=Count('id')).order_by('-casos').first()
    return row['provincia'] if row else '—'


@login_required
@solo_personal
def dashboard_view(request):
    stats_data = _dashboard_data(request.user)
    stats = [
        {'label': 'Total pacientes', 'valor': stats_data['total_pacientes'], 'icono': 'groups', 'color': 'primary', 'bg_icon': 'surface-container-low'},
        {'label': 'Referencias pendientes', 'valor': stats_data['referencias_pendientes'], 'icono': 'send', 'color': 'secondary', 'bg_icon': 'secondary-fixed'},
        {'label': 'Alertas criticas', 'valor': stats_data['alertas_criticas_pendientes'], 'icono': 'warning', 'color': 'error', 'bg_icon': 'error-container'},
        {'label': 'Alertas vencidas', 'valor': stats_data['alertas_vencidas'], 'icono': 'event_busy', 'color': 'error', 'bg_icon': 'error-container'},
    ]
    for stat in stats:
        stat.update({'tendencia': None, 'tendencia_icono': None, 'badge_bg': None, 'badge_color': None})

    pacientes_qs = Paciente.objects.select_related('medico_asignado', 'padre_tutor__usuario')
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        pacientes_qs = pacientes_qs.filter(
            Q(medico_asignado=request.user) | Q(creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        pacientes_qs = pacientes_qs.filter(
            referencias__especialista_destino=request.user
        ).distinct()

    referencias_qs = ReferenciaMedica.objects.select_related('paciente').filter(
        estado=ReferenciaMedica.EstadoReferencia.PENDIENTE
    )
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        referencias_qs = referencias_qs.filter(
            Q(medico_referente=request.user) |
            Q(paciente__medico_asignado=request.user) |
            Q(paciente__creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        referencias_qs = referencias_qs.filter(especialista_destino=request.user)

    alertas_qs = _alertas_data(request.user)
    alertas_resumen = resumen_alertas(_alertas_queryset(request.user))

    context = {
        'titulo_pagina': 'Dashboard Clinico',
        'usuario_nombre': request.user.nombre_completo if request.user.is_authenticated else 'Equipo clinico',
        'saludo': 'Bienvenido',
        'rol': request.user.get_rol_display() if request.user.is_authenticated else 'Usuario',
        'stats': stats,
        'resumen': stats_data,
        'pacientes_recientes': pacientes_qs[:5],
        'alertas_criticas': [
            {
                'titulo': alerta.titulo,
                'tiempo': alerta.fecha_creacion.strftime('%d/%m/%Y'),
                'descripcion': alerta.descripcion,
                'color': 'error' if alerta.prioridad == AlertaClinica.Prioridad.CRITICA else 'secondary',
                'acciones': ['Ver detalle'],
                'detalle_url': alerta.url_detalle,
                'alerta_id': alerta.id,
            }
            for alerta in alertas_qs[:5]
        ],
        'alertas_resumen': alertas_resumen,
        'pendientes': [
            {'nombre': ref.paciente.nombre_completo, 'detalle': ref.motivo_referencia[:90], 'referencia_id': ref.id}
            for ref in referencias_qs[:5]
        ],
        'datos_grafica': _build_datos_grafica(request.user),
        'top_provincia': _get_top_provincia(request.user),
        'ultima_actualizacion': timezone.localtime().strftime('%I:%M %p').lstrip('0'),
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
@roles_requeridos('ADMIN')
def admin_view(request):
    return dashboard_view(request)


@login_required
@roles_requeridos('MEDICO', 'PEDIATRA', 'ADMIN')
def medico_view(request):
    return dashboard_view(request)


@login_required
@roles_requeridos('ONCOLOGO', 'ADMIN')
def oncologo_view(request):
    return dashboard_view(request)


@login_required
@roles_requeridos('PADRE_TUTOR')
def padre_view(request):
    context = {
        'titulo_pagina': 'Mi Panel Familiar',
        'usuario_nombre': request.user.nombre_completo if request.user.is_authenticated else 'Familia',
        'saludo': 'Hola',
        'rol': 'Padre/Tutor',
    }
    return render(request, 'dashboard/padre.html', context)


@login_required
@solo_personal
def centros_salud_view(request):
    if request.method == 'POST':
        if request.user.rol != CustomUser.Rol.ADMIN:
            messages.error(request, 'Su rol no tiene autorización para agregar o editar centros de salud.')
            return redirect('centros_salud')

        centro_id = request.POST.get('centro_id')
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            if centro_id:
                centro = get_object_or_404(CentroSalud, pk=centro_id)
            else:
                centro = CentroSalud()
            centro.nombre = nombre
            centro.tipo = request.POST.get('tipo', CentroSalud.Tipo.HOSPITAL)
            centro.provincia = request.POST.get('provincia', '')
            centro.municipio = request.POST.get('municipio', '')
            centro.direccion = request.POST.get('direccion', '')
            centro.telefono = request.POST.get('telefono', '')
            centro.correo = request.POST.get('correo', '')
            centro.activo = request.POST.get('activo') == 'on'
            lat_val = request.POST.get('latitud')
            lng_val = request.POST.get('longitud')
            if lat_val is not None:
                lat_val = lat_val.strip().replace(',', '.')
                try:
                    centro.latitud = float(lat_val) if lat_val else None
                except ValueError:
                    centro.latitud = None
            if lng_val is not None:
                lng_val = lng_val.strip().replace(',', '.')
                try:
                    centro.longitud = float(lng_val) if lng_val else None
                except ValueError:
                    centro.longitud = None
            centro.save()
            messages.success(request, 'Centro de salud guardado correctamente.')
        return redirect('centros_salud')

    centros = _centros_salud_data()
    search_query = request.GET.get('q', '').strip()

    if search_query:
        centros = centros.filter(
            Q(nombre__icontains=search_query) |
            Q(provincia__icontains=search_query) |
            Q(municipio__icontains=search_query) |
            Q(direccion__icontains=search_query) |
            Q(telefono__icontains=search_query) |
            Q(correo__icontains=search_query)
        )

    import json
    centros_geojson = json.dumps([
        {
            'id': c.id,
            'nombre': c.nombre,
            'tipo': c.get_tipo_display(),
            'tipo_raw': c.tipo,
            'provincia': c.provincia,
            'municipio': c.municipio,
            'direccion': c.direccion,
            'telefono': c.telefono,
            'activo': c.activo,
            'lat': c.latitud,
            'lng': c.longitud,
        }
        for c in centros if c.latitud and c.longitud
    ])

    return render(
        request,
        'dashboard/centros_salud.html',
        {
            'titulo_pagina': 'Centros de Salud',
            'centros': centros,
            'total': centros.count(),
            'tipos': CentroSalud.Tipo.choices,
            'centros_geojson': centros_geojson,
            'sin_coordenadas': centros.filter(Q(latitud__isnull=True) | Q(longitud__isnull=True)).count(),
            'filtro_search': search_query,
        },
    )


@login_required
@roles_requeridos('ADMIN')
def editar_centro_view(request, pk):
    centro = get_object_or_404(CentroSalud, pk=pk)

    if request.method == 'POST':
        centro.nombre   = request.POST.get('nombre', '').strip() or centro.nombre
        centro.tipo     = request.POST.get('tipo', centro.tipo)
        centro.provincia= request.POST.get('provincia', '')
        centro.municipio= request.POST.get('municipio', '')
        centro.direccion= request.POST.get('direccion', '')
        centro.telefono = request.POST.get('telefono', '')
        centro.correo   = request.POST.get('correo', '')
        centro.activo   = request.POST.get('activo') == 'on'

        centro.camas_disponibles = int(request.POST.get('camas_disponibles', 0) or 0)
        centro.camas_total       = int(request.POST.get('camas_total', 0) or 0)
        centro.estado_derivacion = request.POST.get('estado_derivacion', CentroSalud.EstadoDerivacion.DISPONIBLE)
        centro.medicos_titulares = int(request.POST.get('medicos_titulares', 0) or 0)
        centro.entrenados_facci  = int(request.POST.get('entrenados_facci', 0) or 0)

        centro.esp_oncologia_pediatrica  = 'esp_oncologia_pediatrica' in request.POST
        centro.esp_pediatria_general     = 'esp_pediatria_general' in request.POST
        centro.esp_imagenes_diagnosticas = 'esp_imagenes_diagnosticas' in request.POST
        centro.esp_laboratorio_avanzado  = 'esp_laboratorio_avanzado' in request.POST

        lat = request.POST.get('latitud')
        lng = request.POST.get('longitud')
        if lat is not None:
            lat = lat.strip().replace(',', '.')
            try:
                centro.latitud = float(lat) if lat else None
            except ValueError:
                centro.latitud = None
        if lng is not None:
            lng = lng.strip().replace(',', '.')
            try:
                centro.longitud = float(lng) if lng else None
            except ValueError:
                centro.longitud = None

        centro.save()
        messages.success(request, f'Centro "{centro.nombre}" actualizado correctamente.')
        return redirect('centros_salud')

    import json
    geo = json.dumps({'lat': centro.latitud, 'lng': centro.longitud}) if centro.latitud else 'null'

    return render(request, 'dashboard/editar_centro.html', {
        'titulo_pagina': f'Editar — {centro.nombre}',
        'centro': centro,
        'tipos': CentroSalud.Tipo.choices,
        'estados_derivacion': CentroSalud.EstadoDerivacion.choices,
        'centro_geo': geo,
    })


@login_required
@solo_personal
def ver_centro_view(request, pk):
    centro = get_object_or_404(CentroSalud, pk=pk)

    disponibilidad_porcentaje = 0
    if centro.camas_total > 0:
        disponibilidad_porcentaje = int((centro.camas_disponibles / centro.camas_total) * 100)

    import json
    geo = json.dumps({'lat': centro.latitud, 'lng': centro.longitud}) if centro.latitud else 'null'

    return render(request, 'dashboard/ver_centro.html', {
        'titulo_pagina': centro.nombre,
        'centro': centro,
        'disponibilidad_porcentaje': disponibilidad_porcentaje,
        'centro_geo': geo,
    })


@login_required
@requiere_acceso('puede_ver_alertas')
def alertas_view(request):
    generar_alertas_pendientes()
    base_qs = _alertas_queryset(request.user)
    alertas = base_qs

    prioridad = request.GET.get('prioridad', '').strip()
    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    grupo = request.GET.get('grupo', '').strip()
    paciente = request.GET.get('paciente', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    if prioridad in AlertaClinica.Prioridad.values:
        alertas = alertas.filter(prioridad=prioridad)
    if estado in AlertaClinica.Estado.values:
        alertas = alertas.filter(estado=estado)
    if tipo in AlertaClinica.TipoAlerta.values:
        alertas = alertas.filter(tipo_alerta=tipo)
    if grupo == 'cribado':
        alertas = alertas.filter(
            tipo_alerta__in=[
                AlertaClinica.TipoAlerta.SINTOMAS_ALARMA,
                AlertaClinica.TipoAlerta.SOSPECHOSO_SIN_REFERENCIA,
            ]
        )
    elif grupo == 'seguimiento':
        alertas = alertas.filter(
            tipo_alerta__in=[
                AlertaClinica.TipoAlerta.REFERENCIA_SIN_SEGUIMIENTO,
                AlertaClinica.TipoAlerta.SEGUIMIENTO_PENDIENTE,
            ]
        )
    if paciente:
        alertas = alertas.filter(
            Q(paciente__nombres__icontains=paciente) |
            Q(paciente__apellidos__icontains=paciente) |
            Q(paciente__codigo_paciente__icontains=paciente)
        )

    fecha_desde_dt = parse_date(fecha_desde) if fecha_desde else None
    fecha_hasta_dt = parse_date(fecha_hasta) if fecha_hasta else None
    if fecha_desde_dt:
        alertas = alertas.filter(fecha_creacion__date__gte=fecha_desde_dt)
    if fecha_hasta_dt:
        alertas = alertas.filter(fecha_creacion__date__lte=fecha_hasta_dt)

    alertas = list(alertas.order_by('estado', '-fecha_creacion'))
    total = len(alertas)
    urgentes_count = base_qs.filter(
        estado__in=ESTADOS_ABIERTOS,
        prioridad=AlertaClinica.Prioridad.CRITICA,
    ).count()
    cribados_count = base_qs.filter(
        estado__in=ESTADOS_ABIERTOS,
        tipo_alerta__in=[
            AlertaClinica.TipoAlerta.SINTOMAS_ALARMA,
            AlertaClinica.TipoAlerta.SOSPECHOSO_SIN_REFERENCIA,
        ],
    ).count()
    seguimientos_count = base_qs.filter(
        estado__in=ESTADOS_ABIERTOS,
        tipo_alerta__in=[
            AlertaClinica.TipoAlerta.REFERENCIA_SIN_SEGUIMIENTO,
            AlertaClinica.TipoAlerta.SEGUIMIENTO_PENDIENTE,
        ],
    ).count()
    return render(
        request,
        'dashboard/alertas.html',
        {
            'titulo_pagina': 'Alertas Clinicas',
            'alertas': alertas,
            'alerta_principal': alertas[0] if total else None,
            'alerta_secundaria': alertas[1] if total > 1 else None,
            'total': total,
            'urgentes_count': urgentes_count,
            'cribados_count': cribados_count,
            'seguimientos_count': seguimientos_count,
            'resumen_alertas': resumen_alertas(base_qs),
            'prioridades': AlertaClinica.Prioridad.choices,
            'estados': AlertaClinica.Estado.choices,
            'tipos_alerta': AlertaClinica.TipoAlerta.choices,
            'filtros': {
                'prioridad': prioridad,
                'estado': estado,
                'tipo': tipo,
                'grupo': grupo,
                'paciente': paciente,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
            },
        },
    )


def _redirect_alertas(request):
    next_url = request.POST.get('next')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('alertas')


def _alerta_autorizada(request, pk):
    return get_object_or_404(_alertas_queryset(request.user), pk=pk)


@login_required
@requiere_acceso('puede_ver_alertas')
@require_POST
def revisar_alerta_view(request, pk):
    alerta = _alerta_autorizada(request, pk)
    if alerta.estado == AlertaClinica.Estado.PENDIENTE:
        alerta.estado = AlertaClinica.Estado.REVISADA
        alerta.fecha_revision = timezone.now()
        alerta.revisado_por = request.user
        alerta.save(update_fields=['estado', 'fecha_revision', 'revisado_por', 'updated_at'])
        messages.success(request, 'Alerta marcada como revisada.')
    else:
        messages.info(request, 'La alerta ya no esta pendiente.')
    return _redirect_alertas(request)


@login_required
@requiere_acceso('puede_ver_alertas')
@require_POST
def resolver_alerta_view(request, pk):
    alerta = _alerta_autorizada(request, pk)
    comentario = request.POST.get('comentario', '').strip()
    if not comentario:
        messages.error(request, 'Agrega un comentario para resolver la alerta.')
        return _redirect_alertas(request)

    alerta.estado = AlertaClinica.Estado.RESUELTA
    alerta.fecha_revision = timezone.now()
    alerta.revisado_por = request.user
    alerta.comentario_cierre = comentario
    alerta.save(update_fields=['estado', 'fecha_revision', 'revisado_por', 'comentario_cierre', 'updated_at'])
    messages.success(request, 'Alerta resuelta correctamente.')
    return _redirect_alertas(request)


@login_required
@requiere_acceso('puede_ver_alertas')
@require_POST
def descartar_alerta_view(request, pk):
    alerta = _alerta_autorizada(request, pk)
    comentario = request.POST.get('comentario', '').strip()
    if not comentario:
        messages.error(request, 'Agrega una justificacion para descartar la alerta.')
        return _redirect_alertas(request)

    alerta.estado = AlertaClinica.Estado.DESCARTADA
    alerta.fecha_revision = timezone.now()
    alerta.revisado_por = request.user
    alerta.comentario_cierre = comentario
    alerta.save(update_fields=['estado', 'fecha_revision', 'revisado_por', 'comentario_cierre', 'updated_at'])
    messages.success(request, 'Alerta descartada con justificacion.')
    return _redirect_alertas(request)


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def matrices_view(request):
    report = build_matrices_report(request.user, request.GET)
    if request.GET.get('exportar') == 'csv':
        response = HttpResponse(render_matrices_csv(report), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="matrices_operativas_{timezone.localdate()}.csv"'
        )
        return response

    matrices = [
        {'titulo': 'Riesgo clinico', 'tipo': 'riesgo_clinico', 'responsable': 'Equipo FACCI', 'fecha': timezone.now()},
        {'titulo': 'Referencias medicas', 'tipo': 'referencias', 'responsable': 'Coordinacion clinica', 'fecha': timezone.now()},
        {'titulo': 'Seguimiento clinico', 'tipo': 'seguimiento', 'responsable': 'Equipo medico', 'fecha': timezone.now()},
        {'titulo': 'Alertas clinicas', 'tipo': 'alertas', 'responsable': 'Auditoria clinica', 'fecha': timezone.now()},
    ]

    return render(
        request,
        'dashboard/matrices.html',
        {
            'titulo_pagina': 'Matrices Operativas',
            'matrices': matrices,
            'total': len(matrices),
            'report': report,
            'centros': report['centros'],
            'centros_data': report['centros_data'],
            'provincias_data': report['provincias_data'],
            'total_cribados_periodo': report['total_cribados_periodo'],
            'total_referencias_periodo': report['total_referencias_periodo'],
            'periodo_dias': report['periodo_dias'],
            'periodo_param': report['periodo_param'],
            'periodo_label': report['periodo_label'],
            'periodo_opciones': report['periodo_opciones'],
            'tiempo_medio_label': report['tiempo_medio_label'],
            'tiempo_medio_valor': report['tiempo_medio_valor'],
            'tiempo_medio_estado': report['tiempo_medio_estado'],
            'tasa_exito_label': report['tasa_exito_label'],
            'tasa_exito_valor': report['tasa_exito_valor'],
            'tasa_exito_barra': report['tasa_exito_barra'],
            'alertas_operativas': report['alertas_operativas'],
            'alertas_abiertas_total': report['alertas_abiertas_total'],
        },
    )

    import csv
    from django.http import HttpResponse as _HttpResponse
    from datetime import timedelta
    from django.db.models import Avg, Count, F

    # ── Período seleccionado ──────────────────────────────────────
    dias_map = {'7': 7, '30': 30, '90': 90, '365': 365}
    periodo_param = request.GET.get('periodo', '30')
    dias = dias_map.get(periodo_param, 30)
    fecha_inicio = timezone.localdate() - timedelta(days=dias)

    # ── Datos reales de la BD ─────────────────────────────────────
    from apps.cribado.models import CuestionarioCribado
    from apps.referencias.models import ReferenciaMedica as _Ref

    centros = CentroSalud.objects.all().order_by('nombre')

    # KPIs globales del período
    cribados_periodo = CuestionarioCribado.objects.filter(fecha_evaluacion__date__gte=fecha_inicio)
    referencias_periodo = _Ref.objects.filter(fecha_referencia__date__gte=fecha_inicio)

    total_cribados_periodo = cribados_periodo.count()
    total_referencias_periodo = referencias_periodo.count()

    # Datos por centro (para la tabla)
    centros_data = []
    for c in centros:
        crib_c = cribados_periodo.filter(medico__centro_medico=c).count()
        refs_c = referencias_periodo.filter(hospital_destino=c).count()
        centros_data.append({
            'centro': c,
            'cribados': crib_c,
            'referencias': refs_c,
        })

    # Distribución por región/provincia (usa pacientes como proxy)
    provincias_raw = (
        Paciente.objects.filter(created_at__date__gte=fecha_inicio)
        .values('provincia')
        .annotate(total=Count('id'))
        .order_by('-total')[:6]
    )
    max_prov = max((p['total'] for p in provincias_raw), default=1)
    provincias_data = [
        {
            'nombre': p['provincia'] or 'Sin especificar',
            'total': p['total'],
            'porcentaje': max(4, round(p['total'] / max_prov * 100)),
        }
        for p in provincias_raw
    ]

    # ── Exportar CSV ──────────────────────────────────────────────
    if request.GET.get('exportar') == 'csv':
        response = _HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="matrices_operativas_{timezone.localdate()}.csv"'
        )
        response.write('\ufeff')  # BOM para Excel
        writer = csv.writer(response)
        writer.writerow([
            'Centro de Salud', 'Provincia', 'Tipo', 'Estado',
            f'Cribados ({dias}d)', f'Referencias ({dias}d)',
        ])
        for row in centros_data:
            c = row['centro']
            writer.writerow([
                c.nombre,
                c.provincia or '—',
                c.get_tipo_display() if hasattr(c, 'get_tipo_display') else '—',
                'Activo' if c.activo else 'Inactivo',
                row['cribados'],
                row['referencias'],
            ])
        return response

    matrices = [
        {'titulo': 'Riesgo clínico', 'tipo': 'riesgo_clinico', 'responsable': 'Equipo FACCI', 'fecha': timezone.now()},
        {'titulo': 'Referencias médicas', 'tipo': 'referencias', 'responsable': 'Coordinación clínica', 'fecha': timezone.now()},
        {'titulo': 'Seguimiento clínico', 'tipo': 'seguimiento', 'responsable': 'Equipo médico', 'fecha': timezone.now()},
        {'titulo': 'Alertas clínicas', 'tipo': 'alertas', 'responsable': 'Auditoría clínica', 'fecha': timezone.now()},
    ]

    return render(
        request,
        'dashboard/matrices.html',
        {
            'titulo_pagina': 'Matrices Operativas',
            'matrices': matrices,
            'total': len(matrices),
            'centros': centros,
            'centros_data': centros_data,
            'provincias_data': provincias_data,
            'total_cribados_periodo': total_cribados_periodo,
            'total_referencias_periodo': total_referencias_periodo,
            'periodo_dias': dias,
            'periodo_param': periodo_param,
        },
    )


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def matrices_vista_previa_view(request):
    report = build_matrices_report(request.user, request.GET)
    return render(
        request,
        'dashboard/matrices_vista_previa.html',
        {
            'titulo_pagina': 'Vista previa - Matrices Operativas',
            'report': report,
        },
    )


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def matrices_descargar_pdf_view(request):
    report = build_matrices_report(request.user, request.GET)
    content = render_matrices_pdf(report)
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{matrices_pdf_filename(report)}"'
    return response


@login_required
@roles_requeridos('ADMIN')
def auditoria_view(request):
    User = get_user_model()
    hoy = timezone.localdate()

    usuario_filtro = request.GET.get('usuario', '').strip()
    rol_filtro = request.GET.get('rol', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()
    acceso_filtro = request.GET.get('ultimo_acceso', '').strip()
    modulo_filtro = request.GET.get('modulo', '').strip()
    tipo_accion_filtro = request.GET.get('tipo_accion', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    usuarios_base = User.objects.all()
    usuarios = usuarios_base.annotate(acciones_count=Count('logactividad'))
    if usuario_filtro:
        usuarios = usuarios.filter(
            Q(username__icontains=usuario_filtro) |
            Q(first_name__icontains=usuario_filtro) |
            Q(last_name__icontains=usuario_filtro) |
            Q(email__icontains=usuario_filtro)
        )
    if rol_filtro in CustomUser.Rol.values:
        usuarios = usuarios.filter(rol=rol_filtro)
    if estado_filtro == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        usuarios = usuarios.filter(is_active=False)
    if acceso_filtro == 'con_acceso':
        usuarios = usuarios.filter(last_login__isnull=False)
    elif acceso_filtro == 'sin_acceso':
        usuarios = usuarios.filter(last_login__isnull=True)
    elif acceso_filtro == 'ultimos_7':
        usuarios = usuarios.filter(last_login__gte=timezone.now() - timezone.timedelta(days=7))

    actividad = LogActividad.objects.select_related('usuario').all()
    if usuario_filtro:
        actividad = actividad.filter(
            Q(usuario__username__icontains=usuario_filtro) |
            Q(usuario__first_name__icontains=usuario_filtro) |
            Q(usuario__last_name__icontains=usuario_filtro) |
            Q(usuario__email__icontains=usuario_filtro)
        )
    if modulo_filtro:
        actividad = actividad.filter(modulo=modulo_filtro)
    if tipo_accion_filtro in LogActividad.TipoAccion.values:
        actividad = actividad.filter(tipo_accion=tipo_accion_filtro)

    fecha_desde_dt = parse_date(fecha_desde) if fecha_desde else None
    fecha_hasta_dt = parse_date(fecha_hasta) if fecha_hasta else None
    if fecha_desde_dt:
        actividad = actividad.filter(fecha__date__gte=fecha_desde_dt)
    if fecha_hasta_dt:
        actividad = actividad.filter(fecha__date__lte=fecha_hasta_dt)

    reportes = ReporteGenerado.objects.select_related('generado_por')
    if usuario_filtro:
        reportes = reportes.filter(
            Q(generado_por__username__icontains=usuario_filtro) |
            Q(generado_por__first_name__icontains=usuario_filtro) |
            Q(generado_por__last_name__icontains=usuario_filtro)
        )
    if fecha_desde_dt:
        reportes = reportes.filter(created_at__date__gte=fecha_desde_dt)
    if fecha_hasta_dt:
        reportes = reportes.filter(created_at__date__lte=fecha_hasta_dt)

    stats = {
        'total_usuarios': usuarios_base.count(),
        'usuarios_activos': usuarios_base.filter(is_active=True).count(),
        'acciones_hoy': LogActividad.objects.filter(fecha__date=hoy).count(),
        'reportes_generados': ReporteGenerado.objects.count(),
        'accesos_recientes': usuarios_base.filter(
            last_login__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
    }

    return render(
        request,
        'dashboard/auditoria.html',
        {
            'titulo_pagina': 'Auditoria',
            'stats': stats,
            'usuarios': usuarios.order_by('-last_login', 'username')[:30],
            'actividad_reciente': actividad.order_by('-fecha')[:50],
            'reportes': reportes.order_by('-created_at')[:20],
            'roles': CustomUser.Rol.choices,
            'tipos_accion': LogActividad.TipoAccion.choices,
            'modulos': LogActividad.objects.exclude(modulo='').values_list('modulo', flat=True).distinct().order_by('modulo'),
            'filtros': {
                'usuario': usuario_filtro,
                'rol': rol_filtro,
                'estado': estado_filtro,
                'ultimo_acceso': acceso_filtro,
                'modulo': modulo_filtro,
                'tipo_accion': tipo_accion_filtro,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
            },
        },
    )


from apps.core.models import SistemaConfiguracion

@login_required
@roles_requeridos(CustomUser.Rol.ADMIN)
def ajustes_view(request):
    config = SistemaConfiguracion.get_solo()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_logo_aplicacion':
            if config.logo_aplicacion:
                config.logo_aplicacion.delete()
            messages.success(request, 'Logo de la aplicación eliminado. Se restauró el logo por defecto.')
        elif action == 'delete_logo_reportes':
            if config.logo_reportes:
                config.logo_reportes.delete()
            messages.success(request, 'Logo oficial de reportes eliminado. Se restauró el logo por defecto.')
        else:
            nombre_app = request.POST.get('nombre_aplicacion', '').strip()
            nombre_inst = request.POST.get('nombre_institucion', '').strip()
            logo_app = request.FILES.get('logo_aplicacion')
            logo_rep = request.FILES.get('logo_reportes')
            
            if nombre_app:
                config.nombre_aplicacion = nombre_app
            if nombre_inst:
                config.nombre_institucion = nombre_inst
            if logo_app:
                config.logo_aplicacion = logo_app
            if logo_rep:
                config.logo_reportes = logo_rep
            config.save()
            messages.success(request, 'Configuración del sistema guardada correctamente.')
        return redirect('ajustes')

    return render(request, 'dashboard/ajustes.html', {
        'titulo_pagina': 'Ajustes del Sistema',
        'config': config,
    })

