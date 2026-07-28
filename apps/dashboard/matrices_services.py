import csv
import datetime
from io import BytesIO, StringIO
from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.core.models import CentroSalud
from apps.cribado.models import CuestionarioCribado
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaMedica

from .models import AlertaClinica
from .services import ESTADOS_ABIERTOS


DOCUMENT_CODE = 'FACCI-MO-REP-01'
DOCUMENT_VERSION = '1'
def _logo_path() -> str:
    from apps.core.utils import get_system_logo_path_or_fallback
    return get_system_logo_path_or_fallback()

PERIOD_OPTIONS = [
    ('7', 'Ultimos 7 dias'),
    ('30', 'Ultimos 30 dias'),
    ('90', 'Ultimos 3 meses'),
    ('180', 'Ultimos 6 meses'),
    ('365', 'Ultimo ano'),
]


def _local_date(value):
    if not value:
        return ''
    if hasattr(value, 'date') and not isinstance(value, datetime.date):
        value = timezone.localtime(value).date()
    return value.strftime('%d/%m/%Y')


def _local_datetime(value):
    if not value:
        return ''
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d/%m/%Y %H:%M')


def _user_name(user):
    if not user or not user.is_authenticated:
        return 'Usuario no disponible'
    return getattr(user, 'nombre_completo', '') or user.get_full_name() or user.get_username()


def _build_period(query):
    today = timezone.localdate()
    periodo_param = (query.get('periodo') or '30').strip()

    if periodo_param == 'custom':
        start = parse_date(query.get('fecha_inicio', ''))
        end = parse_date(query.get('fecha_fin', ''))
        if start and end and start <= end:
            return {
                'periodo_param': periodo_param,
                'periodo_dias': max((end - start).days + 1, 1),
                'fecha_inicio': start,
                'fecha_fin': end,
                'periodo_label': f'Rango personalizado ({_local_date(start)} - {_local_date(end)})',
                'query_string': f'periodo=custom&fecha_inicio={start.isoformat()}&fecha_fin={end.isoformat()}',
            }

    dias_map = {value: int(value) for value, _ in PERIOD_OPTIONS}
    dias = dias_map.get(periodo_param, 30)
    if periodo_param not in dias_map:
        periodo_param = '30'
    start = today - datetime.timedelta(days=dias)
    label = dict(PERIOD_OPTIONS).get(periodo_param, 'Ultimos 30 dias')
    return {
        'periodo_param': periodo_param,
        'periodo_dias': dias,
        'fecha_inicio': start,
        'fecha_fin': today,
        'periodo_label': label,
        'query_string': f'periodo={periodo_param}',
    }


def _status_for_ratio(value, target):
    if value is None:
        return 'Sin datos', 'outline', 'No hay registros suficientes para calcular este indicador.'
    if value >= target:
        return 'Optimo', 'primary', 'Cumple la meta institucional.'
    if value >= target * 0.8:
        return 'En observacion', 'secondary', 'Cerca de la meta; conviene revisar casos pendientes.'
    return 'Critico', 'error', 'Requiere intervencion operativa.'


def _status_for_time(value, target):
    if value is None:
        return 'Sin datos', 'outline', 'No hay referencias vinculadas a cribados en el periodo.'
    if value <= target:
        return 'Optimo', 'primary', 'Tiempo dentro de la meta institucional.'
    if value <= target * 1.5:
        return 'En observacion', 'secondary', 'Tiempo por encima de la meta; revisar cuellos de botella.'
    return 'Critico', 'error', 'Tiempo fuera de rango operativo esperado.'


def _alert_action(alerta):
    if alerta.prioridad == AlertaClinica.Prioridad.CRITICA:
        return 'Escalar a coordinacion clinica hoy.'
    if alerta.tipo_alerta == AlertaClinica.TipoAlerta.SEGUIMIENTO_PENDIENTE:
        return 'Agendar seguimiento y confirmar responsable.'
    if alerta.tipo_alerta == AlertaClinica.TipoAlerta.REFERENCIA_SIN_SEGUIMIENTO:
        return 'Verificar referencia y contacto con centro destino.'
    if alerta.tipo_alerta == AlertaClinica.TipoAlerta.DOCUMENTO_PENDIENTE:
        return 'Completar documentacion clinica pendiente.'
    return 'Revisar y documentar accion tomada.'


def build_matrices_report(user, query):
    period = _build_period(query)
    start = period['fecha_inicio']
    end = period['fecha_fin']
    now = timezone.localtime()

    cribados = CuestionarioCribado.objects.select_related('paciente', 'medico').filter(
        fecha_evaluacion__date__gte=start,
        fecha_evaluacion__date__lte=end,
    )
    referencias = ReferenciaMedica.objects.select_related(
        'paciente', 'cuestionario', 'medico_referente', 'especialista_destino'
    ).filter(
        fecha_referencia__date__gte=start,
        fecha_referencia__date__lte=end,
    )
    pacientes_periodo = Paciente.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    )
    alertas_periodo = AlertaClinica.objects.select_related('paciente').filter(
        fecha_creacion__date__gte=start,
        fecha_creacion__date__lte=end,
    )
    alertas_abiertas = alertas_periodo.filter(estado__in=ESTADOS_ABIERTOS)

    deltas = []
    for referencia in referencias:
        if referencia.cuestionario_id and referencia.cuestionario.fecha_evaluacion:
            delta = referencia.fecha_referencia - referencia.cuestionario.fecha_evaluacion
            deltas.append(max(delta.total_seconds() / 86400, 0))
    tiempo_medio = round(sum(deltas) / len(deltas), 1) if deltas else None
    tiempo_estado, tiempo_color, tiempo_obs = _status_for_time(tiempo_medio, 5)

    total_referencias = referencias.count()
    ingresos_exitosos = referencias.filter(
        estado__in=[
            ReferenciaMedica.EstadoReferencia.ACEPTADA,
            ReferenciaMedica.EstadoReferencia.EN_PROCESO,
            ReferenciaMedica.EstadoReferencia.COMPLETADA,
        ]
    ).count()
    tasa_exito = round((ingresos_exitosos / total_referencias) * 100, 1) if total_referencias else None
    tasa_estado, tasa_color, tasa_obs = _status_for_ratio(tasa_exito, 90)

    provincias_raw = list(
        pacientes_periodo.values('provincia').annotate(total=Count('id')).order_by('-total')
    )
    total_pacientes_region = sum(item['total'] for item in provincias_raw)
    provincias_data = []
    for item in provincias_raw[:8]:
        porcentaje = round((item['total'] / total_pacientes_region) * 100, 1) if total_pacientes_region else 0
        provincias_data.append({
            'nombre': item['provincia'] or 'Sin especificar',
            'total': item['total'],
            'porcentaje': porcentaje,
            'barra': max(4, round(porcentaje)) if porcentaje else 0,
            'estado': 'Carga alta' if porcentaje >= 40 else 'Balanceado',
        })

    # Altura de barra (%) relativa al máximo, para la gráfica de columnas.
    _max_total = max((p['total'] for p in provincias_data), default=0)
    for _p in provincias_data:
        _ratio = (_p['total'] / _max_total) if _max_total else 0
        _p['altura'] = max(4, round(_ratio * 100)) if _p['total'] else 0
    centros = CentroSalud.objects.all().order_by('nombre')
    centros_data = []
    for centro in centros:
        cribados_centro = cribados.filter(medico__centro_medico=centro).count()
        referencias_centro = referencias.filter(hospital_destino=centro).count()
        centros_data.append({
            'centro': centro,
            'cribados': cribados_centro,
            'referencias': referencias_centro,
        })

    alertas_data = []
    for alerta in alertas_abiertas.order_by('-prioridad', '-fecha_creacion')[:10]:
        alertas_data.append({
            'titulo': alerta.titulo,
            'descripcion': alerta.descripcion,
            'nivel': alerta.get_prioridad_display(),
            'estado': alerta.get_estado_display(),
            'accion': _alert_action(alerta),
            'url': alerta.url_detalle,
            'color': alerta.color,
        })

    total_cribados = cribados.count()
    indicadores = [
        {
            'nombre': 'Tiempo medio cribado a referencia',
            'valor': f'{tiempo_medio} dias' if tiempo_medio is not None else 'Sin datos',
            'meta': '<= 5 dias',
            'estado': tiempo_estado,
            'color': tiempo_color,
            'observacion': tiempo_obs,
        },
        {
            'nombre': 'Tasa exito ingreso hospitalario',
            'valor': f'{tasa_exito}%' if tasa_exito is not None else 'Sin datos',
            'meta': '>= 90%',
            'estado': tasa_estado,
            'color': tasa_color,
            'observacion': tasa_obs,
        },
        {
            'nombre': f'Cribados del periodo',
            'valor': total_cribados,
            'meta': 'Monitoreo continuo',
            'estado': 'Activo' if total_cribados else 'Sin registros',
            'color': 'primary' if total_cribados else 'outline',
            'observacion': 'Cribados realizados dentro del periodo seleccionado.',
        },
        {
            'nombre': 'Alertas operativas abiertas',
            'valor': alertas_abiertas.count(),
            'meta': '0 criticas vencidas',
            'estado': 'Revisar' if alertas_abiertas.exists() else 'Sin alertas',
            'color': 'error' if alertas_abiertas.filter(prioridad=AlertaClinica.Prioridad.CRITICA).exists() else 'primary',
            'observacion': 'Alertas abiertas que requieren seguimiento operativo.',
        },
    ]

    return {
        **period,
        'periodo_opciones': PERIOD_OPTIONS,
        'codigo_documento': DOCUMENT_CODE,
        'version': DOCUMENT_VERSION,
        'fecha_generacion': now,
        'fecha_generacion_label': _local_datetime(now),
        'generado_por': _user_name(user),
        'logo_path': _logo_path(),
        'logo_static': 'img/Logo-Facci-1.png',
        'total_cribados_periodo': total_cribados,
        'total_referencias_periodo': total_referencias,
        'tiempo_medio': tiempo_medio,
        'tiempo_medio_valor': tiempo_medio if tiempo_medio is not None else '-',
        'tiempo_medio_label': f'{tiempo_medio} dias' if tiempo_medio is not None else 'Sin datos',
        'tiempo_medio_estado': tiempo_estado,
        'tasa_exito': tasa_exito,
        'tasa_exito_valor': tasa_exito if tasa_exito is not None else '-',
        'tasa_exito_label': f'{tasa_exito}%' if tasa_exito is not None else 'Sin datos',
        'tasa_exito_barra': min(round(tasa_exito or 0), 100),
        'ingresos_exitosos': ingresos_exitosos,
        'regiones_evaluadas': len(provincias_data),
        'alertas_total': alertas_periodo.count(),
        'alertas_abiertas_total': alertas_abiertas.count(),
        'indicadores': indicadores,
        'provincias_data': provincias_data,
        'centros': centros,
        'centros_data': centros_data,
        'alertas_operativas': alertas_data,
        'sin_datos': not any([total_cribados, total_referencias, total_pacientes_region, alertas_periodo.count()]),
    }


def render_matrices_csv(report):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['FACCI Care', 'Reporte de Matrices Operativas'])
    writer.writerow(['Codigo', report['codigo_documento']])
    writer.writerow(['Version', report['version']])
    writer.writerow(['Periodo', report['periodo_label']])
    writer.writerow(['Fecha generacion', report['fecha_generacion_label']])
    writer.writerow(['Generado por', report['generado_por']])
    writer.writerow([])

    writer.writerow(['Indicadores principales'])
    writer.writerow(['Indicador', 'Valor', 'Meta institucional', 'Estado', 'Observacion'])
    for item in report['indicadores']:
        writer.writerow([item['nombre'], item['valor'], item['meta'], item['estado'], item['observacion']])
    writer.writerow([])

    writer.writerow(['Carga de trabajo por region'])
    writer.writerow(['Region', 'Pacientes', 'Porcentaje', 'Estado'])
    if report['provincias_data']:
        for item in report['provincias_data']:
            writer.writerow([item['nombre'], item['total'], f"{item['porcentaje']}%", item['estado']])
    else:
        writer.writerow(['Sin datos', 0, '0%', 'Sin registros'])
    writer.writerow([])

    writer.writerow(['Alertas operativas'])
    writer.writerow(['Alerta', 'Descripcion', 'Nivel', 'Estado', 'Accion recomendada'])
    if report['alertas_operativas']:
        for item in report['alertas_operativas']:
            writer.writerow([item['titulo'], item['descripcion'], item['nivel'], item['estado'], item['accion']])
    else:
        writer.writerow(['Sin alertas abiertas', '', '', '', 'Mantener monitoreo'])
    return output.getvalue().encode('utf-8-sig')


def matrices_pdf_filename(report):
    date_part = timezone.localtime(report['fecha_generacion']).strftime('%Y%m%d_%H%M')
    return f'matrices_operativas_{date_part}.pdf'


def render_matrices_pdf(report):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.3 * inch,
        leftMargin=0.3 * inch,
        topMargin=0.28 * inch,
        bottomMargin=0.38 * inch,
        title='Reporte de Matrices Operativas',
    )
    styles = getSampleStyleSheet()
    styles['Title'].fontSize = 14
    styles['Title'].leading = 16
    styles.add(ParagraphStyle(name='Small', parent=styles['Normal'], fontSize=6.7, leading=8))
    styles.add(ParagraphStyle(name='Section', parent=styles['Heading2'], fontSize=8.5, leading=10, textColor=colors.HexColor('#1F4F54')))

    story = []
    logo_cell = Paragraph('FACCI', styles['Title'])
    if report['logo_path']:
        try:
            logo_cell = Image(report['logo_path'], width=0.9 * inch, height=0.58 * inch)
        except Exception:
            pass
    header = Table([[
        logo_cell,
        Paragraph('<b>Reporte de Matrices Operativas</b><br/>FACCI Care', styles['Title']),
        Paragraph(
            f"<b>Codigo:</b> {report['codigo_documento']}<br/>"
            f"<b>Version:</b> {report['version']}<br/>"
            f"<b>Fecha:</b> {_local_date(report['fecha_generacion'])}",
            styles['Small'],
        ),
    ]], colWidths=[1.05 * inch, 4.55 * inch, 1.9 * inch])
    header.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#2E6F73')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#B8C7C9')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F6FBFB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.06 * inch))

    meta = [
        ['Periodo', report['periodo_label'], 'Generado por', report['generado_por']],
        ['Fecha generacion', report['fecha_generacion_label'], 'Sistema', 'FACCI Care'],
    ]
    meta_table = Table(meta, colWidths=[1.2 * inch, 2.35 * inch, 1.2 * inch, 2.55 * inch])
    meta_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#B8C7C9')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#D7ECEE')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#D7ECEE')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.7),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.06 * inch))

    summary = [
        ['Total cribados', report['total_cribados_periodo'], 'Tiempo medio', report['tiempo_medio_label']],
        ['Tasa exito', report['tasa_exito_label'], 'Alertas abiertas', report['alertas_abiertas_total']],
        ['Regiones evaluadas', report['regiones_evaluadas'], 'Referencias', report['total_referencias_periodo']],
    ]
    summary_table = Table(summary, colWidths=[1.45 * inch, 1.1 * inch, 1.45 * inch, 1.1 * inch])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#B8C7C9')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EAF7F8')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#EAF7F8')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.7),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(Paragraph('<b>Resumen ejecutivo</b>', styles['Section']))
    story.append(summary_table)
    story.append(Spacer(1, 0.06 * inch))

    def styled_table(rows, col_widths):
        table = Table(rows, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#B8C7C9')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E6F73')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6.2),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6FBFB')]),
            ('LEFTPADDING', (0, 0), (-1, -1), 2.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2.5),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return table

    indicator_rows = [['Indicador', 'Valor', 'Meta', 'Estado', 'Observacion']]
    for item in report['indicadores']:
        indicator_rows.append([
            Paragraph(str(item['nombre']), styles['Small']),
            Paragraph(str(item['valor']), styles['Small']),
            Paragraph(str(item['meta']), styles['Small']),
            Paragraph(str(item['estado']), styles['Small']),
            Paragraph(str(item['observacion']), styles['Small']),
        ])
    story.append(Paragraph('<b>Indicadores principales</b>', styles['Section']))
    story.append(styled_table(indicator_rows, [1.65 * inch, 0.8 * inch, 0.95 * inch, 0.9 * inch, 3.0 * inch]))
    story.append(Spacer(1, 0.06 * inch))

    workload_rows = [['Region', 'Pacientes', 'Porcentaje', 'Estado']]
    if report['provincias_data']:
        for item in report['provincias_data']:
            workload_rows.append([item['nombre'], item['total'], f"{item['porcentaje']}%", item['estado']])
    else:
        workload_rows.append(['Sin datos', '0', '0%', 'Sin registros'])
    story.append(Paragraph('<b>Carga de trabajo por region</b>', styles['Section']))
    story.append(styled_table(workload_rows, [2.7 * inch, 1.1 * inch, 1.1 * inch, 2.4 * inch]))
    story.append(Spacer(1, 0.06 * inch))

    alert_rows = [['Alerta', 'Nivel', 'Estado', 'Accion recomendada']]
    if report['alertas_operativas']:
        for item in report['alertas_operativas']:
            alert_rows.append([
                Paragraph(item['titulo'], styles['Small']),
                item['nivel'],
                item['estado'],
                Paragraph(item['accion'], styles['Small']),
            ])
    else:
        alert_rows.append(['Sin alertas abiertas', '-', '-', 'Mantener monitoreo operativo'])
    story.append(Paragraph('<b>Alertas operativas</b>', styles['Section']))
    story.append(styled_table(alert_rows, [2.25 * inch, 1.0 * inch, 1.0 * inch, 3.05 * inch]))

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont('Helvetica', 6.5)
        canvas.setFillColor(colors.HexColor('#4A5F61'))
        canvas.drawString(0.3 * inch, 0.24 * inch, 'Fundacion Amigos Contra el Cancer Infantil - FACCI Care')
        canvas.drawCentredString(4.25 * inch, 0.24 * inch, f'Pagina {doc_obj.page}')
        canvas.drawRightString(8.2 * inch, 0.24 * inch, report['codigo_documento'])
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
