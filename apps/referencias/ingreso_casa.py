from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


DOCUMENT_TITLE = "FICHA DE INGRESO CASA FACCI"
DOCUMENT_CODE = "CAF-ING-01"
LOGO_STATIC = "img/Logo-Facci-1.png"
FOOTER_TEXT = "FACCI Care - Casa FACCI"


@dataclass(frozen=True)
class IngresoField:
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


def _choice_display(obj, field_name: str) -> str:
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        return _display(method())
    return _display(getattr(obj, field_name, ""))


def _user_name(user) -> str:
    if not user:
        return ""
    return user.get_full_name() or user.username or ""


def _section(title: str, fields: list[tuple[str, str]]) -> dict:
    pairs = [IngresoField(label, _display(value)) for label, value in fields]
    rows = []
    for index in range(0, len(pairs), 2):
        row = pairs[index:index + 2]
        if len(row) == 1:
            row.append(IngresoField("", ""))
        rows.append(row)
    return {"title": title, "rows": rows}


def build_ingreso_casa_context(ingreso) -> dict:
    paciente = ingreso.paciente
    referencia = ingreso.referencia_medica
    fecha_referencia = referencia.fecha_referencia if referencia else ingreso.fecha_creacion
    prioridad = referencia.get_prioridad_display() if referencia else ""
    estado_referencia = referencia.get_estado_display() if referencia else ingreso.get_estado_display()

    return {
        "codigo_documento": DOCUMENT_CODE,
        "titulo": DOCUMENT_TITLE,
        "logo_static": LOGO_STATIC,
        "logo_path": _logo_path(),
        "fecha_documento": timezone.localdate().strftime("%d/%m/%Y"),
        "ingreso": ingreso,
        "referencia": referencia,
        "paciente": paciente,
        "footer_text": FOOTER_TEXT,
        "sections": [
            _section(
                "1. DATOS DEL PACIENTE",
                [
                    ("Nombre del paciente", paciente.nombre_completo),
                    ("Codigo FACCI", paciente.codigo_paciente),
                    ("Edad", paciente.edad),
                    ("Sexo", _choice_display(paciente, "sexo")),
                    ("Fecha de nacimiento", _date(paciente.fecha_nacimiento)),
                    ("Diagnostico", _choice_display(paciente, "diagnostico")),
                    ("Centro de origen", ingreso.centro_origen.nombre if ingreso.centro_origen else ""),
                    ("Hospital destino", ingreso.hospital_destino.nombre if ingreso.hospital_destino else ""),
                    ("Fecha de referencia", _date(fecha_referencia.date() if hasattr(fecha_referencia, "date") else fecha_referencia)),
                    ("Prioridad", prioridad),
                    ("Estado", estado_referencia),
                    ("Medico / usuario referente", _user_name(getattr(referencia, "medico_referente", None)) if referencia else _user_name(ingreso.creado_por)),
                ],
            ),
            _section(
                "2. DATOS DEL FAMILIAR / RESPONSABLE",
                [
                    ("Nombre del responsable", ingreso.responsable_paciente),
                    ("Parentesco", ingreso.parentesco_responsable),
                    ("Cedula", ingreso.cedula_responsable),
                    ("Telefono", ingreso.telefono_responsable),
                    ("Celular", ingreso.celular_responsable),
                    ("Direccion", ingreso.direccion_responsable),
                    ("Ocupacion", ingreso.ocupacion_responsable),
                    ("Observaciones", ingreso.observaciones),
                ],
            ),
            _section(
                "3. DATOS DE INGRESO CASA FACCI",
                [
                    ("Motivo de ingreso", ingreso.motivo_ingreso),
                    ("Tiempo estimado de estadia", ingreso.tiempo_estadia),
                    ("Fecha de entrada", _date(ingreso.fecha_entrada)),
                    ("Fecha de salida", _date(ingreso.fecha_salida)),
                    ("Habitacion asignada", ingreso.habitacion.nombre if ingreso.habitacion else ""),
                    ("Responsable que registra", _user_name(ingreso.creado_por)),
                    ("Estado del ingreso", ingreso.get_estado_display()),
                    ("Codigo de formulario", ingreso.codigo),
                ],
            ),
        ],
    }


def ingreso_pdf_filename(ingreso) -> str:
    codigo = slugify(ingreso.paciente.codigo_paciente) or str(ingreso.paciente.pk)
    return f"ingreso_casa_facci_{codigo}.pdf"


def render_ingreso_casa_pdf(context: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.28 * inch,
        leftMargin=0.28 * inch,
        topMargin=0.24 * inch,
        bottomMargin=0.34 * inch,
        title=context["titulo"],
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "IngresoCasaTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=11.4,
        leading=13,
        alignment=1,
        textColor=colors.black,
    )
    small_style = ParagraphStyle(
        "IngresoCasaSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.7,
        leading=8.1,
        textColor=colors.black,
    )
    label_style = ParagraphStyle("IngresoCasaLabel", parent=small_style, fontName="Helvetica-Bold")
    section_style = ParagraphStyle("IngresoCasaSection", parent=label_style, fontSize=7.4, leading=8.6)

    def para(text, style=small_style):
        return Paragraph(escape(_display(text)) or " ", style)

    story = []
    if context["logo_path"]:
        try:
            logo = Image(context["logo_path"], width=0.86 * inch, height=0.58 * inch)
        except Exception:
            logo = Paragraph("<b>FACCI</b>", title_style)
    else:
        logo = Paragraph("<b>FACCI</b>", title_style)

    control = Table(
        [
            [para("Codigo:", label_style), para(context["codigo_documento"])],
            [para("Fecha:", label_style), para(context["fecha_documento"])],
            [para("Formulario:", label_style), para(context["ingreso"].codigo)],
        ],
        colWidths=[0.66 * inch, 1.12 * inch],
    )
    control.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))

    header = Table(
        [[logo, Paragraph(f"<b>{escape(context['titulo'])}</b>", title_style), control]],
        colWidths=[1.02 * inch, 4.55 * inch, 1.83 * inch],
    )
    header.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.05 * inch))

    for section in context["sections"]:
        data = [[Paragraph(f"<b>{escape(section['title'])}</b>", section_style), "", "", ""]]
        for row in section["rows"]:
            data.append([
                para(row[0].label, label_style),
                para(row[0].value),
                para(row[1].label, label_style),
                para(row[1].value),
            ])

        table = Table(data, colWidths=[1.36 * inch, 2.34 * inch, 1.36 * inch, 2.34 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.045 * inch))

    signature = Table(
        [
            [Paragraph("<b>4. FIRMA Y VALIDACION</b>", section_style)],
            [Paragraph("____________________________________________<br/>Firma del familiar responsable", small_style)],
            [Paragraph("____________________________________________<br/>Firma y sello FACCI", small_style)],
        ],
        colWidths=[7.4 * inch],
        # Altura para que haya espacio en blanco encima de la linea y se pueda
        # firmar a mano sobre ella.
        rowHeights=[None, 0.72 * inch, 0.72 * inch],
    )
    signature.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"),
        # La linea y su leyenda van pegadas abajo: se firma SOBRE la linea y el
        # espacio en blanco queda encima para la firma manual.
        ("VALIGN", (0, 1), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(signature)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(0.28 * inch, 0.22 * inch, context["footer_text"])
        canvas.drawCentredString(4.25 * inch, 0.22 * inch, f"Pagina {doc_obj.page}")
        canvas.drawRightString(8.22 * inch, 0.22 * inch, context["codigo_documento"])
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
