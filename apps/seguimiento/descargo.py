from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.padres.models import PadreTutor


LOGO_STATIC = "img/Logo-Facci-1.png"
DOCUMENT_TITLE = "Descargo de Responsabilidad y Consentimiento Para el Tratamiento Medico a un Menor"
CEDULA_DOMINICANA_RE = re.compile(r"^(?:\d{11}|\d{3}-\d{7}-\d)$")
FOOTER_LINES = [
    "FUNDACION AMIGOS CONTRA EL CANCER INFANTIL",
    "@facci_rd   -   www.facci.org.do   -   faccifundacion@facci.org.do   -   RNC: 430-00602-5",
    "809-533-7596   -   Calle Antonio Maceo #6, sector Mata Hambre, La Feria, Santo Domingo, R.D.",
]
MESES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


@dataclass(frozen=True)
class PersonaDescargo:
    nombre: str = ""
    cedula: str = ""
    tipo_documento: str = "CEDULA"
    nacionalidad: str = ""
    direccion: str = ""
    parentesco: str = ""
    genero_gramatical: str = ""

    @property
    def documento_tipo_label(self) -> str:
        return "Pasaporte" if self.tipo_documento == "PASAPORTE" else "Cédula"


def _logo_path() -> str:
    from apps.core.utils import get_system_logo_path_or_fallback
    return get_system_logo_path_or_fallback()


def _display(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _cedula_dominicana_valida(cedula: str) -> bool:
    text = _display(cedula).replace(" ", "")
    return bool(CEDULA_DOMINICANA_RE.fullmatch(text))


def _nacionalidad_from_tutor(tutor: PadreTutor | None, user) -> str:
    nacionalidad = _display(getattr(tutor, "nacionalidad", ""))
    if nacionalidad:
        return nacionalidad
    if _cedula_dominicana_valida(getattr(user, "cedula", "")):
        return "Dominicana"
    return ""


def _choice_display(instance, field_name: str) -> str:
    raw_value = _display(getattr(instance, field_name, ""))
    if not raw_value:
        return ""
    getter = getattr(instance, f"get_{field_name}_display", None)
    if callable(getter):
        return _display(getter())
    return raw_value


def _join_unique(values: list[str]) -> str:
    clean = []
    for value in values:
        text = _display(value)
        if text and text not in clean:
            clean.append(text)
    if len(clean) <= 1:
        return clean[0] if clean else ""
    return ", ".join(clean[:-1]) + " y " + clean[-1]


def _line(value: str, length: int = 34) -> str:
    text = _display(value)
    return text if text else "_" * length


def _user_name(user) -> str:
    if not user:
        return ""
    return user.get_full_name() or user.username or ""


def _genero_gramatical_tutor(tutor: PadreTutor | None) -> str:
    if not tutor:
        return ""
    if tutor.parentesco == PadreTutor.Parentesco.MADRE:
        return "F"
    if tutor.parentesco in (PadreTutor.Parentesco.PADRE, PadreTutor.Parentesco.TUTOR):
        return "M"
    return ""


def _persona_terms(persona: PersonaDescargo) -> dict[str, str]:
    if persona.genero_gramatical == "F":
        return {
            "domiciliado": "domiciliada",
            "portador": "portadora",
        }
    if persona.genero_gramatical == "M":
        return {
            "domiciliado": "domiciliado",
            "portador": "portador",
        }
    return {
        "domiciliado": "domiciliado(a)",
        "portador": "portador(a)",
    }


def _persona_from_tutor(tutor: PadreTutor | None) -> PersonaDescargo:
    if not tutor:
        return PersonaDescargo()
    user = tutor.usuario
    return PersonaDescargo(
        nombre=_user_name(user),
        cedula=_display(getattr(user, "cedula", "")),
        tipo_documento=_display(getattr(user, "tipo_documento", "CEDULA")),
        nacionalidad=_nacionalidad_from_tutor(tutor, user),
        direccion=_display(getattr(tutor, "direccion", "")),
        parentesco=_display(tutor.get_parentesco_display()),
        genero_gramatical=_genero_gramatical_tutor(tutor),
    )


def _madre_padre(paciente) -> tuple[PersonaDescargo, PersonaDescargo, PersonaDescargo]:
    tutor = getattr(paciente, "padre_tutor", None)
    responsable = _persona_from_tutor(tutor)
    madre = PersonaDescargo()
    padre = PersonaDescargo()

    if tutor and tutor.parentesco == PadreTutor.Parentesco.MADRE:
        madre = responsable
    elif tutor and tutor.parentesco == PadreTutor.Parentesco.PADRE:
        padre = responsable

    return madre, padre, responsable


def _firmantes(madre: PersonaDescargo, padre: PersonaDescargo, responsable: PersonaDescargo) -> list[PersonaDescargo]:
    firmantes = [persona for persona in (madre, padre) if persona.nombre or persona.cedula]
    if firmantes:
        return firmantes
    if responsable.nombre or responsable.cedula:
        return [responsable]
    return [PersonaDescargo(parentesco="Madre/Padre/Tutor")]


def _menor_terms(paciente) -> dict[str, str]:
    es_femenino = _display(getattr(paciente, "sexo", "")).upper() == "F"
    return {
        "articulo": "la" if es_femenino else "el",
        "de": "de la" if es_femenino else "del",
        "a": "a la" if es_femenino else "al",
        "acompanado": "acompanada" if es_femenino else "acompanado",
        "referido": "referida" if es_femenino else "referido",
    }


def build_descargo_context(paciente) -> dict:
    madre, padre, responsable = _madre_padre(paciente)
    firmantes = _firmantes(madre, padre, responsable)
    menor_terms = _menor_terms(paciente)
    direccion = madre.direccion or padre.direccion or responsable.direccion or _display(getattr(paciente, "direccion", ""))
    diagnostico = _choice_display(paciente, "diagnostico")
    fecha_actual = timezone.localdate()

    nombre_madre = f"<b>{escape(_line(madre.nombre))}</b>"
    nombre_padre = f"<b>{escape(_line(padre.nombre))}</b>"
    cedula_madre = f"<b>{escape(_line(madre.cedula, 18))}</b>"
    cedula_padre = f"<b>{escape(_line(padre.cedula, 18))}</b>"
    nacionalidad_val = f"<b>{escape(_line(_join_unique([madre.nacionalidad, padre.nacionalidad]), 18))}</b>"
    domicilio = f"<b>{escape(_line(direccion, 54))}</b>"
    menor = f"<b>{escape(_line(paciente.nombre_completo, 34))}</b>"
    
    if len(firmantes) == 1:
        firmante = firmantes[0]
        firmante_terms = _persona_terms(firmante)
        parentesco_val = firmante.parentesco or "tutor responsable"
        doc_prefix = "de la" if firmante.tipo_documento == "CEDULA" else "del"
        primer_parrafo = (
            f"Quien suscribe, <b>{escape(_line(firmante.nombre))}</b>, de nacionalidad "
            f"<b>{escape(_line(firmante.nacionalidad, 18))}</b>, mayor de edad, {firmante_terms['domiciliado']} y residente "
            f"en {domicilio}, {firmante_terms['portador']} {doc_prefix} {firmante.documento_tipo_label} No. <b>{escape(_line(firmante.cedula, 18))}</b>; "
            f"en calidad de <b>{escape(_line(parentesco_val, 18))}</b> {menor_terms['de']} menor "
            f"de edad {menor}, por el presente documento, tiene a bien declarar y hacer constar "
            "lo siguiente:"
        )
    else:
        madre_prefix = "de la" if madre.tipo_documento == "CEDULA" else "del"
        padre_prefix = "de la" if padre.tipo_documento == "CEDULA" else "del"
        madre_doc = f"{madre_prefix} {madre.documento_tipo_label} No. {cedula_madre}"
        padre_doc = f"{padre_prefix} {padre.documento_tipo_label} No. {cedula_padre}"
        primer_parrafo = (
            f"Quienes suscriben, {nombre_madre} y {nombre_padre}, de nacionalidad "
            f"{nacionalidad_val}, mayores de edad, domiciliados(as) y residentes en {domicilio}, "
            f"portadores {madre_doc} y {padre_doc}; en calidad de "
            f"la <b>Madre y el Padre</b> {menor_terms['de']} menor de edad {menor}, por el presente documento, "
            "tenemos a bien declarar y hacer constar lo siguiente:"
        )

    condicion_salud = f"Que {menor_terms['articulo']} menor <b>{escape(_line(paciente.nombre_completo))}</b>"
    if diagnostico:
        condicion_salud += f", con diagnóstico <b>{escape(diagnostico)}</b>,"
    else:
        condicion_salud += ", por sus condiciones de salud,"
    condicion_salud += (
        " pertenece a uno de los programas de apoyo del área de Oncología-Hematología del "
        "Hospital Infantil Dr. Robert Reid Cabral (HIRRC)."
    )

    conditions = [
        condicion_salud,
        (
            f"Que en razón de que {menor_terms['articulo']} menor requiere tratamiento ambulatorio especializado, "
            f"ha sido {menor_terms['referido']} (a) por el personal médico Oncólogo-Hematólogo del Hospital Infantil "
            f"Dr. Robert Reid Cabral (HIRRC) a <b>Casa FACCI</b>, un albergue gratuito destinado específicamente a estos fines."
        ),
        (
            "En consecuencia, autorizamos por el tiempo que considere necesario el personal médico "
            f"Oncólogo-Hematólogo del HIRRC, el alojamiento {menor_terms['de']} menor <b>Casa FACCI</b>, a los fines "
            "de que, durante su hospedaje, pueda recibir el tratamiento ambulatorio especializado "
            "que requiere."
        ),
        (
            f"Que es de nuestro conocimiento que {menor_terms['articulo']} menor, durante su hospedaje en <b>Casa FACCI</b> "
            f"siempre deberá estar {menor_terms['acompanado']} (a) de un familiar, que será responsable de brindar "
            f"asistencia y soporte durante la estadía {menor_terms['de']} menor en la misma; y que en caso de "
            "que dicho acompañante necesite salir de la casa por algún motivo, deberá notificarlo "
            "mediante una solicitud de permiso, que solicitará al Trabajador Social que le esté asignado, "
            "donde especificará el motivo, la hora de su entrada y salida."
        ),
        (
            "Que al ingresar en <b>Casa FACCI</b>, se nos ha leído el Reglamento de dicha entidad que "
            "indica las normas de comportamiento que deben respetarse durante la estadía en Casa "
            "<b>FACCI</b>, así como los beneficios y las facilidades que el paciente tendrá durante su "
            "permanencia en la Casa."
        ),
        (
            "Que nos obligamos y comprometemos a respetar todos los lineamientos, políticas y normas "
            "del Reglamento de <b>Casa FACCI</b>, los cuales declaramos conocer en forma completa; así como "
            "a suministrar todos los requerimientos que nos sean solicitados a los fines de facilitar "
            f"el ingreso y la estadía {menor_terms['de']} menor en la Casa Albergue."
        ),
        (
            "Que además de la estadía en <b>Casa FACCI</b>, hemos solicitado a la <b>Fundación "
            "Amigos contra el Cáncer Infantil (FACCI)</b>, ayuda económica para adquirir los "
            f"medicamentos que requiere {menor_terms['articulo']} menor, prescritos por el personal médico "
            "que le atiende en el HIRRC."
        ),
        (
            f"Que liberamos y descargamos a <b>FACCI</b>, al personal administrativo y personal "
            "de servicio en el albergue, de cualquier responsabilidad que se pretenda "
            f"imputar por los resultados o reacciones que pueda tener {menor_terms['articulo']} menor como "
            "consecuencia de la administración de los medicamentos que le han sido "
            "prescritos, en razón de que dicha Fundación solo nos ha proporcionado el "
            "alojamiento y la ayuda económica necesarias para el tratamiento "
            f"ambulatorio especializado que requiere {menor_terms['articulo']} menor."
        ),
        (
            "Asimismo, declaramos libre y voluntariamente que renunciamos de manera formal, expresa, "
            "definitiva, y sin reservas a toda reclamación, acción, instancia, derecho, pretensión, "
            "demanda o interés, presente o futuro contra <b>FACCI, sus representantes, personal "
            "administrativo y/o personal de servicio</b>, por entender que dicha Fundación solo nos ha "
            f"otorgado alojamiento y ayuda económica para el tratamiento médico {menor_terms['de']} menor y que "
            "en ningún caso es responsable por los resultados o reacciones que pudiera causar algún "
            f"medicamento que bajo prescripción médica se suministre a {menor_terms['articulo']} menor "
            f"durante su estadía en <b>Casa FACCI</b>."
        ),
    ]
    paragraphs = [primer_parrafo, *conditions]

    return {
        "titulo": DOCUMENT_TITLE,
        "logo_static": LOGO_STATIC,
        "logo_path": _logo_path(),
        "paciente": paciente,
        "madre": madre,
        "padre": padre,
        "responsable": responsable,
        "firmantes": firmantes,
        "intro_text": primer_parrafo,
        "conditions": conditions,
        "paragraphs": paragraphs,
        "nacionalidad_warning": any(not firmante.nacionalidad for firmante in firmantes),
        "ciudad": "Santo Domingo, Distrito Nacional",
        "fecha_actual": fecha_actual,
        "fecha_documento": fecha_actual.strftime("%d/%m/%Y"),
        "dia": fecha_actual.day,
        "mes": MESES[fecha_actual.month],
        "anio": fecha_actual.year,
        "footer_lines": FOOTER_LINES,
    }


def descargo_pdf_filename(paciente) -> str:
    return f"descargo_tratamiento_{paciente.codigo_paciente}.pdf"


def render_descargo_pdf(descargo: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, PageBreak

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=40,
        bottomMargin=72,  # Margen inferior suficiente para el pie de página
        title=descargo["titulo"],
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DescargoTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=14.0,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=18,
    )
    body_style = ParagraphStyle(
        "DescargoBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.8,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=11,
    )
    center_style = ParagraphStyle(
        "DescargoCenter",
        parent=body_style,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    story = []
    
    # --- PÁGINA 1 ---
    # Logo
    if descargo["logo_path"]:
        try:
            logo = Image(descargo["logo_path"], width=0.88 * inch, height=0.6 * inch)
            logo.hAlign = "CENTER"
            story.append(logo)
        except Exception:
            story.append(Paragraph("<b>FACCI</b>", title_style))
    else:
        story.append(Paragraph("<b>FACCI</b>", title_style))

    story.append(Spacer(1, 14))
    story.append(Paragraph("Descargo de Responsabilidad y Consentimiento<br/>Para el Tratamiento Médico a un Menor", title_style))
    story.append(Spacer(1, 14))
    story.append(Paragraph(descargo.get("intro_text") or descargo["paragraphs"][0], body_style))
    
    # Condiciones 1 a 5
    for index, text in enumerate(descargo["conditions"][:5], start=1):
        story.append(Paragraph(f"<b>{index})</b> {text}", body_style))

    story.append(PageBreak())

    # --- PÁGINA 2 ---
    # Logo en página 2
    if descargo["logo_path"]:
        try:
            logo = Image(descargo["logo_path"], width=0.88 * inch, height=0.6 * inch)
            logo.hAlign = "CENTER"
            story.append(logo)
        except Exception:
            pass

    story.append(Spacer(1, 14))

    # Condiciones 6 a 9
    for index, text in enumerate(descargo["conditions"][5:], start=6):
        story.append(Paragraph(f"<b>{index})</b> {text}", body_style))

    story.append(Spacer(1, 14))

    fecha = (
        f"Hecho y firmado de buena fe en dos (2) originales, en la ciudad de <b>{descargo['ciudad']}</b>, "
        f"a los <b>{descargo['dia']}</b> días del mes de <b>{descargo['mes']}</b> "
        f"del año <b>{descargo['anio']}</b>."
    )
    story.append(Paragraph(fecha, body_style))
    story.append(Spacer(1, 45))

    story.append(Paragraph("________________________________", center_style))
    story.append(Paragraph("<b>Firma de la Madre/Padre</b>", center_style))

    def footer(canvas, doc_obj):
        canvas.saveState()
        # Línea divisoria superior del pie de página
        canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
        canvas.setLineWidth(0.5)
        canvas.line(45, 60, doc_obj.pagesize[0] - 45, 60)

        # Nombre de la fundación
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#0f4c81"))
        canvas.drawCentredString(doc_obj.pagesize[0] / 2, 45, "FUNDACIÓN AMIGOS CONTRA EL CÁNCER INFANTIL")
        
        # Redes, web, RNC
        canvas.setFont("Helvetica", 7.2)
        canvas.setFillColor(colors.HexColor("#4b5563"))
        canvas.drawCentredString(doc_obj.pagesize[0] / 2, 33, "@facci_rd   •   www.facci.org.do   •   faccifundacion@facci.org.do   •   RNC: 430-00602-5")
        
        # Teléfono y dirección
        canvas.drawCentredString(doc_obj.pagesize[0] / 2, 21, "809-533-7596   •   Calle Antonio Maceo #6, sector Mata Hambre, La Feria, Santo Domingo, R.D.")
        
        # Número de página
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(colors.HexColor("#9ca3af"))
        canvas.drawCentredString(doc_obj.pagesize[0] / 2, 9, f"Página {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
