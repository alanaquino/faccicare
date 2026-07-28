from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

from apps.padres.models import PadreTutor


DOCUMENT_CODE = "CN-A&S-F-01"
DOCUMENT_VERSION = "1"
LOGO_STATIC = "img/Logo-Facci-1.png"


@dataclass(frozen=True)
class FichaField:
    label: str
    value: str


def _logo_path() -> str:
    from apps.core.utils import get_system_logo_path_or_fallback
    return get_system_logo_path_or_fallback()


def _display(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _display_date(value) -> str:
    if not value:
        return ""
    return timezone.localtime(value).strftime("%d/%m/%Y") if hasattr(value, "hour") else value.strftime("%d/%m/%Y")


def _user_name(user) -> str:
    if not user:
        return ""
    return user.get_full_name() or user.username or ""


def _choice_display(obj, field_name: str) -> str:
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        return _display(method())
    return _display(getattr(obj, field_name, ""))


def _tutor_person_fields(tutor: PadreTutor | None) -> dict[str, str]:
    if not tutor:
        return {
            "nombre": "",
            "cedula": "",
            "estado_civil": "",
            "telefono": "",
            "celular": "",
            "direccion": "",
            "parentesco": "",
            "lugar_trabajo": "",
            "otros_contactos": "",
        }

    usuario = tutor.usuario
    contacto = " / ".join(
        part for part in [_display(tutor.contacto_emergencia), _display(tutor.telefono_emergencia)] if part
    )
    return {
        "nombre": _user_name(usuario),
        "cedula": _display(getattr(usuario, "cedula", "")),
        "estado_civil": _choice_display(tutor, "estado_civil"),
        "telefono": "",
        "celular": _display(getattr(usuario, "telefono", "")),
        "direccion": _display(tutor.direccion),
        "parentesco": _choice_display(tutor, "parentesco"),
        "lugar_trabajo": _display(tutor.ocupacion),
        "otros_contactos": contacto,
    }


def _section(title: str, fields: list[tuple[str, str]]) -> dict:
    pairs = [FichaField(label, _display(value)) for label, value in fields]
    rows = []
    for index in range(0, len(pairs), 2):
        row = pairs[index:index + 2]
        if len(row) == 1:
            row.append(FichaField("", ""))
        rows.append(row)
    return {"title": title, "rows": rows}


def build_ficha_context(paciente) -> dict:
    tutor = getattr(paciente, "padre_tutor", None)
    tutor_fields = _tutor_person_fields(tutor)

    madre_fields = _tutor_person_fields(tutor) if tutor and tutor.parentesco == PadreTutor.Parentesco.MADRE else _tutor_person_fields(None)
    padre_fields = _tutor_person_fields(tutor) if tutor and tutor.parentesco == PadreTutor.Parentesco.PADRE else _tutor_person_fields(None)

    seguro = bool(_display(getattr(paciente, "seguro_medico", "")) or _display(getattr(paciente, "numero_seguro", "")))
    cantidad_hijos = getattr(tutor, "cantidad_hijos", None) if tutor else None
    cantidad_hermanos = ""
    if cantidad_hijos is not None:
        cantidad_hermanos = str(max(int(cantidad_hijos) - 1, 0))

    paciente_fields = [
        ("Nombre", paciente.nombre_completo),
        ("Sexo", _choice_display(paciente, "sexo")),
        ("Edad", paciente.edad),
        ("Fecha nacimiento", _display_date(paciente.fecha_nacimiento)),
        ("Direccion", getattr(paciente, "direccion", "")),
        ("Diagnostico", _choice_display(paciente, "diagnostico")),
        ("Nombre de la doctora", _user_name(getattr(paciente, "medico_asignado", None))),
        ("Tipo sangre", _choice_display(paciente, "tipo_sangre")),
        ("Posee seguro medico", "Si" if seguro else "No"),
        ("ARS si aplica", getattr(paciente, "seguro_medico", "")),
        ("Esta vacunado/a", ""),
        ("Fecha diagnostico", ""),
        ("Cantidad hermanos", cantidad_hermanos),
        ("Codigo paciente", getattr(paciente, "codigo_paciente", "")),
    ]

    madre_section = [
        ("Nombre", madre_fields["nombre"]),
        ("Cedula", madre_fields["cedula"]),
        ("Estado civil", madre_fields["estado_civil"]),
        ("Telefono", madre_fields["telefono"]),
        ("Celular", madre_fields["celular"]),
        ("Lugar de trabajo", madre_fields["lugar_trabajo"]),
    ]
    padre_section = [
        ("Nombre", padre_fields["nombre"]),
        ("Estado civil", padre_fields["estado_civil"]),
        ("Telefono", padre_fields["telefono"]),
        ("Celular", padre_fields["celular"]),
        ("Lugar de trabajo", padre_fields["lugar_trabajo"]),
    ]
    tutor_section = [
        ("Nombre tutor responsable", tutor_fields["nombre"]),
        ("Cedula", tutor_fields["cedula"]),
        ("Estado civil", tutor_fields["estado_civil"]),
        ("Direccion", tutor_fields["direccion"]),
        ("Parentesco paciente", tutor_fields["parentesco"]),
        ("Celular", tutor_fields["celular"]),
        ("Lugar trabajo", tutor_fields["lugar_trabajo"]),
        ("Otros contactos", tutor_fields["otros_contactos"]),
    ]

    return {
        "codigo_documento": DOCUMENT_CODE,
        "version": DOCUMENT_VERSION,
        "fecha_documento": timezone.localdate().strftime("%d/%m/%Y"),
        "logo_static": LOGO_STATIC,
        "logo_path": _logo_path(),
        "titulo": "FICHA PACIENTE NUEVO",
        "paciente": paciente,
        "sections": [
            _section("A) DATOS DEL PACIENTE", paciente_fields),
            _section("B) DATOS DE LA MADRE", madre_section),
            _section("C) DATOS DEL PADRE", padre_section),
            _section("D) DATOS DEL TUTOR RESPONSABLE", tutor_section),
        ],
    }


def ficha_pdf_filename(paciente) -> str:
    base = slugify(paciente.nombre_completo) or "paciente"
    return f"ficha-paciente-{base}-{paciente.codigo_paciente}.pdf"


def render_ficha_pdf(ficha: dict) -> bytes:
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
        title=ficha["titulo"],
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FichaTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=13,
        textColor=colors.black,
        alignment=1,
    )
    small_style = ParagraphStyle(
        "FichaSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.6,
        leading=8,
        textColor=colors.black,
    )
    label_style = ParagraphStyle(
        "FichaLabel",
        parent=small_style,
        fontName="Helvetica-Bold",
    )
    value_style = ParagraphStyle(
        "FichaValue",
        parent=small_style,
        fontName="Helvetica",
    )
    section_style = ParagraphStyle(
        "FichaSection",
        parent=small_style,
        fontName="Helvetica-Bold",
        fontSize=7.4,
        leading=8.6,
    )

    def para(text, style):
        return Paragraph(escape(_display(text)) or " ", style)

    story = []
    if ficha["logo_path"]:
        try:
            logo = Image(ficha["logo_path"], width=0.86 * inch, height=0.58 * inch)
        except Exception:
            logo = Paragraph("<b>FACCI</b>", title_style)
    else:
        logo = Paragraph("<b>FACCI</b>", title_style)

    control_table = Table(
        [
            [para("Codigo:", label_style), para(ficha["codigo_documento"], value_style)],
            [para("Version:", label_style), para(ficha["version"], value_style)],
            [para("Fecha:", label_style), para(ficha["fecha_documento"], value_style)],
        ],
        colWidths=[0.58 * inch, 1.06 * inch],
    )
    control_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))

    header = Table(
        [[logo, Paragraph(f"<b>{escape(ficha['titulo'])}</b>", title_style), control_table]],
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

    for section in ficha["sections"]:
        data = [[Paragraph(f"<b>{escape(section['title'])}</b>", section_style), "", "", ""]]
        for row in section["rows"]:
            data.append([
                para(row[0].label, label_style),
                para(row[0].value, value_style),
                para(row[1].label, label_style),
                para(row[1].value, value_style),
            ])

        table = Table(data, colWidths=[1.28 * inch, 2.42 * inch, 1.28 * inch, 2.42 * inch], repeatRows=1)
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
        story.append(Spacer(1, 0.045 * inch))

    def footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(0.28 * inch, 0.22 * inch, "FACCI Care - Fundacion Amigos Contra el Cancer Infantil")
        canvas.drawCentredString(4.25 * inch, 0.22 * inch, f"Pagina {doc_obj.page}")
        canvas.drawRightString(8.22 * inch, 0.22 * inch, ficha["codigo_documento"])
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
