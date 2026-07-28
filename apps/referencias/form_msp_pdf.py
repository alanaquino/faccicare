import os
import datetime
from io import BytesIO
from html import escape
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer

NAVY_BLUE = colors.HexColor("#122a53")

def _display(value) -> str:
    if value is None:
        return ""
    return str(value).strip()

def _check_char(is_checked: bool) -> str:
    return "[X]" if is_checked else "[  ]"

def render_msp_form_pdf(referencia, data: dict) -> bytes:
    paciente = referencia.paciente
    
    # Resolver ruta del logo
    logo_path = os.path.join(settings.BASE_DIR, "static", "img", "logo_msp.jpeg")
    
    # Obtener cuestionario de cribado
    cribado = referencia.cuestionario
    if not cribado:
        # Fallback al último cribado del paciente si no está en la referencia
        cribado = paciente.cribados.order_by("-fecha_evaluacion").first()
        
    buffer = BytesIO()
    
    # 8.5in x 11in, márgenes estrechos para que quepa en 1 sola página
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.35 * inch,
        leftMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
        title="Formulario de Referencia y Contrarreferencia MSP",
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos de Párrafo personalizados
    normal_style = ParagraphStyle(
        "MSPNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=9.5,
        textColor=colors.black,
    )
    bold_style = ParagraphStyle(
        "MSPBold",
        parent=normal_style,
        fontName="Helvetica-Bold",
    )
    title_style = ParagraphStyle(
        "MSPTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=NAVY_BLUE,
        alignment=1, # Centrado
    )
    subtitle_style = ParagraphStyle(
        "MSPSubtitle",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=1, # Centrado
    )
    header_box_style = ParagraphStyle(
        "MSPHeaderBox",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9,
        textColor=colors.white,
    )
    header_box_italic_style = ParagraphStyle(
        "MSPHeaderBoxItalic",
        parent=header_box_style,
        fontName="Helvetica-BoldOblique",
    )
    
    def esc(value):
        # Escapa SOLO datos dinámicos. El marcado estático de ReportLab
        # (<u>, <b>, <br/>) debe pasar sin escapar para que se renderice.
        return escape(_display(value))

    def p(text, style=normal_style):
        # No escapa: el texto puede contener marcado intencional. Los datos
        # dinámicos se escapan en el sitio de llamada con esc().
        return Paragraph(_display(text) or " ", style)

    def p_white(text, style=header_box_style):
        return Paragraph(_display(text) or " ", style)

    story = []

    # 1. ENCABEZADO
    logo_element = None
    if os.path.exists(logo_path):
        try:
            logo_element = Image(logo_path, width=1.5 * inch, height=0.55 * inch)
        except Exception:
            logo_element = Paragraph("<b>SALUD PÚBLICA</b>", bold_style)
    else:
        logo_element = Paragraph("<b>SALUD PÚBLICA</b>", bold_style)
        
    title_paragraphs = [
        Paragraph("FORMULARIO PARA REFERENCIA Y CONTRARREFERENCIA", title_style),
        Paragraph("ANTE SOSPECHA DE CANCER INFANTIL", subtitle_style)
    ]
    
    header_table = Table(
        [[logo_element, title_paragraphs]],
        colWidths=[1.8 * inch, 6.0 * inch]
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.08 * inch))
    
    # 2. FILA GENERAL
    fecha_ref = referencia.fecha_referencia.strftime("%d/%m/%Y") if referencia.fecha_referencia else ""
    general_row = Table(
        [[
            p(f"Fecha: <u>  {esc(fecha_ref)}  </u>", bold_style),
            p(f"Establecimiento de salud que refiere: <u>  {esc(data.get('establecimiento_refiere', ''))}  </u>", bold_style)
        ]],
        colWidths=[2.5 * inch, 5.3 * inch]
    )
    general_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(general_row)
    story.append(Spacer(1, 0.04 * inch))
    
    # 3. SECCIÓN 1: NOMBRE DEL PACIENTE
    patient_header = Table(
        [[p_white("Nombre del Paciente"), p(f"<b>{esc(paciente.nombre_completo)}</b>", bold_style)]],
        colWidths=[1.8 * inch, 6.0 * inch]
    )
    patient_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), NAVY_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (1, 0), (1, 0), 1, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(patient_header)
    
    # 4. TABLA DE DETALLES DEL PACIENTE
    # Sexo
    if 'sexo_m' in data:
        sexo_m = _check_char(data.get('sexo_m'))
        sexo_f = _check_char(data.get('sexo_f'))
    else:
        sexo_m = _check_char(paciente.sexo == "M")
        sexo_f = _check_char(paciente.sexo == "F")
    
    # Nacionalidad
    if 'nacionalidad_dom' in data:
        is_dom = data.get('nacionalidad_dom')
        is_ext = data.get('nacionalidad_ext')
        especifique_nac = data.get('nacionalidad_especifique', '')
    else:
        tutor_nac = _display(getattr(paciente.padre_tutor, "nacionalidad", "")).lower()
        is_dom = not tutor_nac or "domin" in tutor_nac
        is_ext = not is_dom
        especifique_nac = "" if is_dom else getattr(paciente.padre_tutor, "nacionalidad", "")

    nacionalidad_dom = _check_char(is_dom)
    nacionalidad_ext = _check_char(is_ext)
    
    # ARS
    if 'ars_nombre' in data:
        seguro_label = data.get('ars_nombre', '')
        ars_cont = _check_char(data.get('ars_cont'))
        ars_subs = _check_char(data.get('ars_subs'))
        ars_otro = _check_char(data.get('ars_otro'))
    else:
        seguro = _display(paciente.seguro_medico).lower()
        is_cont = "contri" in seguro
        is_subs = "subsi" in seguro or ("senasa" in seguro and not is_cont)
        is_otro = bool(seguro and not is_cont and not is_subs)
        ars_cont = _check_char(is_cont)
        ars_subs = _check_char(is_subs)
        ars_otro = _check_char(is_otro)
        seguro_label = paciente.seguro_medico or "Ninguno"
        if paciente.numero_seguro:
            seguro_label += f" (No. {paciente.numero_seguro})"
        
    details_data = [
        [
            Paragraph("<b>Edad</b><br/>" + escape(paciente.edad), normal_style),
            Paragraph(f"<b>Sexo</b><br/>M {sexo_m}   F {sexo_f}", normal_style),
            Paragraph(f"<b>Nacionalidad</b><br/>Dom. {nacionalidad_dom}   Extranjero {nacionalidad_ext}<br/>Especifique: <u>  {esc(especifique_nac)}  </u>", normal_style),
            Paragraph(f"<b>ARS y Tipo:</b> <u>{escape(seguro_label)}</u><br/>Cont. {ars_cont}   Subs. {ars_subs}   Otro {ars_otro}", normal_style)
        ]
    ]
    
    details_table = Table(details_data, colWidths=[1.2 * inch, 1.5 * inch, 2.7 * inch, 2.4 * inch])
    details_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 0.06 * inch))
    
    # 5. BREVE HISTORIA
    brief_header = Table(
        [[p_white("Breve Historia por la que se refiere al paciente", header_box_italic_style)]],
        colWidths=[7.8 * inch]
    )
    brief_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(brief_header)
    
    brief_content = Table(
        [[Paragraph(escape(referencia.motivo_referencia).replace("\n", "<br/>"), normal_style)]],
        colWidths=[7.8 * inch]
    )
    brief_content.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("MINHEIGHT", (0, 0), (-1, -1), 70),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(brief_content)
    story.append(Spacer(1, 0.06 * inch))
    
    # 6. SIGNOS VITALES
    vital_header = Table(
        [[p_white("Signos Vitales", header_box_italic_style)]],
        colWidths=[7.8 * inch]
    )
    vital_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(vital_header)
    
    vital_data = [
        [
            p(f"TA: <u>  {esc(data.get('ta', ''))}  </u>", bold_style),
            p(f"FC: <u>  {esc(data.get('fc', ''))}  </u> lpm", bold_style),
            p(f"FR: <u>  {esc(data.get('fr', ''))}  </u> rpm", bold_style),
            p(f"TEMPERATURA: <u>  {esc(data.get('temperatura', ''))}  </u> °C", bold_style),
        ]
    ]
    vital_table = Table(vital_data, colWidths=[1.95 * inch, 1.95 * inch, 1.95 * inch, 1.95 * inch])
    vital_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(vital_table)
    story.append(Spacer(1, 0.06 * inch))
    
    # 7. SIGNOS DE ALERTA DE CÁNCER INFANTIL
    sintomas_header = Table(
        [[p_white("Signos de Alerta de Cáncer Infantil", header_box_italic_style)]],
        colWidths=[7.8 * inch]
    )
    sintomas_header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sintomas_header)
    
    # Determinar si los síntomas están activos
    if 'sintoma_fiebre' in data:
        fiebre = _check_char(data.get('sintoma_fiebre'))
        masa = _check_char(data.get('sintoma_masa'))
        moretones = _check_char(data.get('sintoma_moretones'))
        peso = _check_char(data.get('sintoma_peso'))
        ojo = _check_char(data.get('sintoma_ojo'))
        vomitos = _check_char(data.get('sintoma_vomitos'))
        huesos = _check_char(data.get('sintoma_huesos'))
        sudoracion = _check_char(data.get('sintoma_sudoracion'))
        ganglios = _check_char(data.get('sintoma_ganglios'))
        fatiga = _check_char(data.get('sintoma_fatiga'))
        otros_label = data.get('sintoma_otro', '')
    else:
        fiebre = _check_char(bool(getattr(cribado, "fiebre_persistente", False)))
        masa = _check_char(bool(getattr(cribado, "masa_abdominal", False)))
        moretones = _check_char(bool(getattr(cribado, "moretones", False) or getattr(cribado, "sangrado", False)))
        peso = _check_char(bool(getattr(cribado, "perdida_peso", False)))
        ojo = _check_char(bool(getattr(cribado, "leucocoria", False)))
        vomitos = _check_char(bool(getattr(cribado, "vomitos", False)))
        huesos = _check_char(bool(getattr(cribado, "dolor_huesos", False)))
        
        observaciones_lower = _display(getattr(cribado, "observaciones", "")).lower() + " " + _display(referencia.observaciones).lower()
        sudoracion = _check_char("sudor" in observaciones_lower)
        ganglios = _check_char(bool(getattr(cribado, "ganglios", False)))
        fatiga = _check_char(bool(getattr(cribado, "fatiga", False)))
        
        otros_sintomas = []
        if getattr(cribado, "palidez", False):
            otros_sintomas.append("Palidez")
        if getattr(cribado, "infecciones_recurrentes", False):
            otros_sintomas.append("Infecciones recurrentes")
        if getattr(cribado, "dolor_cabeza", False):
            otros_sintomas.append("Dolor de cabeza persistente")
        if getattr(cribado, "observaciones", ""):
            otros_sintomas.append(getattr(cribado, "observaciones"))
            
        otros_label = ", ".join(otros_sintomas) if otros_sintomas else ""
    
    sintomas_data = [
        [
            p(f"Fiebre {fiebre}"),
            p(f"Masa en Abdomen {masa}"),
            p(f"Moretones en piel o sangrado {moretones}"),
        ],
        [
            p(f"Pérdida de Peso {peso}"),
            p(f"Mancha blanca o masa en el ojo {ojo}"),
            p(f"Vómitos mañaneros {vomitos}"),
            p(f"Dolor de Huesos {huesos}"),
        ],
        [
            p(f"Sudoración Abundante {sudoracion}"),
            p(f"Crecimiento de ganglios {ganglios}"),
            p(f"Fatiga, pérdida apetito {fatiga}"),
            p(""),
        ],
        [
            Paragraph(f"Otro: <u>  {escape(otros_label)}  </u>", normal_style), "", "", ""
        ]
    ]
    
    # Reconfigurar colWidths
    sintomas_table = Table(
        sintomas_data,
        colWidths=[2.3 * inch, 2.5 * inch, 1.5 * inch, 1.5 * inch]
    )
    sintomas_table.setStyle(TableStyle([
        ("SPAN", (0, 3), (3, 3)), # Combinar fila de "Otro"
        ("SPAN", (2, 2), (3, 2)), # Combinar vacío en fila 3
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sintomas_table)
    story.append(Spacer(1, 0.06 * inch))
    
    # 8. DESTINO Y MÉDICO QUE REFIERE
    dest_medico_data = [
        [
            p_white("Centro al cual se refiere", header_box_style),
            p(esc(referencia.hospital_destino.nombre if referencia.hospital_destino else ''), bold_style),
            Paragraph("<b>Sello del Centro que Refiere</b>", ParagraphStyle("StampLabel", parent=normal_style, fontName="Helvetica-Bold", fontSize=7, alignment=1))
        ],
        [
            p_white("Nombre del médico que refiere", header_box_style),
            p(esc(referencia.medico_referente.get_full_name()), bold_style),
            "" # Espacio vacío para el sello
        ]
    ]
    dest_medico_table = Table(
        dest_medico_data,
        colWidths=[2.2 * inch, 3.2 * inch, 2.4 * inch]
    )
    dest_medico_table.setStyle(TableStyle([
        ("GRID", (0, 0), (1, 1), 1, colors.black), # Cuadrícula para datos
        ("BOX", (2, 0), (2, 1), 1, colors.black), # Recuadro para sello
        ("BACKGROUND", (0, 0), (0, 0), NAVY_BLUE),
        ("BACKGROUND", (0, 1), (0, 1), NAVY_BLUE),
        ("SPAN", (2, 0), (2, 0)), # Título sello
        ("SPAN", (2, 1), (2, 1)), # Área de sello
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(dest_medico_table)
    story.append(Spacer(1, 0.08 * inch))
    
    # Separador horizontal
    story.append(Table([[""]], colWidths=[7.8 * inch], rowHeights=[2], style=[("LINEBELOW", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(Spacer(1, 0.08 * inch))
    
    # 9. SECCIÓN: CONTRARREFERENCIA
    story.append(Paragraph("<b>CONTRA-REFERENCIA</b>", subtitle_style))
    story.append(Spacer(1, 0.04 * inch))
    
    # Fecha Contra
    contra_fecha_val = data.get("contra_fecha", "")
    if contra_fecha_val:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                contra_fecha_val = datetime.datetime.strptime(contra_fecha_val, fmt).strftime("%d/%m/%Y")
                break
            except ValueError:
                pass
            
    contra_date_table = Table(
        [[p(f"Fecha: <u>  {esc(contra_fecha_val)}  </u>", bold_style)]],
        colWidths=[7.8 * inch]
    )
    contra_date_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(contra_date_table)
    
    # Secciones de texto de Contra-referencia
    sections = [
        ("Historia de Atención", data.get("contra_historia", "")),
        ("Medicación indicada", data.get("contra_medicamentos", "")),
        ("Estudios y/o imágenes realizadas", data.get("contra_estudios", ""))
    ]
    
    for title, content in sections:
        sec_header = Table([[p_white(title)]], colWidths=[7.8 * inch])
        sec_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY_BLUE),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(sec_header)

        # Caja con altura mínima para poder rellenarla a mano cuando se imprime
        # en blanco. (ReportLab NO tiene comando "MINHEIGHT"; se usa rowHeights.)
        # Si el contenido digital es más alto que el mínimo, la caja crece para
        # no recortarlo.
        sec_par = Paragraph(escape(content).replace("\n", "<br/>") or " ", normal_style)
        _, sec_nat_h = sec_par.wrap(7.8 * inch - 8, 10 * inch)  # -8 = padding L+R
        sec_row_h = max(0.55 * inch, sec_nat_h + 6)
        sec_content = Table(
            [[sec_par]],
            colWidths=[7.8 * inch],
            rowHeights=[sec_row_h],
        )
        sec_content.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(sec_content)
        story.append(Spacer(1, 0.04 * inch))
        
    story.append(Spacer(1, 0.02 * inch))
    
    # 10. MÉDICO QUE CONTRA-REFIERE Y SELLO
    contra_med_data = [
        [
            p_white("Nombre del médico que contra-refiere", header_box_style),
            p(esc(data.get("contra_medico", "")), bold_style),
            Paragraph("<b>Sello del Centro que contra-refiere</b>", ParagraphStyle("StampLabel2", parent=normal_style, fontName="Helvetica-Bold", fontSize=7, alignment=1))
        ],
        [
            "", "", "" # Fila para espacio del sello
        ]
    ]
    contra_med_table = Table(
        contra_med_data,
        colWidths=[2.5 * inch, 2.7 * inch, 2.6 * inch],
        rowHeights=[0.3 * inch, 0.55 * inch],  # 2da fila: espacio para el sello/firma
    )
    contra_med_table.setStyle(TableStyle([
        ("GRID", (0, 0), (1, 0), 1, colors.black), # Cuadrícula para datos
        ("BOX", (2, 0), (2, 1), 1, colors.black), # Recuadro para sello
        ("BACKGROUND", (0, 0), (0, 0), NAVY_BLUE),
        ("SPAN", (0, 0), (0, 1)), # Expandir verticalmente título médico
        ("SPAN", (1, 0), (1, 1)), # Expandir verticalmente valor médico
        ("SPAN", (2, 0), (2, 0)), # Título sello
        ("SPAN", (2, 1), (2, 1)), # Área de sello
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (2, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(contra_med_table)

    doc.build(story)
    return buffer.getvalue()
