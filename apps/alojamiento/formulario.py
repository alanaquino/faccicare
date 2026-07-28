from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


DOCUMENT_CODE = "CN-A&S-F-08"
DOCUMENT_VERSION = "1"
LOGO_STATIC = "img/Logo-Facci-1.png"
ACCEPTANCE_TEXT = (
    "Yo acepto el ingreso de la CASA FACCI, me declaro en conocimiento del "
    "reglamento para estadia en la misma y me comprometo a su cumplimiento "
    "tanto por mi parte como por parte del paciente al que acompano."
)


@dataclass(frozen=True)
class FormularioField:
    label: str
    value: str


def _logo_path() -> str:
    from apps.core.utils import get_system_logo_path_or_fallback
    return get_system_logo_path_or_fallback()


def _display(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _display_date(value) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def _choice_display(obj, field_name: str) -> str:
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        return _display(method())
    return _display(getattr(obj, field_name, ""))


def _user_name(user) -> str:
    if not user:
        return ""
    return user.get_full_name() or user.username or ""


def _responsable_data(estancia) -> dict[str, str]:
    tutor = getattr(estancia.paciente, "padre_tutor", None)
    tutor_user = getattr(tutor, "usuario", None) if tutor else None

    return {
        "nombre": _display(estancia.acompanante_nombre) or _user_name(tutor_user),
        "parentesco": _display(estancia.acompanante_parentesco) or _choice_display(tutor, "parentesco"),
        "telefono": _display(getattr(tutor, "telefono_emergencia", "")) if tutor else "",
        "celular": _display(estancia.acompanante_telefono) or _display(getattr(tutor_user, "telefono", "")),
        "cedula": _display(getattr(tutor_user, "cedula", "")),
        "estado_civil": _choice_display(tutor, "estado_civil"),
        "ocupacion": _display(getattr(tutor, "ocupacion", "")),
        "salario": _display(getattr(tutor, "ingresos_aproximados", "")),
        "edad": "",
    }


def _tiempo_estadia(estancia) -> str:
    salida = estancia.fecha_egreso_real or estancia.fecha_egreso_prevista
    if salida and estancia.fecha_ingreso:
        dias = max(0, (salida - estancia.fecha_ingreso).days)
        if dias == 1:
            return "1 noche"
        return f"{dias} noches"
    noches = estancia.noches
    if noches is not None:
        if noches == 1:
            return "1 noche"
        return f"{noches} noches"
    return ""


def _section(title: str, fields: list[tuple[str, str]]) -> dict:
    pairs = [FormularioField(label, _display(value)) for label, value in fields]
    rows = []
    for index in range(0, len(pairs), 2):
        row = pairs[index:index + 2]
        if len(row) == 1:
            row.append(FormularioField("", ""))
        rows.append(row)
    return {"title": title, "rows": rows}


def build_formulario_context(estancia) -> dict:
    paciente = estancia.paciente
    responsable = _responsable_data(estancia)
    fecha_salida = estancia.fecha_egreso_real or estancia.fecha_egreso_prevista
    motivo = _choice_display(estancia, "motivo")
    if estancia.observaciones:
        motivo = f"{motivo}. {estancia.observaciones}".strip()

    return {
        "codigo_documento": DOCUMENT_CODE,
        "version": DOCUMENT_VERSION,
        "fecha_documento": timezone.localdate().strftime("%d/%m/%Y"),
        "logo_static": LOGO_STATIC,
        "logo_path": _logo_path(),
        "titulo": "HOJA DE REFERIMIENTO INGRESO CASA FACCI",
        "estancia": estancia,
        "acceptance_text": ACCEPTANCE_TEXT,
        "sections": [
            _section(
                "1. DATOS DEL PACIENTE Y FAMILIAR RESPONSABLE",
                [
                    ("Nombre del paciente", paciente.nombre_completo),
                    ("Edad", paciente.edad),
                    ("Diagnostico", _choice_display(paciente, "diagnostico")),
                    ("Responsable del paciente", responsable["nombre"]),
                    ("Parentesco con paciente", responsable["parentesco"]),
                    ("Edad del responsable", responsable["edad"]),
                    ("Fecha de nacimiento", _display_date(paciente.fecha_nacimiento)),
                    ("Sexo", _choice_display(paciente, "sexo")),
                    ("Estado civil", responsable["estado_civil"]),
                    ("Cedula", responsable["cedula"]),
                    ("Ocupacion", responsable["ocupacion"]),
                    ("Salario", responsable["salario"]),
                    ("Telefono", responsable["telefono"]),
                    ("Celular", responsable["celular"]),
                ],
            ),
            _section(
                "2. DATOS DEL REFERIMIENTO",
                [
                    ("Motivos de referimiento", motivo),
                    ("Tiempo de estadia", _tiempo_estadia(estancia)),
                    ("Fecha de entrada", _display_date(estancia.fecha_ingreso)),
                    ("Fecha de salida", _display_date(fecha_salida)),
                    ("Numero de habitacion", estancia.habitacion.nombre),
                    ("Codigo estancia", estancia.codigo),
                ],
            ),
        ],
    }


def formulario_pdf_filename(estancia) -> str:
    codigo = slugify(estancia.codigo) or str(estancia.pk)
    return f"estancia_casa_facci_{codigo}.pdf"


def render_formulario_pdf(formulario: dict) -> bytes:
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
        title=formulario["titulo"],
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CasaFacciTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=11.2,
        leading=13,
        textColor=colors.black,
        alignment=1,
    )
    small_style = ParagraphStyle(
        "CasaFacciSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.7,
        leading=8.1,
        textColor=colors.black,
    )
    label_style = ParagraphStyle("CasaFacciLabel", parent=small_style, fontName="Helvetica-Bold")
    value_style = ParagraphStyle("CasaFacciValue", parent=small_style, fontName="Helvetica")
    section_style = ParagraphStyle(
        "CasaFacciSection",
        parent=small_style,
        fontName="Helvetica-Bold",
        fontSize=7.4,
        leading=8.6,
    )

    def para(text, style):
        return Paragraph(escape(_display(text)) or " ", style)

    story = []
    if formulario["logo_path"]:
        try:
            logo = Image(formulario["logo_path"], width=0.86 * inch, height=0.58 * inch)
        except Exception:
            logo = Paragraph("<b>FACCI</b>", title_style)
    else:
        logo = Paragraph("<b>FACCI</b>", title_style)

    control = Table(
        [
            [para("Codigo:", label_style), para(formulario["codigo_documento"], value_style)],
            [para("Version:", label_style), para(formulario["version"], value_style)],
            [para("Fecha:", label_style), para(formulario["fecha_documento"], value_style)],
        ],
        colWidths=[0.58 * inch, 1.06 * inch],
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
        [[logo, Paragraph(f"<b>{escape(formulario['titulo'])}</b>", title_style), control]],
        colWidths=[1.02 * inch, 4.74 * inch, 1.64 * inch],
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
    story.append(Spacer(1, 0.06 * inch))

    for section in formulario["sections"]:
        data = [[Paragraph(f"<b>{escape(section['title'])}</b>", section_style), "", "", ""]]
        for row in section["rows"]:
            data.append([
                para(row[0].label, label_style),
                para(row[0].value, value_style),
                para(row[1].label, label_style),
                para(row[1].value, value_style),
            ])

        table = Table(data, colWidths=[1.36 * inch, 2.34 * inch, 1.36 * inch, 2.34 * inch], repeatRows=1)
        table.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.05 * inch))

    signature_data = [
        [Paragraph("<b>3. FIRMA</b>", section_style)],
        [Paragraph(escape(formulario["acceptance_text"]), value_style)],
        [Paragraph("____________________________________________<br/>Firma del familiar responsable", value_style)],
    ]
    # Fila de firma con altura para dejar espacio en blanco encima de la linea.
    signature = Table(signature_data, colWidths=[7.4 * inch], rowHeights=[None, None, 1.5 * inch])
    signature.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDEFE7")),
        # La linea y su leyenda van pegadas abajo: se firma SOBRE la linea y el
        # espacio en blanco queda encima para la firma manual.
        ("VALIGN", (0, 2), (-1, 2), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(signature)

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(0.28 * inch, 0.22 * inch, "FACCI Care - Casa FACCI")
        canvas.drawCentredString(4.25 * inch, 0.22 * inch, f"Pagina {doc_obj.page}")
        canvas.drawRightString(8.22 * inch, 0.22 * inch, formulario["codigo_documento"])
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
