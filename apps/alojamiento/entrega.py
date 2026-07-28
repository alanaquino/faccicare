from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


DOCUMENT_CODE = "CAF-PRO-01"
DOCUMENT_ANNEX = "Anexo 4"
DOCUMENT_TITLE = "CONTROL DE ENTREGA DE HABITACION"
LOGO_STATIC = "img/Logo-Facci-1.png"
FINAL_TEXT = (
    "El detalle de lo entregado con la habitacion esta en perfectas condiciones, "
    "por lo que debe ser entregado en iguales condiciones, debiendo validar el "
    "paciente dicho estado y reportar cualquier inconveniente, lo cual constara "
    "como parte de las observaciones de este formulario."
)
CHECKLIST_ITEMS = [
    "Llaves",
    "Almohadas",
    "Sabanas",
    "Cubre cama",
    "Tinaco",
    "Banco",
    "Cepillo de limpiar bano",
    "Mesita de noche",
    "Cuna",
    "Cama",
    "Lampara",
    "Toallas",
    "Pasta",
    "Jabon",
    "Cepillo de dientes",
    "Shampoo",
    "Cuentos",
]


@dataclass(frozen=True)
class EntregaField:
    label: str
    value: str


def _logo_path() -> str:
    from apps.core.utils import get_system_logo_path_or_fallback
    return get_system_logo_path_or_fallback()


def _display(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _date(value) -> str:
    return value.strftime("%d/%m/%Y") if value else ""


def _time(value) -> str:
    return value.strftime("%I:%M %p") if value else ""


def _choice_display(obj, field_name: str) -> str:
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        return _display(method())
    return _display(getattr(obj, field_name, ""))


def ensure_entrega_items(entrega) -> None:
    existing = set(entrega.items.values_list("nombre_item", flat=True))
    missing = [
        entrega.items.model(entrega=entrega, nombre_item=nombre, orden=index)
        for index, nombre in enumerate(CHECKLIST_ITEMS, start=1)
        if nombre not in existing
    ]
    if missing:
        entrega.items.bulk_create(missing)


def _responsable(estancia) -> dict[str, str]:
    tutor = getattr(estancia.paciente, "padre_tutor", None)
    parentesco = _display(estancia.acompanante_parentesco) or _choice_display(tutor, "parentesco")
    return {
        "nombre": _display(estancia.acompanante_nombre),
        "parentesco": parentesco,
        "telefono": _display(estancia.acompanante_telefono),
    }


def _section(fields: list[tuple[str, str]]) -> list[list[EntregaField]]:
    pairs = [EntregaField(label, _display(value)) for label, value in fields]
    rows = []
    for index in range(0, len(pairs), 2):
        row = pairs[index:index + 2]
        if len(row) == 1:
            row.append(EntregaField("", ""))
        rows.append(row)
    return rows


def build_entrega_context(entrega) -> dict:
    estancia = entrega.estancia
    paciente = estancia.paciente
    responsable = _responsable(estancia)
    fecha_salida = estancia.fecha_egreso_real or estancia.fecha_egreso_prevista
    items = list(entrega.items.all())

    return {
        "codigo_documento": DOCUMENT_CODE,
        "anexo": DOCUMENT_ANNEX,
        "titulo": DOCUMENT_TITLE,
        "logo_static": LOGO_STATIC,
        "logo_path": _logo_path(),
        "fecha_documento": timezone.localdate().strftime("%d/%m/%Y"),
        "estancia": estancia,
        "entrega": entrega,
        "items": items,
        "final_text": FINAL_TEXT,
        "paciente_rows": _section([
            ("Nombre del paciente", paciente.nombre_completo),
            ("Edad", paciente.edad),
            ("Familiar responsable", responsable["nombre"]),
            ("Parentesco", responsable["parentesco"]),
        ]),
        "habitacion_rows": _section([
            ("Numero de habitacion", estancia.habitacion.nombre),
            ("Nombre de habitacion", estancia.habitacion.descripcion),
            ("Fecha de ingreso", _date(estancia.fecha_ingreso)),
            ("Hora de ingreso", _time(entrega.hora_ingreso)),
            ("Fecha de salida", _date(fecha_salida)),
            ("Hora de salida", _time(entrega.hora_salida)),
        ]),
        "firmas": [
            ("Entregado por", entrega.entregado_por_facci or "Encargado Administrativo FACCI"),
            ("Recibido por", entrega.recibido_por_familiar or responsable["nombre"] or "Representante del Paciente"),
            ("Entregado por", entrega.entregado_por_familiar or responsable["nombre"] or "Representante del Paciente"),
            ("Recibido por", entrega.recibido_por_facci or "Encargado Administrativo FACCI"),
        ],
    }


def entrega_pdf_filename(entrega) -> str:
    codigo = slugify(entrega.estancia.codigo) or str(entrega.estancia.pk)
    return f"entrega_habitacion_{codigo}.pdf"


def render_entrega_pdf(context: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.24 * inch,
        leftMargin=0.24 * inch,
        topMargin=0.22 * inch,
        bottomMargin=0.32 * inch,
        title=context["titulo"],
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EntregaTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=10.6,
        leading=12,
        alignment=1,
    )
    small = ParagraphStyle(
        "EntregaSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.2,
        leading=7.3,
    )
    bold = ParagraphStyle("EntregaBold", parent=small, fontName="Helvetica-Bold")
    section_style = ParagraphStyle("EntregaSection", parent=bold, fontSize=6.9, leading=8)

    def para(value, style=small):
        return Paragraph(escape(_display(value)) or " ", style)

    story = []
    if context["logo_path"]:
        try:
            logo = Image(context["logo_path"], width=0.74 * inch, height=0.5 * inch)
        except Exception:
            logo = Paragraph("<b>FACCI</b>", title_style)
    else:
        logo = Paragraph("<b>FACCI</b>", title_style)

    control = Table(
        [
            [para("Codigo:", bold), para(context["codigo_documento"])],
            [para("Anexo:", bold), para(context["anexo"])],
            [para("Fecha:", bold), para(context["fecha_documento"])],
        ],
        colWidths=[0.55 * inch, 1.0 * inch],
    )
    control.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))

    header = Table([[logo, Paragraph(f"<b>{escape(context['titulo'])}</b>", title_style), control]], colWidths=[0.95 * inch, 4.88 * inch, 1.55 * inch])
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.04 * inch))

    def add_section(title, rows):
        data = [[Paragraph(f"<b>{escape(title)}</b>", section_style), "", "", ""]]
        for row in rows:
            data.append([para(row[0].label, bold), para(row[0].value), para(row[1].label, bold), para(row[1].value)])
        table = Table(data, colWidths=[1.28 * inch, 2.42 * inch, 1.28 * inch, 2.42 * inch])
        table.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.035 * inch))

    add_section("DATOS DEL PACIENTE", context["paciente_rows"])
    add_section("DATOS DE LA HABITACION", context["habitacion_rows"])

    checklist = [[
        para("Item", bold),
        para("Entregado por FACCI", bold),
        para("Recibido del familiar responsable", bold),
        para("Observacion", bold),
    ]]
    for item in context["items"]:
        checklist.append([
            para(item.nombre_item),
            para("Si" if item.entregado_por_facci else "No"),
            para("Si" if item.recibido_por_familiar else "No"),
            para(item.observacion),
        ])
    table = Table(checklist, repeatRows=1, colWidths=[2.0 * inch, 1.45 * inch, 2.05 * inch, 1.9 * inch])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.035 * inch))

    observations = Table(
        [
            [Paragraph("<b>OBSERVACIONES GENERALES</b>", section_style)],
            [para(context["entrega"].observaciones)],
            [para(context["final_text"])],
        ],
        colWidths=[7.4 * inch],
    )
    observations.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(observations)
    story.append(Spacer(1, 0.06 * inch))

    firmas = []
    for label, value in context["firmas"]:
        firmas.append(Paragraph(f"<b>{escape(label)}:</b> {escape(_display(value))}<br/>______________________________", small))
    signature = Table([firmas[:2], firmas[2:]], colWidths=[3.7 * inch, 3.7 * inch])
    signature.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(signature)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(0.24 * inch, 0.2 * inch, "FACCI Care - Casa FACCI")
        canvas.drawCentredString(4.25 * inch, 0.2 * inch, f"Pagina {doc_obj.page}")
        canvas.drawRightString(8.24 * inch, 0.2 * inch, context["codigo_documento"])
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
