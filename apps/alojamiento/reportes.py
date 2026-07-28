from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import EstanciaFamiliar, HabitacionCasa


LOGO_STATIC = "img/Logo-Facci-1.png"
REPORT_TITLE = "Reporte de Pacientes en Estancia Casa FACCI"
FOOTER_TEXT = "FACCI Care - Casa FACCI"


@dataclass(frozen=True)
class ReporteEstanciaRow:
    paciente: str
    edad: str
    diagnostico: str
    responsable: str
    parentesco: str
    telefono: str
    habitacion: str
    fecha_ingreso: str
    fecha_salida: str
    tiempo_estadia: str
    estado: str
    observaciones: str


def _logo_path() -> str:
    from apps.core.utils import get_system_logo_path_or_fallback
    return get_system_logo_path_or_fallback()


def _display(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _choice_display(obj, field_name: str) -> str:
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        return _display(method())
    return _display(getattr(obj, field_name, ""))


def _user_name(user) -> str:
    if not user:
        return ""
    return user.get_full_name() or user.username or ""


def _responsable(estancia) -> dict[str, str]:
    tutor = getattr(estancia.paciente, "padre_tutor", None)
    tutor_user = getattr(tutor, "usuario", None) if tutor else None
    return {
        "nombre": _display(estancia.acompanante_nombre) or _user_name(tutor_user),
        "parentesco": _display(estancia.acompanante_parentesco) or _choice_display(tutor, "parentesco"),
        "telefono": _display(estancia.acompanante_telefono) or _display(getattr(tutor_user, "telefono", "")),
    }


def _tiempo_estadia(estancia) -> str:
    noches = estancia.noches
    if noches is None:
        return ""
    if noches == 1:
        return "1 noche"
    return f"{noches} noches"


def _row(estancia) -> ReporteEstanciaRow:
    responsable = _responsable(estancia)
    salida = estancia.fecha_egreso_real or estancia.fecha_egreso_prevista
    return ReporteEstanciaRow(
        paciente=estancia.paciente.nombre_completo,
        edad=_display(estancia.paciente.edad),
        diagnostico=_choice_display(estancia.paciente, "diagnostico") or "No registrado",
        responsable=responsable["nombre"],
        parentesco=responsable["parentesco"],
        telefono=responsable["telefono"],
        habitacion=estancia.habitacion.nombre,
        fecha_ingreso=_date(estancia.fecha_ingreso),
        fecha_salida=_date(salida),
        tiempo_estadia=_tiempo_estadia(estancia),
        estado=_choice_display(estancia, "estado"),
        observaciones=_display(estancia.observaciones),
    )


def _estancias_queryset():
    return EstanciaFamiliar.objects.select_related(
        "paciente__padre_tutor__usuario",
        "habitacion",
        "registrado_por",
    ).order_by("-fecha_ingreso", "paciente__apellidos", "paciente__nombres")


def build_reporte_estancias_context(user=None) -> dict:
    estancias = list(_estancias_queryset())
    habitaciones = list(HabitacionCasa.objects.filter(activa=True))
    activas_qs = EstanciaFamiliar.objects.filter(estado=EstanciaFamiliar.Estado.ACTIVA)
    disponibles = sum(1 for habitacion in habitaciones if habitacion.disponible)

    return {
        "titulo": REPORT_TITLE,
        "logo_static": LOGO_STATIC,
        "logo_path": _logo_path(),
        "fecha_generacion": timezone.localtime(),
        "generado_por": _user_name(user) if user else "",
        "estancias": estancias,
        "rows": [_row(estancia) for estancia in estancias],
        "resumen": {
            "estancias_activas": activas_qs.count(),
            "habitaciones_ocupadas": activas_qs.values("habitacion").distinct().count(),
            "habitaciones_disponibles": disponibles,
            "total_pacientes_hospedados": EstanciaFamiliar.objects.values("paciente").distinct().count(),
        },
        "footer_text": FOOTER_TEXT,
    }


def render_reporte_estancias_pdf(reporte: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.24 * inch,
        leftMargin=0.24 * inch,
        topMargin=0.24 * inch,
        bottomMargin=0.34 * inch,
        title=reporte["titulo"],
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReporteCasaTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        alignment=1,
    )
    small = ParagraphStyle(
        "ReporteCasaSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.8,
        leading=6.8,
    )
    bold = ParagraphStyle("ReporteCasaBold", parent=small, fontName="Helvetica-Bold")

    def para(value, style=small):
        return Paragraph(escape(_display(value)) or " ", style)

    story = []
    if reporte["logo_path"]:
        try:
            logo = Image(reporte["logo_path"], width=0.74 * inch, height=0.5 * inch)
        except Exception:
            logo = Paragraph("<b>FACCI</b>", title_style)
    else:
        logo = Paragraph("<b>FACCI</b>", title_style)

    fecha = timezone.localtime(reporte["fecha_generacion"]).strftime("%d/%m/%Y %I:%M %p")
    meta = Table(
        [
            [para("Fecha", bold), para(fecha)],
            [para("Generado por", bold), para(reporte["generado_por"] or "Sistema")],
        ],
        colWidths=[0.85 * inch, 1.7 * inch],
    )
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))

    header = Table([[logo, Paragraph(f"<b>{escape(reporte['titulo'])}</b>", title_style), meta]], colWidths=[0.9 * inch, 7.0 * inch, 2.55 * inch])
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.05 * inch))

    resumen = reporte["resumen"]
    summary = Table(
        [
            [para("Estancias activas", bold), para(resumen["estancias_activas"])],
            [para("Habitaciones ocupadas", bold), para(resumen["habitaciones_ocupadas"])],
            [para("Habitaciones disponibles", bold), para(resumen["habitaciones_disponibles"])],
            [para("Total pacientes hospedados", bold), para(resumen["total_pacientes_hospedados"])],
        ],
        colWidths=[1.55 * inch, 0.55 * inch],
    )
    summary.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9CA3AF")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7F2EC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary)
    story.append(Spacer(1, 0.05 * inch))

    data = [[
        para("Paciente", bold),
        para("Edad", bold),
        para("Diagnostico", bold),
        para("Responsable", bold),
        para("Parentesco", bold),
        para("Telefono", bold),
        para("Habitacion", bold),
        para("Ingreso", bold),
        para("Salida", bold),
        para("Tiempo", bold),
        para("Estado", bold),
        para("Observaciones", bold),
    ]]
    for row in reporte["rows"]:
        data.append([
            para(row.paciente),
            para(row.edad),
            para(row.diagnostico),
            para(row.responsable),
            para(row.parentesco),
            para(row.telefono),
            para(row.habitacion),
            para(row.fecha_ingreso),
            para(row.fecha_salida),
            para(row.tiempo_estadia),
            para(row.estado),
            para(row.observaciones),
        ])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            1.05 * inch,
            0.55 * inch,
            0.85 * inch,
            1.05 * inch,
            0.7 * inch,
            0.82 * inch,
            0.72 * inch,
            0.62 * inch,
            0.62 * inch,
            0.58 * inch,
            0.62 * inch,
            1.05 * inch,
        ],
    )
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9CA3AF")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.8),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(table)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(0.24 * inch, 0.2 * inch, reporte["footer_text"])
        canvas.drawCentredString(5.5 * inch, 0.2 * inch, f"Pagina {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
