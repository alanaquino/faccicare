import secrets
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.auth_app.models import CustomUser
from apps.core.audit import registrar_actividad
from apps.core.constants import PROVINCIAS_RD
from apps.core.models import CentroSalud
from apps.padres.models import PadreTutor
from apps.seguimiento.models import SeguimientoPaciente

from .ficha import build_ficha_context, ficha_pdf_filename, render_ficha_pdf
from .forms import NotaClinicaForm, RegistroPacienteForm
from .models import Paciente

from apps.referencias.models import ReferenciaMedica


MESES = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}


def _fecha_corta(fecha):
    if not fecha:
        return "Reciente"
    return f"{fecha.day} {MESES.get(fecha.month, '')}, {fecha.year}"


def _autor_nombre(usuario):
    if not usuario:
        return "Sistema"
    return usuario.get_full_name() or usuario.username


def _generar_codigo_paciente():
    year = timezone.localdate().year
    prefix = f"FACCI-{year}"
    ultimo = (
        Paciente.objects.filter(codigo_paciente__startswith=prefix)
        .order_by("-codigo_paciente")
        .values_list("codigo_paciente", flat=True)
        .first()
    )
    consecutivo = 1
    if ultimo:
        try:
            consecutivo = int(ultimo.replace(prefix, "")) + 1
        except ValueError:
            consecutivo = Paciente.objects.filter(codigo_paciente__startswith=prefix).count() + 1

    codigo = f"{prefix}{consecutivo:04d}"
    while Paciente.objects.filter(codigo_paciente=codigo).exists():
        consecutivo += 1
        codigo = f"{prefix}{consecutivo:04d}"
    return codigo


def _separar_nombre_completo(nombre_completo):
    partes = nombre_completo.strip().split()
    if not partes:
        return "", ""
    if len(partes) == 1:
        return partes[0], ""
    return " ".join(partes[:-1]), partes[-1]


def _puede_resetear_pin(user, paciente):
    return (
        user.rol == CustomUser.Rol.ADMIN
        or paciente.medico_asignado_id == user.id
        or paciente.creado_por_id == user.id
    )


def _puede_editar_paciente(user, paciente):
    """Autoriza solo al personal clínico responsable y al Administrador."""
    if user.rol == CustomUser.Rol.ADMIN:
        return True
    if user.rol in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
        return paciente.medico_asignado == user or paciente.creado_por == user
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return paciente.referencias.filter(especialista_destino=user).exists()
    return False


def _generar_username_tutor(email, cedula, nombre_completo):
    base = (email.split("@")[0] if email else cedula or nombre_completo).lower()
    base = "".join(ch for ch in base if ch.isalnum() or ch in "._-").strip("._-") or "tutor"
    username = base
    contador = 1
    while CustomUser.objects.filter(username=username).exists():
        contador += 1
        username = f"{base}{contador}"
    return username


def _obtener_o_crear_tutor(data):
    cedula = data.get("tutor_cedula")
    tipo_documento = data.get("tutor_tipo_documento", CustomUser.TipoDocumento.CEDULA)
    email = data.get("tutor_email") or ""
    nombre_completo = data["tutor_nombre"]
    first_name, last_name = _separar_nombre_completo(nombre_completo)

    usuario = None
    if cedula:
        usuario = CustomUser.objects.filter(cedula=cedula).first()
    if usuario is None and email:
        usuario = CustomUser.objects.filter(email__iexact=email).first()

    tutor_nuevo_pin = None
    if usuario is None:
        pin = "".join(secrets.choice("0123456789") for _ in range(6))
        usuario = CustomUser(
            username=_generar_username_tutor(email, cedula, nombre_completo),
            first_name=first_name,
            last_name=last_name,
            email=email,
            telefono=data["tutor_telefono"],
            cedula=cedula,
            tipo_documento=tipo_documento,
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        usuario.set_password(pin)
        usuario.save()
        tutor_nuevo_pin = pin
    else:
        if (
            usuario.rol != CustomUser.Rol.PADRE_TUTOR
            or usuario.is_staff
            or usuario.is_superuser
        ):
            raise ValueError(
                "No se puede vincular una cuenta del personal como padre o tutor."
            )
        usuario.first_name = first_name or usuario.first_name
        usuario.last_name = last_name or usuario.last_name
        usuario.email = email or usuario.email
        usuario.telefono = data["tutor_telefono"] or usuario.telefono
        if cedula:
            usuario.cedula = cedula
        usuario.tipo_documento = tipo_documento
        usuario.save()

    tutor, created = PadreTutor.objects.get_or_create(
        usuario=usuario,
        defaults={
            "parentesco": data["parentesco"],
            "direccion": data["tutor_direccion"],
            "provincia": data["provincia"],
            "municipio": data.get("municipio") or "",
        },
    )
    if not created:
        tutor.parentesco = data["parentesco"]
        tutor.direccion = data["tutor_direccion"]
        tutor.provincia = data["provincia"]
        tutor.municipio = data.get("municipio") or tutor.municipio
        tutor.save()
    return tutor, tutor_nuevo_pin


def _build_timeline(cribados, referencias, seguimientos, documentos, notas,
                    reportes_sintomas=None, indicaciones=None, solicitudes=None):
    from apps.cribado.models import CuestionarioCribado

    timeline = []
    score_maximo = len(CuestionarioCribado.CAMPOS_SINTOMAS)

    for nota in notas:
        badges = [{"label": nota.get_tipo_display(), "color": nota.color}]
        if nota.es_importante:
            badges.append({"label": "Importante", "color": "error"})
        timeline.append({
            "fecha_dt": nota.created_at,
            "fecha": nota.fecha,
            "tipo": "Nota clínica",
            "titulo": nota.get_tipo_display(),
            "descripcion": nota.texto,
            "autor": nota.autor_nombre,
            "icono": "note_alt",
            "color": nota.color,
            "badges": badges,
            "campos": [],
        })

    for cribado in cribados:
        color = "error" if cribado.nivel_riesgo == "ALTO" else "secondary" if cribado.nivel_riesgo == "MEDIO" else "primary"
        badges = [{"label": cribado.get_nivel_riesgo_display(), "color": color}]
        if cribado.requiere_referencia:
            badges.append({"label": "Requiere referencia", "color": "secondary"})
        campos = [
            {"label": "Puntaje", "valor": f"{cribado.puntaje_total}/{score_maximo}"},
            {"label": "Resultado", "valor": cribado.get_resultado_display() if hasattr(cribado, 'get_resultado_display') else "—"},
        ]
        timeline.append({
            "fecha_dt": cribado.fecha_evaluacion,
            "fecha": _fecha_corta(cribado.fecha_evaluacion),
            "tipo": "Cribado FACCI",
            "titulo": f"Cribado — {cribado.get_nivel_riesgo_display()}",
            "descripcion": cribado.observaciones or f"Puntaje total: {cribado.puntaje_total}/{score_maximo}",
            "autor": _autor_nombre(cribado.medico),
            "icono": "fact_check",
            "color": color,
            "detalle_url": "cribado",
            "id": cribado.id,
            "badges": badges,
            "campos": campos,
        })

    for referencia in referencias:
        color = "error" if referencia.prioridad in ["URGENTE", "ALTA"] else "secondary"
        badges = [
            {"label": referencia.get_prioridad_display() if hasattr(referencia, 'get_prioridad_display') else referencia.prioridad, "color": color},
            {"label": referencia.get_estado_display() if hasattr(referencia, 'get_estado_display') else referencia.estado, "color": "tertiary"},
        ]
        especialista = getattr(referencia, 'especialista_destino', None)
        campos = [
            {"label": "Hospital destino", "valor": referencia.hospital_destino.nombre if referencia.hospital_destino else "—"},
            {"label": "Especialista", "valor": _autor_nombre(especialista) if especialista else "—"},
            {"label": "Fecha cita", "valor": _fecha_corta(referencia.fecha_cita) if getattr(referencia, 'fecha_cita', None) else "Por confirmar"},
            {"label": "Estado", "valor": referencia.get_estado_display() if hasattr(referencia, 'get_estado_display') else referencia.estado},
        ]
        timeline.append({
            "fecha_dt": referencia.fecha_referencia,
            "fecha": referencia.fecha,
            "tipo": "Referencia médica",
            "titulo": f"Referencia a {referencia.hospital_destino.nombre if referencia.hospital_destino else 'destino sin asignar'}",
            "descripcion": referencia.motivo_referencia,
            "autor": referencia.medico_origen,
            "icono": "send",
            "color": color,
            "detalle_url": "referencia",
            "id": referencia.id,
            "badges": badges,
            "campos": campos,
        })

    for seguimiento in seguimientos:
        es_cita = (
            seguimiento.proxima_fecha_seguimiento is not None
            and not seguimiento.sintomas_actuales
            and not seguimiento.tratamiento_actual
            and not seguimiento.medicamentos
            and seguimiento.peso_kg is None
            and seguimiento.talla_cm is None
            and seguimiento.temperatura_c is None
            and not seguimiento.tension_arterial
        )
        if es_cita:
            medico_cita_nombre = _autor_nombre(seguimiento.medico_seguimiento) if seguimiento.medico_seguimiento else _autor_nombre(seguimiento.medico)
            lugar = seguimiento.lugar_seguimiento.nombre if seguimiento.lugar_seguimiento else "Por confirmar"
            badges = [{"label": "Seguimiento programado", "color": "secondary"}]
            campos = [
                {"label": "Fecha del seguimiento", "valor": seguimiento.proxima_fecha_seguimiento.strftime("%d/%m/%Y %H:%M")},
                {"label": "Médico", "valor": medico_cita_nombre},
                {"label": "Centro / Lugar", "valor": lugar},
                {"label": "Motivo", "valor": seguimiento.observaciones or "—"},
            ]
            timeline.append({
                "id": str(seguimiento.id),
                "fecha_dt": seguimiento.fecha_seguimiento,
                "fecha": _fecha_corta(seguimiento.fecha_seguimiento),
                "tipo": "Seguimiento agendado",
                "titulo": f"Seguimiento — {seguimiento.proxima_fecha_seguimiento.strftime('%d/%m/%Y a las %H:%M')}",
                "descripcion": f"{medico_cita_nombre} · {lugar}" + (f" — {seguimiento.observaciones}" if seguimiento.observaciones else ""),
                "autor": _autor_nombre(seguimiento.medico),
                "icono": "calendar_add_on",
                "color": "secondary",
                "badges": badges,
                "campos": campos,
            })
        else:
            color = "error" if seguimiento.requiere_hospitalizacion else "tertiary"
            badges = []
            if seguimiento.requiere_hospitalizacion:
                badges.append({"label": "Requiere hospitalización", "color": "error"})
            if seguimiento.proxima_fecha_seguimiento:
                badges.append({"label": f"Próximo seguimiento: {seguimiento.proxima_fecha_seguimiento.strftime('%d/%m/%Y')}", "color": "secondary"})
            for alerta in seguimiento.alertas_valores_atipicos:
                badges.append({"label": alerta, "color": "error"})
            campos = []
            if seguimiento.sintomas_actuales:
                campos.append({"label": "Síntomas", "valor": seguimiento.sintomas_actuales})
            if seguimiento.tratamiento_actual:
                campos.append({"label": "Tratamiento", "valor": seguimiento.tratamiento_actual})
            if seguimiento.medicamentos:
                campos.append({"label": "Medicamentos", "valor": seguimiento.medicamentos})
            if seguimiento.peso_kg is not None:
                campos.append({"label": "Peso", "valor": f"{seguimiento.peso_kg} kg"})
            if seguimiento.talla_cm is not None:
                campos.append({"label": "Talla", "valor": f"{seguimiento.talla_cm} cm"})
            if seguimiento.imc is not None:
                campos.append({"label": "IMC", "valor": str(seguimiento.imc)})
            if seguimiento.temperatura_c is not None:
                campos.append({"label": "Temperatura", "valor": f"{seguimiento.temperatura_c} °C"})
            if seguimiento.tension_arterial:
                campos.append({"label": "Tensión arterial", "valor": f"{seguimiento.tension_arterial} mmHg"})
            if seguimiento.observaciones:
                campos.append({"label": "Observaciones", "valor": seguimiento.observaciones})
            timeline.append({
                "id": str(seguimiento.id),
                "fecha_dt": seguimiento.fecha_seguimiento,
                "fecha": _fecha_corta(seguimiento.fecha_seguimiento),
                "tipo": "Seguimiento clínico",
                "titulo": seguimiento.estado_clinico,
                "descripcion": seguimiento.observaciones or seguimiento.sintomas_actuales or seguimiento.tratamiento_actual,
                "autor": _autor_nombre(seguimiento.medico),
                "icono": "monitor_heart",
                "color": color,
                "badges": badges,
                "campos": campos,
            })

    for documento in documentos:
        fecha_dt = documento.created_at
        if documento.fecha_documento:
            fecha_dt = datetime.datetime.combine(
                documento.fecha_documento,
                datetime.datetime.min.time(),
                tzinfo=timezone.get_current_timezone(),
            )
        badges = [
            {"label": documento.get_tipo_documento_display() if hasattr(documento, 'get_tipo_documento_display') else documento.tipo, "color": documento.color},
            {"label": documento.get_estado_display() if hasattr(documento, 'get_estado_display') else "—", "color": "tertiary" if documento.estado == "REVISADO" else "secondary"},
        ]
        campos = [
            {"label": "Tipo", "valor": documento.get_tipo_documento_display() if hasattr(documento, 'get_tipo_documento_display') else documento.tipo},
            {"label": "Estado", "valor": documento.get_estado_display() if hasattr(documento, 'get_estado_display') else "—"},
            {"label": "Tamaño", "valor": documento.tamano},
        ]
        timeline.append({
            "fecha_dt": fecha_dt,
            "fecha": documento.fecha,
            "tipo": "Documento médico",
            "titulo": documento.nombre,
            "descripcion": documento.descripcion or documento.tipo,
            "autor": _autor_nombre(documento.subido_por),
            "icono": documento.icono,
            "color": documento.color,
            "badges": badges,
            "campos": campos,
        })

    for reporte in (reportes_sintomas or []):
        tutor_nombre = reporte.tutor.usuario.get_full_name() if reporte.tutor else "Padre/Tutor"
        badges = [{"label": f"Gravedad: {reporte.gravedad}", "color": reporte.color_gravedad}]
        campos = [
            {"label": "Síntomas", "valor": reporte.sintomas_str},
            {"label": "Inicio de síntomas", "valor": reporte.fecha_inicio.strftime("%d/%m/%Y")},
            {"label": "Descripción", "valor": reporte.descripcion or "Sin detalle adicional"},
        ]
        timeline.append({
            "fecha_dt": reporte.created_at,
            "fecha": _fecha_corta(reporte.created_at),
            "tipo": "Reporte de síntomas",
            "titulo": f"Síntomas reportados por el tutor — {reporte.gravedad}",
            "descripcion": reporte.sintomas_str + (f". {reporte.descripcion}" if reporte.descripcion else ""),
            "autor": tutor_nombre,
            "icono": "sick",
            "color": reporte.color_gravedad,
            "badges": badges,
            "campos": campos,
        })

    for indicacion in (indicaciones or []):
        color = "error" if indicacion.prioridad == "ALTA" else "primary" if indicacion.prioridad == "MEDIA" else "tertiary"
        badges = [
            {"label": indicacion.get_tipo_indicacion_display(), "color": "primary"},
            {"label": f"Prioridad {indicacion.get_prioridad_display()}", "color": color},
            {"label": "Activa" if indicacion.activa else "Inactiva", "color": "tertiary" if indicacion.activa else "secondary"},
        ]
        campos = [
            {"label": "Tipo", "valor": indicacion.get_tipo_indicacion_display()},
            {"label": "Prioridad", "valor": indicacion.get_prioridad_display()},
            {"label": "Estado", "valor": "Activa" if indicacion.activa else "Inactiva"},
        ]
        timeline.append({
            "fecha_dt": indicacion.created_at,
            "fecha": _fecha_corta(indicacion.created_at),
            "tipo": "Indicación médica",
            "titulo": indicacion.titulo,
            "descripcion": indicacion.descripcion,
            "autor": _autor_nombre(indicacion.medico),
            "icono": indicacion.icono,
            "color": color,
            "badges": badges,
            "campos": campos,
        })

    for solicitud in (solicitudes or []):
        color_estado = {"PENDIENTE": "secondary", "SUBIDO": "primary", "REVISADO": "tertiary", "CORRECCION": "error"}.get(solicitud.estado, "secondary")
        badges = [{"label": solicitud.get_estado_display(), "color": color_estado}]
        campos = [
            {"label": "Estudio solicitado", "valor": solicitud.titulo},
            {"label": "Estado", "valor": solicitud.get_estado_display()},
            {"label": "Descripción", "valor": solicitud.descripcion or "—"},
        ]
        timeline.append({
            "fecha_dt": solicitud.created_at,
            "fecha": _fecha_corta(solicitud.created_at),
            "tipo": "Estudio médico",
            "titulo": f"Estudio solicitado: {solicitud.titulo}",
            "descripcion": solicitud.descripcion or solicitud.titulo,
            "autor": _autor_nombre(solicitud.medico_solicitante),
            "icono": "biotech",
            "color": color_estado,
            "badges": badges,
            "campos": campos,
        })

    timeline.sort(key=lambda item: item["fecha_dt"] or timezone.now(), reverse=True)
    return timeline


@login_required
def lista_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ENFERMERA]:
        pacientes = Paciente.objects.filter(
            Q(medico_asignado=request.user) | Q(creado_por=request.user)
        ).select_related("medico_asignado", "padre_tutor__usuario")
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        pacientes = Paciente.objects.filter(
            referencias__especialista_destino=request.user
        ).distinct().select_related("medico_asignado", "padre_tutor__usuario")
    else:
        pacientes = Paciente.objects.select_related("medico_asignado", "padre_tutor__usuario").all()

    search_query = request.GET.get("q", "").strip()
    estado_filtro = request.GET.get("estado", "").strip()

    if search_query:
        pacientes = pacientes.filter(
            Q(nombres__icontains=search_query) |
            Q(apellidos__icontains=search_query) |
            Q(codigo_paciente__icontains=search_query) |
            Q(provincia__icontains=search_query) |
            Q(municipio__icontains=search_query) |
            Q(padre_tutor__usuario__first_name__icontains=search_query) |
            Q(padre_tutor__usuario__last_name__icontains=search_query) |
            Q(padre_tutor__usuario__email__icontains=search_query) |
            Q(medico_asignado__first_name__icontains=search_query) |
            Q(medico_asignado__last_name__icontains=search_query)
        )
    if estado_filtro in Paciente.EstadoPaciente.values:
        pacientes = pacientes.filter(estado_actual=estado_filtro)

    total = pacientes.count()
    paginator = Paginator(pacientes, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "titulo_pagina": "Pacientes",
        "pacientes": page_obj,
        "page_obj": page_obj,
        "total": total,
        "filtros": ["Todos", "En seguimiento", "Referido", "En tratamiento", "Alta"],
        "filtro_search": search_query,
        "filtro_estado": estado_filtro,
        "estados_paciente": Paciente.EstadoPaciente.choices,
    }
    return render(request, "pacientes/lista.html", context)


@login_required
def registro_view(request):
    if request.user.rol in [CustomUser.Rol.ONCOLOGO, CustomUser.Rol.PADRE_TUTOR]:
        messages.error(request, "Su rol no tiene autorización para registrar pacientes.")
        return redirect("pacientes:lista")

    form = RegistroPacienteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            tutor, nuevo_pin = _obtener_o_crear_tutor(form.cleaned_data)
            paciente = Paciente.objects.create(
                codigo_paciente=_generar_codigo_paciente(),
                nombres=form.cleaned_data["nombres"],
                apellidos=form.cleaned_data["apellidos"],
                fecha_nacimiento=form.cleaned_data["fecha_nacimiento"],
                sexo=form.cleaned_data["sexo"],
                tipo_sangre=form.cleaned_data.get("tipo_sangre") or "",
                peso=form.cleaned_data.get("peso"),
                altura=form.cleaned_data.get("altura"),
                direccion=form.cleaned_data.get("direccion") or form.cleaned_data["tutor_direccion"],
                provincia=form.cleaned_data["provincia"],
                municipio=form.cleaned_data.get("municipio") or "",
                escuela=form.cleaned_data.get("escuela") or "",
                seguro_medico=form.cleaned_data.get("seguro_medico") or "",
                numero_seguro=form.cleaned_data.get("numero_seguro") or "",
                alergias=form.cleaned_data.get("alergias") or "",
                antecedentes_medicos=form.cleaned_data.get("antecedentes_medicos") or "",
                padre_tutor=tutor,
                medico_asignado=form.cleaned_data.get("medico_asignado"),
                creado_por=request.user,
            )
        if nuevo_pin:
            request.session["pin_creado"] = {
                "pin": nuevo_pin,
                "tutor": tutor.usuario.get_full_name(),
                "paciente_id": str(paciente.id),
            }
        messages.success(request, f"Paciente {paciente.nombre_completo} registrado con codigo {paciente.codigo_paciente}.")
        return redirect("pacientes:expediente", pk=paciente.pk)

    context = {
        "titulo_pagina": "Nuevo Paciente",
        "provincias": PROVINCIAS_RD,
        "form": form,
    }
    return render(request, "pacientes/registro.html", context)


@login_required
@require_GET
def verificar_tutor_cedula(request):
    if request.user.rol in [CustomUser.Rol.ONCOLOGO, CustomUser.Rol.PADRE_TUTOR]:
        return JsonResponse({"error": "No autorizado"}, status=403)

    cleaned_ced = request.GET.get("cedula", "").replace(" ", "").replace("-", "")
    if not (len(cleaned_ced) == 11 and cleaned_ced.isdigit()):
        return JsonResponse({"match": False})
    cedula = f"{cleaned_ced[:3]}-{cleaned_ced[3:10]}-{cleaned_ced[10]}"

    usuario = CustomUser.objects.filter(cedula=cedula).first()
    if usuario is None:
        registrar_actividad(
            usuario=request.user,
            accion="Consultar cédula de tutor",
            modelo="PadreTutor",
            objeto_id=cedula,
            objeto_repr=cedula,
            descripcion=f"Verificación en vivo de cédula {cedula} al registrar paciente: sin coincidencia.",
        )
        return JsonResponse({"match": False})

    if usuario.rol != CustomUser.Rol.PADRE_TUTOR or usuario.is_staff or usuario.is_superuser:
        registrar_actividad(
            usuario=request.user,
            accion="Consultar cédula de tutor",
            modelo="PadreTutor",
            objeto_id=cedula,
            objeto_repr=cedula,
            descripcion=f"Verificación en vivo de cédula {cedula} al registrar paciente: pertenece a cuenta de personal.",
        )
        return JsonResponse({
            "match": True,
            "valido": False,
            "mensaje": "Esta cédula pertenece a una cuenta de personal y no puede usarse como tutor.",
        })

    perfil = getattr(usuario, "perfil_padre", None)
    pacientes_asignados = Paciente.objects.filter(padre_tutor=perfil).count() if perfil else 0
    registrar_actividad(
        usuario=request.user,
        accion="Consultar cédula de tutor",
        modelo="PadreTutor",
        objeto_id=cedula,
        objeto_repr=usuario.get_full_name(),
        descripcion=(
            f"Verificación en vivo de cédula {cedula} al registrar paciente: "
            f"tutor existente ({pacientes_asignados} paciente(s) asignado(s))."
        ),
    )
    return JsonResponse({
        "match": True,
        "valido": True,
        "nombre": usuario.get_full_name(),
        "telefono": usuario.telefono,
        "email": usuario.email,
        "direccion": perfil.direccion if perfil else "",
        "parentesco": perfil.parentesco if perfil else "",
        "pacientes_asignados": pacientes_asignados,
    })


def _paciente_ficha_queryset():
    return Paciente.objects.select_related("padre_tutor__usuario", "medico_asignado")


@login_required
def ficha_paciente(request, pk):
    paciente = get_object_or_404(_paciente_ficha_queryset(), pk=pk)
    ficha = build_ficha_context(paciente)
    return render(
        request,
        "pacientes/ficha_paciente.html",
        {
            "titulo_pagina": f"Ficha - {paciente.nombre_completo}",
            "paciente": paciente,
            "ficha": ficha,
            "auto_print": request.GET.get("print") == "1",
        },
    )


@login_required
def ficha_paciente_pdf(request, pk):
    paciente = get_object_or_404(_paciente_ficha_queryset(), pk=pk)
    ficha = build_ficha_context(paciente)
    response = HttpResponse(render_ficha_pdf(ficha), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{ficha_pdf_filename(paciente)}"'
    return response


@login_required
def editar_view(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)

    if not _puede_editar_paciente(request.user, paciente):
        if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
            return redirect('padres:estado')
        messages.error(request, 'No tiene permiso para editar este paciente.')
        return redirect('pacientes:lista')

    if request.method == "POST":
        nombres = request.POST.get("nombres", "").strip()
        apellidos = request.POST.get("apellidos", "").strip()
        fecha_nacimiento = request.POST.get("fecha_nacimiento", "").strip()
        sexo = request.POST.get("sexo", "").strip()
        provincia = request.POST.get("provincia", "").strip()
        tipo_sangre = request.POST.get("tipo_sangre", "").strip()
        alergias = request.POST.get("alergias", "").strip()
        direccion = request.POST.get("direccion", "").strip()
        antecedentes_medicos = request.POST.get("antecedentes_medicos", "").strip()

        tutor_nombre = request.POST.get("tutor_nombre", "").strip()
        tutor_tipo_documento = request.POST.get("tutor_tipo_documento", "CEDULA").strip()
        tutor_cedula = request.POST.get("tutor_cedula", "").strip() or None
        tutor_telefono = request.POST.get("tutor_telefono", "").strip()
        tutor_email = request.POST.get("tutor_email", "").strip()
        tutor_direccion = request.POST.get("tutor_direccion", "").strip()
        
        medico_asignado_id = request.POST.get("medico_asignado", "").strip()
        estado_actual = request.POST.get("estado_actual", "").strip()
        
        tutor = paciente.padre_tutor
        tutor_usuario = tutor.usuario

        error_cedula = False
        if tutor_tipo_documento == "CEDULA" and tutor_cedula:
            cleaned_ced = tutor_cedula.replace(" ", "").replace("-", "")
            if not (len(cleaned_ced) == 11 and cleaned_ced.isdigit()):
                messages.error(request, "La cédula dominicana debe tener 11 dígitos.")
                error_cedula = True
            else:
                tutor_cedula = f"{cleaned_ced[:3]}-{cleaned_ced[3:10]}-{cleaned_ced[10]}"
                if CustomUser.objects.filter(cedula=tutor_cedula).exclude(pk=tutor_usuario.pk).exists():
                    messages.error(request, f"La cédula {tutor_cedula} ya está registrada.")
                    error_cedula = True
        elif tutor_cedula:
            if CustomUser.objects.filter(cedula=tutor_cedula).exclude(pk=tutor_usuario.pk).exists():
                messages.error(request, f"El documento {tutor_cedula} ya está registrado.")
                error_cedula = True

        if error_cedula:
            pass
        elif not nombres or not apellidos or not fecha_nacimiento or not sexo or not provincia or not tutor_nombre or not tutor_telefono or not tutor_direccion:
            messages.error(request, "Los campos marcados con asterisco (*) son obligatorios.")
        else:
            with transaction.atomic():
                # 1. Actualizar tutor/usuario
                first_name, last_name = _separar_nombre_completo(tutor_nombre)
                tutor_usuario.first_name = first_name
                tutor_usuario.last_name = last_name
                tutor_usuario.telefono = tutor_telefono
                tutor_usuario.email = tutor_email
                tutor_usuario.cedula = tutor_cedula
                tutor_usuario.tipo_documento = tutor_tipo_documento
                tutor_usuario.save()
                
                tutor.direccion = tutor_direccion
                tutor.provincia = provincia
                tutor.save()
                
                # 2. Actualizar paciente
                paciente.nombres = nombres
                paciente.apellidos = apellidos
                paciente.fecha_nacimiento = fecha_nacimiento
                paciente.sexo = sexo
                paciente.provincia = provincia
                paciente.tipo_sangre = tipo_sangre
                paciente.alergias = alergias
                paciente.direccion = direccion
                paciente.antecedentes_medicos = antecedentes_medicos

                if medico_asignado_id:
                    medico_asignado = CustomUser.objects.filter(pk=medico_asignado_id).first()
                    paciente.medico_asignado = medico_asignado
                else:
                    paciente.medico_asignado = None
                    
                if estado_actual in dict(Paciente.EstadoPaciente.choices):
                    paciente.estado_actual = estado_actual
                    
                paciente.save()
                
                registrar_actividad(
                    usuario=request.user,
                    accion="Editar Paciente",
                    modelo="Paciente",
                    objeto_id=str(paciente.id),
                    objeto_repr=paciente.nombre_completo,
                    descripcion=f'Datos actualizados para el paciente {paciente.nombre_completo}'
                )
                
            messages.success(request, f"Paciente {paciente.nombre_completo} actualizado correctamente.")
            return redirect("pacientes:expediente", pk=paciente.pk)

    pin_reseteado = None
    _pin_data = request.session.get("pin_reseteado")
    if _pin_data and _pin_data.get("paciente_id") == str(paciente.id):
        pin_reseteado = request.session.pop("pin_reseteado")

    medicos = CustomUser.objects.filter(rol__in=["MEDICO", "PEDIATRA", "ONCOLOGO", "PERSONAL_FACCI"])
    cribados_qs = paciente.cribados.select_related("medico").all()
    ultima_visita = "Nunca"
    if cribados_qs.exists():
        ultima_visita = _fecha_corta(cribados_qs.first().fecha_evaluacion)

    context = {
        "titulo_pagina": f"Editar - {paciente.nombres} {paciente.apellidos}",
        "paciente": paciente,
        "provincias": PROVINCIAS_RD,
        "medicos": medicos,
        "estados": Paciente.EstadoPaciente.choices,
        "tipos_sangre": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
        "ultima_visita": ultima_visita,
        "fecha_registro": _fecha_corta(paciente.created_at),
        "cribados_count": cribados_qs.count(),
        "puede_resetear_pin": _puede_resetear_pin(request.user, paciente),
        "pin_reseteado": pin_reseteado,
    }
    return render(request, "pacientes/editar.html", context)


@login_required
def resetear_pin_padre(request, pk):
    paciente = get_object_or_404(Paciente, pk=pk)
    # La autorización de esta acción es independiente del gate de edición de
    # editar_view: depende solo de _puede_resetear_pin (no del acceso a la página).

    if request.method != "POST":
        return redirect("pacientes:editar", pk=pk)

    if not _puede_resetear_pin(request.user, paciente):
        messages.error(request, "No tiene permiso para resetear el PIN de acceso de este paciente.")
        return redirect("pacientes:editar", pk=pk)

    tutor_usuario = paciente.padre_tutor.usuario
    pin = "".join(secrets.choice("0123456789") for _ in range(6))
    tutor_usuario.set_password(pin)
    tutor_usuario.save(update_fields=["password"])

    registrar_actividad(
        usuario=request.user,
        accion="Resetear PIN de acceso",
        modelo="Paciente",
        objeto_id=str(paciente.id),
        objeto_repr=paciente.nombre_completo,
        descripcion=(
            f"Se reseteó el PIN de acceso del padre/tutor "
            f"{tutor_usuario.get_full_name()} (paciente {paciente.nombre_completo})."
        ),
        dedupe_seconds=0,
    )

    request.session["pin_reseteado"] = {
        "pin": pin,
        "tutor": tutor_usuario.get_full_name(),
        "paciente_id": str(paciente.id),
    }
    return redirect("pacientes:editar", pk=pk)


@login_required
def expediente_view(request, pk):
    from apps.cribado.models import CuestionarioCribado

    paciente = get_object_or_404(
        Paciente.objects.select_related("medico_asignado", "padre_tutor__usuario"),
        pk=pk,
    )

    pin_creado = None
    _pin_data = request.session.get("pin_creado")
    if _pin_data and _pin_data.get("paciente_id") == str(paciente.id):
        pin_creado = request.session.pop("pin_creado")

    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if paciente.medico_asignado != request.user and paciente.creado_por != request.user:
            messages.error(request, 'No tiene permiso para ver el expediente de este paciente.')
            return redirect('pacientes:lista')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        tiene_referencia_propia = paciente.referencias.filter(especialista_destino=request.user).exists()
        tiene_referencia_urgente_sin_asignar = paciente.referencias.filter(
            especialista_destino__isnull=True,
            estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
            prioridad=ReferenciaMedica.Prioridad.URGENTE,
        ).exists()
        if not (tiene_referencia_propia or tiene_referencia_urgente_sin_asignar):
            messages.error(request, 'No tiene permiso para ver el expediente de este paciente, ya que no le ha sido referido.')
            return redirect('referencias:lista')

    if request.method == "POST":
        action = request.POST.get("action")
        
        # Restrict clinical actions (prescribing indications, clinical notes, requesting studies)
        # to clinicians only. Personal FACCI is blocked from doing clinical tasks.
        if action in ["guardar_indicaciones", "eliminar_indicacion", "solicitar_estudio", "eliminar_estudio_solicitud"]:
            if request.user.rol == CustomUser.Rol.PERSONAL_FACCI:
                messages.error(request, 'Su rol no tiene autorización para realizar esta acción clínica.')
                return redirect(request.path)
        
        if action == "guardar_indicaciones":
            tipo_indicacion = request.POST.get("tipo_indicacion", "OTRA")
            titulo = request.POST.get("titulo", "").strip()
            descripcion = request.POST.get("descripcion", "").strip()
            prioridad = request.POST.get("prioridad", "MEDIA")
            visible_padre = request.POST.get("visible_padre") == "on"
            
            if not titulo or not descripcion:
                messages.error(request, "Debe especificar un título y descripción para la indicación.")
                return redirect(f"{request.path}?tab=indicaciones")
                
            from apps.seguimiento.models import IndicacionMedica
            IndicacionMedica.objects.create(
                paciente=paciente,
                medico=request.user,
                tipo_indicacion=tipo_indicacion,
                titulo=titulo,
                descripcion=descripcion,
                prioridad=prioridad,
                activa=True,
                visible_padre=visible_padre,
            )
            
            # También logueamos y creamos un seguimiento vacío hoy para trazabilidad general si no existe
            hoy = timezone.now().date()
            ultimo_seguimiento = paciente.seguimientos.order_by('-fecha_seguimiento').first()
            if not (ultimo_seguimiento and ultimo_seguimiento.fecha_seguimiento.date() == hoy):
                SeguimientoPaciente.objects.create(
                    paciente=paciente,
                    medico=request.user,
                    estado_clinico=paciente.get_estado_actual_display(),
                    tratamiento_actual=f"Nueva indicación prescrita: {titulo}",
                    observaciones=f"Indicación tipo {tipo_indicacion} con prioridad {prioridad}.",
                )
            
            registrar_actividad(
                usuario=request.user,
                accion="Crear Indicación Médica",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Creada indicación "{titulo}" ({tipo_indicacion}) para el paciente {paciente.nombre_completo}'
            )
            
            messages.success(request, "Indicación médica creada correctamente.")
            return redirect(f"{request.path}?tab=indicaciones")
            
        elif action == "editar_indicacion":
            indicacion_id = request.POST.get("indicacion_id")
            from apps.seguimiento.models import IndicacionMedica
            ind = get_object_or_404(IndicacionMedica, id=indicacion_id, paciente=paciente)
            ind.titulo = request.POST.get("titulo", ind.titulo).strip()
            ind.descripcion = request.POST.get("descripcion", ind.descripcion).strip()
            ind.tipo_indicacion = request.POST.get("tipo_indicacion", ind.tipo_indicacion)
            ind.prioridad = request.POST.get("prioridad", ind.prioridad)
            ind.visible_padre = request.POST.get("visible_padre") == "on"
            ind.save()
            registrar_actividad(
                usuario=request.user,
                accion="Editar Indicación Médica",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Actualizada indicación "{ind.titulo}" para el paciente {paciente.nombre_completo}'
            )
            messages.success(request, "Indicación médica actualizada correctamente.")
            return redirect(f"{request.path}?tab=indicaciones")

        elif action == "eliminar_indicacion" or action == "desactivar_indicacion":
            indicacion_id = request.POST.get("indicacion_id")
            from apps.seguimiento.models import IndicacionMedica
            ind = get_object_or_404(IndicacionMedica, id=indicacion_id, paciente=paciente)
            
            registrar_actividad(
                usuario=request.user,
                accion="Desactivar Indicación Médica",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Desactivada indicación "{ind.titulo}" para el paciente {paciente.nombre_completo}'
            )
            
            ind.activa = False
            ind.save(update_fields=['activa', 'updated_at'])
            messages.success(request, "Indicación médica desactivada correctamente.")
            return redirect(f"{request.path}?tab=indicaciones")
            
        elif action == "solicitar_estudio":
            titulo = request.POST.get("titulo", "").strip()
            descripcion = request.POST.get("descripcion", "").strip()
            if not titulo:
                messages.error(request, "Debe especificar el título/nombre del estudio solicitado.")
                return redirect(f"{request.path}?tab=estudios")
            
            from apps.documentos.models import SolicitudDocumento
            SolicitudDocumento.objects.create(
                paciente=paciente,
                medico_solicitante=request.user,
                titulo=titulo,
                descripcion=descripcion,
                estado='PENDIENTE'
            )
            
            registrar_actividad(
                usuario=request.user,
                accion="Solicitar Estudio Médico",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Solicitado estudio "{titulo}" para el paciente {paciente.nombre_completo}'
            )
            messages.success(request, "Estudio médico solicitado correctamente.")
            return redirect(f"{request.path}?tab=estudios")

        elif action == "subir_estudio_admin":
            solicitud_id = request.POST.get("solicitud_id")
            tipo_documento = request.POST.get("tipo_documento", "OTRO")
            descripcion = request.POST.get("descripcion", "").strip()
            fecha_documento_str = request.POST.get("fecha_documento")
            archivo = request.FILES.get("archivo")
            
            if not archivo:
                messages.error(request, "Debe cargar un archivo de resultados.")
                return redirect(f"{request.path}?tab=estudios")
                
            from django.utils.dateparse import parse_date
            import datetime
            fecha_documento = parse_date(fecha_documento_str) if fecha_documento_str else datetime.date.today()
            if not fecha_documento:
                fecha_documento = datetime.date.today()
                
            from apps.documentos.models import DocumentoMedico, SolicitudDocumento
            doc = DocumentoMedico.objects.create(
                paciente=paciente,
                subido_por=request.user,
                tipo_documento=tipo_documento,
                archivo=archivo,
                descripcion=descripcion,
                fecha_documento=fecha_documento,
                estado='REVISADO'
            )
            
            sol = None
            if solicitud_id:
                sol = SolicitudDocumento.objects.filter(id=solicitud_id, paciente=paciente).first()
                if sol:
                    sol.documento_asociado = doc
                    sol.estado = 'REVISADO'
                    sol.save()
                    
            desc_log = f'Subido resultado para estudio "{sol.titulo if sol else tipo_documento}"'
            registrar_actividad(
                usuario=request.user,
                accion="Cargar Resultado de Estudio",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'{desc_log} para el paciente {paciente.nombre_completo}'
            )
            messages.success(request, "Resultado de estudio cargado correctamente.")
            return redirect(f"{request.path}?tab=estudios")

        elif action == "revisar_estudio":
            solicitud_id = request.POST.get("solicitud_id")
            from apps.documentos.models import SolicitudDocumento
            sol = get_object_or_404(SolicitudDocumento, id=solicitud_id, paciente=paciente)
            sol.estado = 'REVISADO'
            sol.save()
            
            if sol.documento_asociado:
                sol.documento_asociado.estado = 'REVISADO'
                sol.documento_asociado.save()
                
            registrar_actividad(
                usuario=request.user,
                accion="Revisar Estudio Médico",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Revisado y completado estudio "{sol.titulo}" para el paciente {paciente.nombre_completo}'
            )
            messages.success(request, "Estudio médico marcado como revisado y completado.")
            return redirect(f"{request.path}?tab=estudios")

        elif action == "eliminar_estudio_solicitud":
            solicitud_id = request.POST.get("solicitud_id")
            from apps.documentos.models import SolicitudDocumento
            sol = get_object_or_404(SolicitudDocumento, id=solicitud_id, paciente=paciente)
            titulo = sol.titulo
            
            if sol.documento_asociado:
                sol.documento_asociado.delete()
            sol.delete()
            
            registrar_actividad(
                usuario=request.user,
                accion="Eliminar Solicitud de Estudio",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Eliminado estudio "{titulo}" para el paciente {paciente.nombre_completo}'
            )
            messages.success(request, "Solicitud de estudio eliminada correctamente.")
            return redirect(f"{request.path}?tab=estudios")

        elif action == "registrar_seguimiento":
            from django.utils.dateparse import parse_datetime
            from apps.seguimiento.services import registrar_seguimiento
            proxima_cita_str = request.POST.get("proxima_fecha_seguimiento", "").strip()
            motivo = request.POST.get("observaciones", "").strip()
            medico_id = request.POST.get("medico_seguimiento", "").strip()
            lugar_id = request.POST.get("lugar_seguimiento", "").strip()
            lugar = CentroSalud.objects.filter(pk=lugar_id).first() if lugar_id else None
            try:
                peso_kg = float(request.POST.get("peso_kg", "").strip() or 0) or None
            except (ValueError, TypeError):
                peso_kg = None
            try:
                talla_cm = float(request.POST.get("talla_cm", "").strip() or 0) or None
            except (ValueError, TypeError):
                talla_cm = None
            try:
                temperatura_c = float(request.POST.get("temperatura_c", "").strip() or 0) or None
            except (ValueError, TypeError):
                temperatura_c = None
            tension_arterial = request.POST.get("tension_arterial", "").strip()
            from django.utils.timezone import make_aware, is_naive
            proxima_cita_dt = parse_datetime(proxima_cita_str)
            if not proxima_cita_dt:
                messages.error(request, "Fecha de seguimiento inválida. Por favor selecciona una fecha y hora.")
                return redirect(f"{request.path}?tab=resumen")
            if is_naive(proxima_cita_dt):
                proxima_cita_dt = make_aware(proxima_cita_dt)
            if proxima_cita_dt < timezone.now():
                messages.error(request, "La fecha de la cita no puede ser en el pasado.")
                return redirect(f"{request.path}?tab=resumen")
            medico_seguimiento = None
            if medico_id:
                medico_seguimiento = CustomUser.objects.filter(pk=medico_id).first()
            seguimiento = registrar_seguimiento(
                paciente=paciente,
                autor=request.user,
                estado_clinico=paciente.get_estado_actual_display(),
                observaciones=motivo or "Seguimiento programado.",
                proxima_fecha_seguimiento=proxima_cita_dt,
                medico_seguimiento=medico_seguimiento,
                lugar_seguimiento=lugar,
                peso_kg=peso_kg,
                talla_cm=talla_cm,
                temperatura_c=temperatura_c,
                tension_arterial=tension_arterial,
            )
            for alerta in seguimiento.alertas_valores_atipicos:
                messages.warning(request, alerta)
            messages.success(request, f'Seguimiento registrado para el {proxima_cita_dt.strftime("%d de %B de %Y a las %H:%M")}.')
            return redirect(f"{request.path}?tab=resumen")

        elif action == "editar_seguimiento":
            from django.utils.dateparse import parse_datetime
            from django.utils.timezone import make_aware, is_naive
            seguimiento_id = request.POST.get("seguimiento_id")
            seg = get_object_or_404(SeguimientoPaciente, id=seguimiento_id, paciente=paciente)
            
            proxima_cita_str = request.POST.get("proxima_fecha_seguimiento", "").strip()
            motivo = request.POST.get("observaciones", "").strip()
            medico_id = request.POST.get("medico_seguimiento", "").strip()
            lugar_id = request.POST.get("lugar_seguimiento", "").strip()
            lugar = CentroSalud.objects.filter(pk=lugar_id).first() if lugar_id else None

            proxima_cita_dt = parse_datetime(proxima_cita_str)
            if not proxima_cita_dt:
                messages.error(request, "Fecha de seguimiento inválida.")
                return redirect(f"{request.path}?tab=resumen")
            if is_naive(proxima_cita_dt):
                proxima_cita_dt = make_aware(proxima_cita_dt)
            if proxima_cita_dt < timezone.now():
                messages.error(request, "La fecha de la cita no puede ser en el pasado.")
                return redirect(f"{request.path}?tab=resumen")
                
            medico_seguimiento = None
            if medico_id:
                medico_seguimiento = CustomUser.objects.filter(pk=medico_id).first()
                
            seg.proxima_fecha_seguimiento = proxima_cita_dt
            seg.medico_seguimiento = medico_seguimiento
            seg.lugar_seguimiento = lugar
            seg.observaciones = motivo
            seg.save()
            
            registrar_actividad(
                usuario=request.user,
                accion="Modificar Seguimiento Programado",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Modificada la cita de seguimiento programada para el {proxima_cita_dt.strftime("%d/%m/%Y %H:%M")} del paciente {paciente.nombre_completo}'
            )
            messages.success(request, f'La cita de seguimiento ha sido modificada correctamente para el {proxima_cita_dt.strftime("%d de %B de %Y a las %H:%M")}.')
            return redirect(f"{request.path}?tab=resumen")

        elif action == "cancelar_seguimiento":
            seguimiento_id = request.POST.get("seguimiento_id")
            seg = get_object_or_404(SeguimientoPaciente, id=seguimiento_id, paciente=paciente)
            
            es_cita = (
                seg.proxima_fecha_seguimiento is not None
                and not seg.sintomas_actuales
                and not seg.tratamiento_actual
                and not seg.medicamentos
            )
            
            fecha_cancelada = seg.proxima_fecha_seguimiento.strftime("%d/%m/%Y %H:%M") if seg.proxima_fecha_seguimiento else "desconocida"
            
            if es_cita:
                seg.delete()
            else:
                seg.proxima_fecha_seguimiento = None
                seg.medico_seguimiento = None
                seg.lugar_seguimiento = None
                seg.save()
                
            registrar_actividad(
                usuario=request.user,
                accion="Cancelar Seguimiento Programado",
                modelo="Paciente",
                objeto_id=str(paciente.id),
                objeto_repr=paciente.nombre_completo,
                descripcion=f'Cancelada la cita de seguimiento del {fecha_cancelada} para el paciente {paciente.nombre_completo}'
            )
            
            messages.success(request, f"La cita de seguimiento del {fecha_cancelada} ha sido cancelada correctamente.")
            return redirect(f"{request.path}?tab=resumen")

        elif action == "agregar_nota" or not action:
            if request.user.rol == CustomUser.Rol.PERSONAL_FACCI:
                messages.error(request, 'Su rol no tiene autorización para agregar notas clínicas.')
                return redirect(request.path)
            nota_form = NotaClinicaForm(request.POST)
            if nota_form.is_valid():
                nota = nota_form.save(commit=False)
                nota.paciente = paciente
                nota.autor = request.user
                nota.save()
                messages.success(request, "Nota clinica agregada al expediente.")
                return redirect(f"{request.path}?tab=resumen")
            messages.error(request, "Revise los datos de la nota clinica.")
    else:
        nota_form = NotaClinicaForm()

    cribados_qs = paciente.cribados.select_related("medico").all()
    referencias_qs = paciente.referencias.select_related("medico_referente", "especialista_destino").all()
    documentos_qs = paciente.documentos.select_related("subido_por").all()
    seguimientos_qs = paciente.seguimientos.select_related("medico").all()
    notas_qs = paciente.notas_clinicas.select_related("autor").all()
    
    from apps.documentos.models import SolicitudDocumento, DocumentoMedico
    solicitudes_qs = paciente.solicitudes_documento.select_related("medico_solicitante", "documento_asociado").order_by('-created_at')
    solicitudes_pendientes_count = solicitudes_qs.filter(estado='PENDIENTE').count()

    historial = []
    for idx, cribado in enumerate(cribados_qs):
        historial.append({
            "id": str(cribado.id),
            "numero": idx + 1,
            "fecha": _fecha_corta(cribado.fecha_evaluacion),
            "medico": _autor_nombre(cribado.medico),
            "nivel": cribado.get_nivel_riesgo_display(),
            "nivel_key": cribado.nivel_riesgo,
            "score": cribado.puntaje_total,
            "requiere_referencia": cribado.requiere_referencia,
            "observaciones": cribado.observaciones,
        })

    tutor = paciente.padre_tutor
    tutor_usuario = tutor.usuario if tutor else None
    tutor_nombre = _autor_nombre(tutor_usuario) if tutor_usuario else "-"
    tutor_telefono = getattr(tutor_usuario, "telefono", "-") or "-"
    tutor_email = tutor_usuario.email if tutor_usuario else "-"
    tutor_direccion = tutor.direccion if tutor else "-"

    fechas_clinicas = [
        *(cribado.fecha_evaluacion for cribado in cribados_qs),
        *(seguimiento.fecha_seguimiento for seguimiento in seguimientos_qs),
        *(nota.created_at for nota in notas_qs),
    ]
    fechas_clinicas = [fecha for fecha in fechas_clinicas if fecha]
    ultima_visita = _fecha_corta(max(fechas_clinicas)) if fechas_clinicas else ""

    desde = paciente.created_at
    ahora = timezone.now()
    
    # Calculate months and days precisely
    d1 = desde.date()
    d2 = ahora.date()
    
    months = 0
    temp_date = d1
    
    import calendar
    while True:
        m = temp_date.month + 1
        y = temp_date.year
        if m > 12:
            m = 1
            y += 1
        
        _, max_days = calendar.monthrange(y, m)
        d = min(temp_date.day, max_days)
        next_month_date = temp_date.replace(year=y, month=m, day=d)
        if next_month_date > d2:
            break
        temp_date = next_month_date
        months += 1
        
    days = (d2 - temp_date).days
    
    if months == 0:
        if days == 1:
            meses_seguimiento = "1 día"
        else:
            meses_seguimiento = f"{days} días"
    else:
        m_str = "1 mes" if months == 1 else f"{months} meses"
        if days == 0:
            meses_seguimiento = m_str
        elif days == 1:
            meses_seguimiento = f"{m_str} y 1 día"
        else:
            meses_seguimiento = f"{m_str} y {days} días"

    # Cargar Indicaciones Médicas dinámicas
    from apps.seguimiento.models import IndicacionMedica
    indicaciones_list = paciente.indicaciones_medicas.all()
    fecha_actualizacion_ind = 'Sin registros'
    if indicaciones_list.exists():
        fecha_actualizacion_ind = _fecha_corta(indicaciones_list.order_by('-updated_at').first().updated_at)

    ultimo_seguimiento = paciente.seguimientos.order_by('-fecha_seguimiento').first()
    tratamiento_actual = ultimo_seguimiento.tratamiento_actual if ultimo_seguimiento else ''
    observaciones_indicaciones = ultimo_seguimiento.observaciones if ultimo_seguimiento else ''

    # Próxima cita: busca en seguimiento
    proxima_cita_seg = paciente.seguimientos.filter(
        proxima_fecha_seguimiento__isnull=False,
        proxima_fecha_seguimiento__gte=timezone.now()
    ).order_by('proxima_fecha_seguimiento').first()

    from apps.core.constants import RESTRICCIONES_GENERALES
    _ind_db = paciente.indicaciones_medicas.filter(activa=True).order_by('prioridad', '-created_at')
    indicaciones_estaticas = [
        {
            'titulo': i.titulo,
            'descripcion': i.descripcion,
            'icono': i.icono,
            'prioridad': i.get_prioridad_display(),
        }
        for i in _ind_db
    ]
    restricciones = RESTRICCIONES_GENERALES

    from apps.laboratorio.models import ResultadoLaboratorio
    resultados_lab = list(
        paciente.resultados_laboratorio.select_related('solicitado_por').order_by('-fecha_muestra')[:10]
    )
    resultados_lab_count = paciente.resultados_laboratorio.count()
    resultados_lab_criticos = paciente.resultados_laboratorio.filter(hay_valores_criticos=True).count()

    from apps.alojamiento.models import EstanciaFamiliar
    estancias_list = list(
        EstanciaFamiliar.objects.filter(paciente=paciente)
        .select_related('habitacion')
        .order_by('-fecha_ingreso')[:10]
    )
    estancias_activas = EstanciaFamiliar.objects.filter(
        paciente=paciente, estado=EstanciaFamiliar.Estado.ACTIVA
    ).count()

    from apps.psicosocial.models import EvaluacionPsicosocial
    psico_list = list(
        EvaluacionPsicosocial.objects.filter(paciente=paciente)
        .select_related('evaluador')
        .order_by('-fecha_evaluacion')[:10]
    )
    psico_count = EvaluacionPsicosocial.objects.filter(paciente=paciente).count()
    psico_criticos = EvaluacionPsicosocial.objects.filter(
        paciente=paciente,
        nivel_riesgo__in=[EvaluacionPsicosocial.NivelRiesgo.ALTO, EvaluacionPsicosocial.NivelRiesgo.CRITICO],
    ).count()

    context = {
        "titulo_pagina": f"Expediente - {paciente.nombres} {paciente.apellidos}",
        "paciente": paciente,
        "historial_cribados": historial,
        "notas_clinicas": notas_qs,
        "nota_form": nota_form,
        "referencias": referencias_qs,
        "documentos": documentos_qs,
        "seguimientos": seguimientos_qs,
        "timeline_clinico": _build_timeline(
            cribados_qs, referencias_qs, seguimientos_qs, documentos_qs, notas_qs,
            reportes_sintomas=paciente.reportes_sintomas.select_related('tutor__usuario').all(),
            indicaciones=paciente.indicaciones_medicas.select_related('medico').all(),
            solicitudes=paciente.solicitudes_documento.select_related('medico_solicitante').all(),
        ),
        "tutor_nombre": tutor_nombre,
        "tutor_telefono": tutor_telefono,
        "tutor_email": tutor_email,
        "tutor_direccion": tutor_direccion,
        "ultima_visita": ultima_visita,
        "proxima_cita_seg": proxima_cita_seg,
        "medicos_disponibles": CustomUser.objects.filter(
            rol__in=['MEDICO', 'PEDIATRA', 'ONCOLOGO', 'PERSONAL_FACCI']
        ).order_by('first_name'),
        "centros_disponibles": CentroSalud.objects.filter(activo=True).order_by('nombre'),
        "meses_seguimiento": meses_seguimiento,
        "documentos_count": documentos_qs.count(),
        "seguimientos_count": seguimientos_qs.count(),
        "tab_activo": request.GET.get("tab", "resumen"),
        "solicitudes_documento": solicitudes_qs,
        "solicitudes_pendientes_count": solicitudes_pendientes_count,
        "tipos_documento_choices": DocumentoMedico.TipoDocumento.choices,
        "tratamiento_actual": tratamiento_actual,
        "observaciones_indicaciones": observaciones_indicaciones,
        "fecha_actualizacion_ind": fecha_actualizacion_ind,
        "indicaciones_estaticas": indicaciones_estaticas,
        "restricciones": restricciones,
        "indicaciones_list": indicaciones_list,
        "tipos_indicacion_choices": IndicacionMedica.TipoIndicacion.choices,
        "prioridad_choices": IndicacionMedica.Prioridad.choices,
        "resultados_lab": resultados_lab,
        "resultados_lab_count": resultados_lab_count,
        "resultados_lab_criticos": resultados_lab_criticos,
        "estancias_list": estancias_list,
        "estancias_activas": estancias_activas,
        "psico_list": psico_list,
        "psico_count": psico_count,
        "psico_criticos": psico_criticos,
        "score_maximo": len(CuestionarioCribado.CAMPOS_SINTOMAS),
        "pin_creado": pin_creado,
    }
    return render(request, "pacientes/expediente.html", context)
