import calendar
import datetime
from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.core.decorators import roles_requeridos, requiere_acceso
from apps.pacientes.models import Paciente
from apps.cribado.models import CuestionarioCribado
from apps.dashboard.models import AlertaClinica
from apps.dashboard.services import generar_alertas_pendientes, resumen_alertas
from apps.referencias.models import ReferenciaMedica

from .models import ReporteGenerado
from .services import (
    FORMAT_CHOICES,
    PERIOD_CHOICES,
    REPORT_TYPES,
    build_report,
    parse_report_params,
    render_report_file,
    report_filename,
)


def _hace_n_meses(dt, n):
    """Retrocede n meses sin dateutil, clampando el día al máximo del mes destino."""
    month = dt.month - n
    year = dt.year
    while month <= 0:
        month += 12
        year -= 1
    max_day = calendar.monthrange(year, month)[1]
    return dt.replace(year=year, month=month, day=min(dt.day, max_day))


MESES_CORTOS = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
}
MESES_LARGOS = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}
COLORES_CANCER = ['error', 'secondary', 'primary', 'tertiary', 'primary', 'outline']


@login_required
@requiere_acceso('puede_ver_reportes')
def dashboard_view(request):
    hoy = timezone.now()
    generar_alertas_pendientes()
    periodo_param = request.GET.get('periodo', '')
    try:
        periodo_inicio = datetime.datetime.strptime(periodo_param, '%Y-%m').date().replace(day=1)
    except ValueError:
        periodo_inicio = hoy.date().replace(day=1)
        periodo_param = periodo_inicio.strftime('%Y-%m')
    siguiente_mes = periodo_inicio.replace(day=28) + datetime.timedelta(days=4)
    periodo_fin = siguiente_mes.replace(day=1) - datetime.timedelta(days=1)
    periodo_inicio_dt = timezone.make_aware(datetime.datetime.combine(periodo_inicio, datetime.time.min))
    periodo_fin_dt = timezone.make_aware(datetime.datetime.combine(periodo_fin, datetime.time.max))
    alertas_resumen = resumen_alertas(AlertaClinica.objects.filter(
        fecha_creacion__gte=periodo_inicio_dt,
        fecha_creacion__lte=periodo_fin_dt,
    ))

    # ── Stats generales ──────────────────────────────────────────────
    total_pacientes = Paciente.objects.count()
    nuevos_mes = Paciente.objects.filter(
        created_at__date__gte=periodo_inicio,
        created_at__date__lte=periodo_fin,
    ).count()
    cribados_positivos = CuestionarioCribado.objects.filter(
        resultado__in=['SOSPECHA_MODERADA', 'SOSPECHA_ALTA'],
        fecha_evaluacion__date__gte=periodo_inicio,
        fecha_evaluacion__date__lte=periodo_fin,
    ).count()
    referencias_enviadas = ReferenciaMedica.objects.filter(
        fecha_referencia__date__gte=periodo_inicio,
        fecha_referencia__date__lte=periodo_fin,
    ).count()
    en_tratamiento = Paciente.objects.filter(estado_actual='EN_TRATAMIENTO').count()
    en_remision = Paciente.objects.filter(estado_actual='EN_REMISION').count()

    # ── Distribución por provincia ───────────────────────────────────
    provincias_qs = list(
        Paciente.objects.filter(
            created_at__date__gte=periodo_inicio,
            created_at__date__lte=periodo_fin,
        )
        .values('provincia')
        .annotate(casos=Count('id'))
        .order_by('-casos')
    )
    max_casos = provincias_qs[0]['casos'] if provincias_qs else 1

    mes_ant = _hace_n_meses(periodo_inicio, 1)
    actual_prov = {
        p['provincia']: p['casos']
        for p in Paciente.objects.filter(
            created_at__date__gte=periodo_inicio, created_at__date__lte=periodo_fin,
        ).values('provincia').annotate(casos=Count('id'))
    }
    anterior_prov = {
        p['provincia']: p['casos']
        for p in Paciente.objects.filter(
            created_at__month=mes_ant.month, created_at__year=mes_ant.year,
        ).values('provincia').annotate(casos=Count('id'))
    }

    def _tendencia(prov):
        a, b = actual_prov.get(prov, 0), anterior_prov.get(prov, 0)
        if a > b:
            return 'up'
        if a < b:
            return 'down'
        return 'stable'

    datos_provincias = [
        {
            'nombre': p['provincia'],
            'casos': p['casos'],
            'porcentaje': round(p['casos'] / max_casos * 100),
            'tendencia': _tendencia(p['provincia']),
        }
        for p in provincias_qs
    ]

    # ── Tipos de cáncer ──────────────────────────────────────────────
    diag_qs = list(
        Paciente.objects.filter(
            created_at__date__gte=periodo_inicio,
            created_at__date__lte=periodo_fin,
        )
        .exclude(diagnostico='')
        .values('diagnostico')
        .annotate(casos=Count('id'))
        .order_by('-casos')
    )
    total_diag = sum(d['casos'] for d in diag_qs) or 1
    tipos_cancer = [
        {
            'tipo': Paciente.Diagnostico(d['diagnostico']).label,
            'casos': d['casos'],
            'porcentaje': round(d['casos'] / total_diag * 100),
            'color': COLORES_CANCER[i % len(COLORES_CANCER)],
        }
        for i, d in enumerate(diag_qs)
    ]

    # ── Tendencia mensual (últimos 6 meses) ──────────────────────────
    inicio = _hace_n_meses(periodo_inicio_dt, 5)

    cribados_por_mes = {
        (e['mes'].year, e['mes'].month): e['total']
        for e in (
            CuestionarioCribado.objects
            .filter(fecha_evaluacion__gte=inicio)
            .annotate(mes=TruncMonth('fecha_evaluacion'))
            .values('mes')
            .annotate(total=Count('id'))
        )
    }
    positivos_por_mes = {
        (e['mes'].year, e['mes'].month): e['total']
        for e in (
            CuestionarioCribado.objects
            .filter(
                fecha_evaluacion__gte=inicio,
                resultado__in=['SOSPECHA_MODERADA', 'SOSPECHA_ALTA'],
            )
            .annotate(mes=TruncMonth('fecha_evaluacion'))
            .values('mes')
            .annotate(total=Count('id'))
        )
    }

    tendencia_mensual = []
    for i in range(6):
        d = _hace_n_meses(periodo_inicio, 5 - i)
        key = (d.year, d.month)
        c = cribados_por_mes.get(key, 0)
        p = positivos_por_mes.get(key, 0)
        tendencia_mensual.append({'mes': MESES_CORTOS[d.month], 'cribados': c, 'positivos': p})

    max_cribados = max((m['cribados'] for m in tendencia_mensual), default=0) or 1
    max_positivos = max((m['positivos'] for m in tendencia_mensual), default=0) or 1

    # ── Selector de período (últimos 6 meses) ───────────────────────
    ultimos_meses = [
        f"{MESES_LARGOS[_hace_n_meses(hoy, i).month]} {_hace_n_meses(hoy, i).year}"
        for i in range(6)
    ]
    periodos_meses = [
        {
            'valor': _hace_n_meses(hoy, i).strftime('%Y-%m'),
            'etiqueta': ultimos_meses[i],
        }
        for i in range(6)
    ]
    periodo = f'{MESES_LARGOS[periodo_inicio.month]} {periodo_inicio.year}'

    context = {
        'titulo_pagina': 'Reportes y Estadísticas',
        'periodo': periodo,
        'periodo_param': periodo_param,
        'ultimos_meses': ultimos_meses,
        'periodos_meses': periodos_meses,
        'stats_generales': {
            'total_pacientes': total_pacientes,
            'nuevos_mes': nuevos_mes,
            'cribados_positivos': cribados_positivos,
            'referencias_enviadas': referencias_enviadas,
            'en_tratamiento': en_tratamiento,
            'en_remision': en_remision,
        },
        'alertas_resumen': alertas_resumen,
        'datos_provincias': datos_provincias,
        'tipos_cancer': tipos_cancer,
        'tendencia_mensual': tendencia_mensual,
        'max_cribados': max_cribados,
        'max_positivos': max_positivos,
    }
    return render(request, 'reportes/dashboard.html', context)


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def generacion_view(request):
    from apps.core.constants import PROVINCIAS_RD
    from apps.auth_app.models import CustomUser
    from apps.core.models import SistemaConfiguracion
    hoy = timezone.now().date()

    if request.method == 'POST':
        return generar_reporte(request)

    context = {
        'titulo_pagina': 'Generar Reportes',
        'tipos_reporte': REPORT_TYPES,
        '_legacy_tipos_reporte': [
            {'id': 'resumen_mensual', 'titulo': 'Resumen Mensual', 'descripcion': 'Estadísticas generales del mes seleccionado', 'icono': 'calendar_month'},
            {'id': 'por_provincia', 'titulo': 'Por Provincia', 'descripcion': 'Distribución geográfica de casos', 'icono': 'map'},
            {'id': 'por_diagnostico', 'titulo': 'Por Diagnóstico', 'descripcion': 'Tipos de cáncer y frecuencia', 'icono': 'medical_information'},
            {'id': 'seguimiento', 'titulo': 'Seguimiento de Casos', 'descripcion': 'Estado actual de todos los pacientes en seguimiento', 'icono': 'monitor_heart'},
            {'id': 'referencias', 'titulo': 'Referencias Médicas', 'descripcion': 'Historial de referencias enviadas y recibidas', 'icono': 'send'},
        ],
        'formatos': FORMAT_CHOICES,
        'periodos': ['Último mes', 'Últimos 3 meses', 'Últimos 6 meses', 'Último año', 'Rango personalizado'],
        'periodos_opciones': PERIOD_CHOICES,
        'provincias': PROVINCIAS_RD,
        'medicos': CustomUser.objects.filter(
            rol__in=[CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA, CustomUser.Rol.ONCOLOGO]
        ).order_by('first_name', 'last_name'),
        'fecha_inicio_default': hoy.replace(day=1).isoformat(),
        'fecha_fin_default': hoy.isoformat(),
        'reportes_recientes': ReporteGenerado.objects.select_related('generado_por')[:5],
        'logo_configurado': True,
        'logo_path': SistemaConfiguracion.get_solo().logo_url,
    }
    return render(request, 'reportes/generacion.html', context)


def _params_or_redirect(request, requiere_correo=False):
    params = parse_report_params(request.POST, request.user)
    if requiere_correo and not request.POST.get('correo_destino', '').strip():
        params['errors'].append('Ingrese el correo destino.')
    if params['errors']:
        for error in params['errors']:
            messages.error(request, error)
        return None
    return params


def _guardar_reporte(request, params, report, content, filename):
    reporte = ReporteGenerado.objects.create(
        generado_por=request.user,
        tipo_reporte=report['tipo_modelo'],
        nombre_reporte=report['titulo'],
        formato=params['formato'],
        codigo_documento=report['codigo_documento'],
        fecha_inicio=params['fecha_inicio'],
        fecha_fin=params['fecha_fin'],
        total_registros=report['total_registros'],
    )
    try:
        reporte.archivo.save(filename, ContentFile(content), save=True)
    except OSError as exc:
        messages.warning(
            request,
            f'El reporte se genero, pero no pudo guardarse el archivo en MEDIA_ROOT: {exc}',
        )
    return reporte


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def generar_reporte(request):
    if request.method != 'POST':
        return redirect('reportes:generacion')

    params = _params_or_redirect(request)
    if not params:
        return redirect('reportes:generacion')

    report = build_report(params)
    content, mime_type = render_report_file(report, params['formato'])
    filename = report_filename(report, params['formato'])
    _guardar_reporte(request, params, report, content, filename)

    response = HttpResponse(content, content_type=mime_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    download_token = request.POST.get('download_token', '').strip()
    if download_token:
        response.set_cookie(
            'facci_report_download',
            download_token,
            max_age=120,
            path='/',
            samesite='Lax',
        )
    return response


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def vista_previa_reporte(request):
    if request.method != 'POST':
        return redirect('reportes:generacion')

    params = _params_or_redirect(request)
    if not params:
        return redirect('reportes:generacion')

    report = build_report(params)
    return render(request, 'reportes/reporte_print.html', {
        'report': report,
        'params': params,
        'formatos': FORMAT_CHOICES,
    })


@login_required
@roles_requeridos('ADMIN', 'PERSONAL_FACCI')
def enviar_reporte_correo(request):
    if request.method != 'POST':
        return redirect('reportes:generacion')

    params = _params_or_redirect(request, requiere_correo=True)
    if not params:
        return redirect('reportes:generacion')

    correo_destino = request.POST.get('correo_destino', '').strip()
    asunto = request.POST.get('correo_asunto', '').strip() or 'Reporte FACCI Care'
    mensaje = request.POST.get('correo_mensaje', '').strip()

    report = build_report(params)
    content, mime_type = render_report_file(report, params['formato'])
    filename = report_filename(report, params['formato'])
    _guardar_reporte(request, params, report, content, filename)

    cuerpo = mensaje or (
        f"Adjunto reporte {report['titulo']} correspondiente a {report['periodo_label']}.\n\n"
        'FACCI Care'
    )
    email = EmailMessage(
        subject=asunto,
        body=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[correo_destino],
    )
    email.attach(filename, content, mime_type)
    try:
        email.send(fail_silently=False)
    except Exception as exc:
        messages.error(request, f'No se pudo enviar el correo: {exc}')
    else:
        messages.success(request, f'Reporte enviado correctamente a {correo_destino}.')
    return redirect('reportes:generacion')


# ── Mapeo ICD-O3 para PENCI-RD ──────────────────────────────────────────────
_ICDO3 = {
    'LEUCEMIA':       'C91–C95',
    'TUMORES_SNC':    'C70–C72',
    'RETINOBLASTOMA': 'C69.2',
    'TUMOR_WILMS':    'C64',
    'NEUROBLASTOMA':  'C74',
    'OTRO':           'C00–C97',
}

_GRUPOS_ETARIOS = [
    ('0–4 años',   0,  4),
    ('5–9 años',   5,  9),
    ('10–14 años', 10, 14),
    ('≥15 años',   15, 99),
]


def _edad_en_fecha(nacimiento, referencia):
    edad = referencia.year - nacimiento.year
    if (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day):
        edad -= 1
    return edad


@login_required
@requiere_acceso('puede_ver_reportes')
def penci_view(request):
    hoy = timezone.now().date()
    año_actual = hoy.year

    fecha_inicio_raw = request.GET.get('fecha_inicio', '')
    fecha_fin_raw = request.GET.get('fecha_fin', '')
    fecha_inicio = parse_date(fecha_inicio_raw) or datetime.date(año_actual, 1, 1)
    fecha_fin = parse_date(fecha_fin_raw) or hoy

    # ── Casos nuevos en el período (por fecha de registro) ───────────
    pacientes_periodo = Paciente.objects.filter(
        created_at__date__gte=fecha_inicio,
        created_at__date__lte=fecha_fin,
    )
    total_nuevos = pacientes_periodo.count()

    # ── Incidencia mensual ────────────────────────────────────────────
    incidencia_qs = list(
        pacientes_periodo
        .annotate(mes=TruncMonth('created_at'))
        .values('mes')
        .annotate(casos=Count('id'))
        .order_by('mes')
    )
    incidencia_mensual = [
        {
            'mes': MESES_LARGOS[e['mes'].month] + ' ' + str(e['mes'].year),
            'mes_corto': MESES_CORTOS[e['mes'].month],
            'casos': e['casos'],
        }
        for e in incidencia_qs
    ]
    max_incidencia = max((m['casos'] for m in incidencia_mensual), default=0) or 1

    # ── Distribución por sexo ─────────────────────────────────────────
    sexo_qs = {
        s['sexo']: s['total']
        for s in pacientes_periodo.values('sexo').annotate(total=Count('id'))
    }
    total_sexo = total_nuevos or 1
    por_sexo = [
        {
            'etiqueta': 'Masculino',
            'codigo': 'M',
            'total': sexo_qs.get('M', 0),
            'pct': round(sexo_qs.get('M', 0) / total_sexo * 100),
        },
        {
            'etiqueta': 'Femenino',
            'codigo': 'F',
            'total': sexo_qs.get('F', 0),
            'pct': round(sexo_qs.get('F', 0) / total_sexo * 100),
        },
    ]

    # ── Distribución por grupo etario (al momento del registro) ──────
    por_grupo_etario = []
    for etiqueta, edad_min, edad_max in _GRUPOS_ETARIOS:
        cnt = sum(
            1 for p in pacientes_periodo
            if edad_min <= _edad_en_fecha(p.fecha_nacimiento, p.created_at.date()) <= edad_max
        )
        por_grupo_etario.append({
            'etiqueta': etiqueta,
            'total': cnt,
            'pct': round(cnt / total_sexo * 100),
        })

    # ── Distribución geográfica (por provincia) ───────────────────────
    prov_qs = list(
        pacientes_periodo.values('provincia')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    max_prov = prov_qs[0]['total'] if prov_qs else 1
    por_provincia = [
        {
            'nombre': p['provincia'] or '(No especificada)',
            'total': p['total'],
            'pct': round(p['total'] / max_prov * 100),
        }
        for p in prov_qs
    ]

    # ── Clasificación diagnóstica ─────────────────────────────────────
    diag_qs = {
        d['diagnostico']: d['total']
        for d in pacientes_periodo.values('diagnostico').annotate(total=Count('id'))
    }
    total_diag = sum(diag_qs.values()) or 1
    por_diagnostico = []
    for codigo, etiqueta in Paciente.Diagnostico.choices:
        cnt = diag_qs.get(codigo, 0)
        por_diagnostico.append({
            'etiqueta': etiqueta,
            'codigo': codigo,
            'icdo3': _ICDO3.get(codigo, '—'),
            'total': cnt,
            'pct': round(cnt / total_diag * 100),
        })
    sin_diagnostico = diag_qs.get('', 0)
    if sin_diagnostico:
        por_diagnostico.append({
            'etiqueta': 'Sin diagnóstico confirmado',
            'codigo': '',
            'icdo3': '—',
            'total': sin_diagnostico,
            'pct': round(sin_diagnostico / total_diag * 100),
        })

    # ── Estado clínico actual (todos los pacientes, no solo el período) ──
    estado_qs = {
        e['estado_actual']: e['total']
        for e in Paciente.objects.values('estado_actual').annotate(total=Count('id'))
    }
    total_estado = Paciente.objects.count() or 1
    por_estado = [
        {
            'etiqueta': etiqueta,
            'codigo': codigo,
            'total': estado_qs.get(codigo, 0),
            'pct': round(estado_qs.get(codigo, 0) / total_estado * 100),
        }
        for codigo, etiqueta in Paciente.EstadoPaciente.choices
    ]

    # ── Actividades de detección temprana ─────────────────────────────
    cribados_total = CuestionarioCribado.objects.filter(
        fecha_evaluacion__gte=fecha_inicio,
        fecha_evaluacion__lte=fecha_fin,
    ).count()
    cribados_positivos = CuestionarioCribado.objects.filter(
        fecha_evaluacion__gte=fecha_inicio,
        fecha_evaluacion__lte=fecha_fin,
        resultado__in=['SOSPECHA_MODERADA', 'SOSPECHA_ALTA'],
    ).count()
    referencias_total = ReferenciaMedica.objects.filter(
        fecha_referencia__gte=fecha_inicio,
        fecha_referencia__lte=fecha_fin,
    ).count()
    referencias_atendidas = ReferenciaMedica.objects.filter(
        fecha_referencia__gte=fecha_inicio,
        fecha_referencia__lte=fecha_fin,
        estado=ReferenciaMedica.EstadoReferencia.COMPLETADA,
    ).count()

    if total_nuevos == 0 and cribados_total == 0 and referencias_total == 0:
        messages.info(request, 'No hay datos disponibles para el período seleccionado.')

    # ── Evaluación psicosocial ─────────────────────────────────────────
    from apps.psicosocial.models import EvaluacionPsicosocial
    psico_total = EvaluacionPsicosocial.objects.filter(
        fecha_evaluacion__gte=fecha_inicio,
        fecha_evaluacion__lte=fecha_fin,
    ).count()
    psico_por_nivel = {
        e['nivel_riesgo']: e['total']
        for e in EvaluacionPsicosocial.objects.filter(
            fecha_evaluacion__gte=fecha_inicio,
            fecha_evaluacion__lte=fecha_fin,
        ).values('nivel_riesgo').annotate(total=Count('id'))
    }

    # ── Número de reporte ──────────────────────────────────────────────
    num_reporte = (
        ReporteGenerado.objects.filter(
            tipo_reporte=ReporteGenerado.TipoReporte.ESTADISTICAS,
        ).count() + 1
    )

    context = {
        'titulo_pagina': 'Reporte Epidemiológico PENCI-RD',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'fecha_generacion': hoy,
        'generado_por': request.user,
        'num_reporte': f'FACCI-PENCI-{hoy.year}-{num_reporte:04d}',
        # Sección I
        'total_nuevos': total_nuevos,
        'incidencia_mensual': incidencia_mensual,
        'max_incidencia': max_incidencia,
        # Sección II
        'por_sexo': por_sexo,
        # Sección III
        'por_grupo_etario': por_grupo_etario,
        # Sección IV
        'por_provincia': por_provincia,
        # Sección V
        'por_diagnostico': por_diagnostico,
        # Sección VI
        'por_estado': por_estado,
        'total_pacientes_sistema': Paciente.objects.count(),
        # Sección VII
        'cribados_total': cribados_total,
        'cribados_positivos': cribados_positivos,
        'tasa_positividad': round(cribados_positivos / cribados_total * 100) if cribados_total else 0,
        'referencias_total': referencias_total,
        'referencias_atendidas': referencias_atendidas,
        # Sección VIII
        'psico_total': psico_total,
        'psico_bajo': psico_por_nivel.get(EvaluacionPsicosocial.NivelRiesgo.BAJO, 0),
        'psico_medio': psico_por_nivel.get(EvaluacionPsicosocial.NivelRiesgo.MEDIO, 0),
        'psico_alto': psico_por_nivel.get(EvaluacionPsicosocial.NivelRiesgo.ALTO, 0),
        'psico_critico': psico_por_nivel.get(EvaluacionPsicosocial.NivelRiesgo.CRITICO, 0),
    }
    return render(request, 'reportes/penci.html', context)
