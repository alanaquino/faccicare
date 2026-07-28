import datetime
import os
import mimetypes
import re
from urllib.parse import parse_qs, urlparse

from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.templatetags.static import static
from apps.notificaciones.models import Notificacion
from apps.notificaciones.services import sincronizar_notificaciones_usuario
from apps.seguimiento.models import SeguimientoPaciente, IndicacionMedica
from apps.documentos.models import DocumentoMedico, SolicitudDocumento
from apps.pacientes.models import Paciente
from .models import RecursoEducativo, RegistroTomaMedicamento


def _youtube_embed_url(video_url):
    """Convierte solo enlaces reconocidos de YouTube en una URL embebible."""
    if not video_url:
        return ''

    parsed = urlparse(video_url)
    host = parsed.netloc.lower().split(':')[0]
    video_id = ''

    if host in {'youtu.be', 'www.youtu.be'}:
        video_id = parsed.path.strip('/').split('/')[0]
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        elif parsed.path.startswith(('/embed/', '/shorts/')):
            video_id = parsed.path.strip('/').split('/')[1]

    if re.fullmatch(r'[A-Za-z0-9_-]{6,20}', video_id or ''):
        return f'https://www.youtube-nocookie.com/embed/{video_id}'
    return ''


def _recurso_imagen_url(recurso):
    imagen = recurso.imagen or 'img/portal_padres_bg.jpg'
    return imagen if imagen.startswith(('http://', 'https://', '/')) else static(imagen)


def _get_hospital(paciente):
    """Retorna el nombre del hospital del médico asignado, con fallback a BD."""
    if paciente and paciente.medico_asignado and paciente.medico_asignado.centro_medico:
        return paciente.medico_asignado.centro_medico.nombre
    from apps.core.models import CentroSalud
    default = CentroSalud.objects.filter(activo=True).order_by('nombre').first()
    return default.nombre if default else 'Sin asignar'


@login_required
def estado_view(request):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return redirect('home')

    tutor = getattr(request.user, 'perfil_padre', None)
    if not tutor:
        return render(request, 'padres/estado.html', {'titulo_pagina': 'Estado del Paciente'})

    paciente = tutor.pacientes.first()
    if not paciente:
        return render(request, 'padres/estado.html', {'titulo_pagina': 'Estado del Paciente'})

    # 1. Dinamizar paciente familiar desde DB
    paciente_familiar = {
        'id': str(paciente.id),
        'nombre': paciente.nombre_completo,
        'nombres': paciente.nombres,
        'apellidos': paciente.apellidos,
        'edad': paciente.edad,
        'estado': paciente.get_estado_actual_display(),
        'medico': paciente.medico,
        'hospital': _get_hospital(paciente),
        'diagnostico': paciente.get_estado_actual_display(),
        'grupo_sanguineo': paciente.tipo_sangre or 'N/D',
        'alergias': paciente.alergias or 'Ninguna conocida',
        'iniciales': paciente.iniciales,
    }

    # 2. Medicación de hoy desde la base de datos (IndicacionMedica) o fallback
    from apps.seguimiento.models import IndicacionMedica
    ultimo_seguimiento = paciente.seguimientos.order_by('-fecha_seguimiento').first()
    db_meds = paciente.indicaciones_medicas.filter(
        tipo_indicacion=IndicacionMedica.TipoIndicacion.MEDICACION, activa=True
    ).order_by('prioridad', '-created_at')

    # Slugs tomados hoy — fuente de verdad: BD
    hoy = timezone.now().date()
    tomados_hoy = set(
        RegistroTomaMedicamento.objects.filter(paciente=paciente, fecha=hoy)
        .values_list('nombre_medicamento', 'indice')
    )
    slugs_tomados = {f"{nombre}_{idx}" for nombre, idx in tomados_hoy}

    medicacion_hoy = []

    if db_meds.exists():
        for idx, med in enumerate(db_meds):
            desc = med.descripcion.strip()
            dosis = desc
            hora = "Según indicación"
            if " cada " in desc.lower():
                parts = desc.lower().split(" cada ")
                dosis = parts[0].strip().capitalize()
                hora = "Cada " + parts[1].strip()
            elif " a las " in desc.lower():
                parts = desc.lower().split(" a las ")
                dosis = parts[0].strip().capitalize()
                hora = parts[1].strip().upper()
            medicacion_hoy.append({
                'nombre': med.titulo,
                'dosis': dosis,
                'hora': hora,
                'tomado': f"{med.titulo}_{idx}" in slugs_tomados,
                'icono': 'medication',
            })
    else:
        if ultimo_seguimiento and ultimo_seguimiento.medicamentos:
            lines = [line.strip() for line in ultimo_seguimiento.medicamentos.split('\n') if line.strip()]
            for idx, line in enumerate(lines):
                parts = line.split(':')
                if len(parts) >= 2:
                    nombre = parts[0].strip()
                    resto = parts[1].strip()
                else:
                    parts = line.split('-')
                    if len(parts) >= 2:
                        nombre = parts[0].strip()
                        resto = parts[1].strip()
                    else:
                        nombre = line
                        resto = 'Según indicación'
                horas_sugeridas = ["8:00 AM", "12:00 PM", "8:00 PM", "4:00 PM", "10:00 PM"]
                hora = horas_sugeridas[idx % len(horas_sugeridas)]
                if "a las" in resto.lower():
                    r_parts = resto.lower().split("a las")
                    dosis = r_parts[0].strip()
                    hora = r_parts[1].strip().upper()
                elif "cada" in resto.lower():
                    r_parts = resto.lower().split("cada")
                    dosis = r_parts[0].strip()
                    hora = "Cada " + r_parts[1].strip()
                else:
                    dosis = resto
                medicacion_hoy.append({
                    'nombre': nombre,
                    'dosis': dosis,
                    'hora': hora,
                    'tomado': f"{nombre}_{idx}" in slugs_tomados,
                    'icono': 'medication',
                })
        else:
            fallback = [
                ('Vitaminas pediátricas', '1 tableta', '8:00 AM'),
                ('Hierro pediátrico',     '5 ml',      '12:00 PM'),
                ('Ácido fólico',          '1 tableta', '8:00 PM'),
            ]
            for idx, (nombre, dosis, hora) in enumerate(fallback):
                medicacion_hoy.append({
                    'nombre': nombre,
                    'dosis': dosis,
                    'hora': hora,
                    'tomado': f"{nombre}_{idx}" in slugs_tomados,
                    'icono': 'medication',
                })

    # 3. Próximo seguimiento — se lee del seguimiento
    proxima_cita = None
    if ultimo_seguimiento and ultimo_seguimiento.proxima_fecha_seguimiento and ultimo_seguimiento.proxima_fecha_seguimiento >= timezone.now():
        d = ultimo_seguimiento.proxima_fecha_seguimiento
        dias = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
        meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        dia_semana = dias.get(d.weekday(), '')
        mes = meses.get(d.month, '')
        proxima_cita = {
            'fecha': f'{dia_semana}, {d.day} {mes}',
            'hora': d.strftime('%I:%M %p').lstrip('0'),
            'medico': f'{paciente.medico} ({paciente.medico_asignado.especialidad or "Pediatría"})' if paciente.medico_asignado else 'Equipo FACCI',
            'lugar': f'{paciente_familiar["hospital"]}',
            'tipo': 'Control clínico' if paciente.estado_actual == 'FINALIZADO' else 'Control de tratamiento',
        }

    # 4. Alertas reales
    sincronizar_notificaciones_usuario(request.user)
    alertas = [
        {'tipo': 'precaucion', 'texto': f'Si {paciente.nombres} presenta fiebre mayor a 38°C o fatiga extrema, contáctenos inmediatamente.', 'color': 'error', 'icono': 'warning'},
    ]
    if ultimo_seguimiento and ultimo_seguimiento.estado_clinico:
        alertas.append({
            'tipo': 'info',
            'texto': f'Último reporte clínico: {ultimo_seguimiento.estado_clinico}',
            'color': 'primary',
            'icono': 'info',
        })

    context = {
        'titulo_pagina': 'Estado del Paciente',
        'paciente': paciente_familiar,
        'medicacion_hoy': medicacion_hoy,
        'proxima_cita': proxima_cita,
        'alertas': alertas,
        'recursos': RecursoEducativo.objects.filter(activo=True)[:3],
    }
    return render(request, 'padres/estado.html', context)


@login_required
def evolucion_view(request):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return redirect('home')

    tutor = getattr(request.user, 'perfil_padre', None)
    if not tutor:
        return redirect('auth_app:login_padres')

    paciente = tutor.pacientes.first()
    if not paciente:
        return redirect('padres:estado')

    paciente_familiar = {
        'nombre': paciente.nombre_completo,
        'nombres': paciente.nombres,
        'apellidos': paciente.apellidos,
        'edad': paciente.edad,
        'estado': paciente.get_estado_actual_display(),
        'medico': paciente.medico,
        'hospital': _get_hospital(paciente),
        'diagnostico': paciente.get_estado_actual_display(),
        'grupo_sanguineo': paciente.tipo_sangre or 'N/D',
        'alergias': paciente.alergias or 'Ninguna conocida',
        'iniciales': paciente.iniciales,
    }

    # Obtener el historial clínico de seguimientos del paciente ordenados por fecha
    seguimientos = paciente.seguimientos.order_by('-fecha_seguimiento')
    
    # Procesar para la línea de tiempo en el frontend
    timeline = []
    for s in seguimientos:
        timeline.append({
            'fecha': s.fecha_seguimiento.strftime('%d %b, %Y'),
            'hora': s.fecha_seguimiento.strftime('%I:%M %p').lstrip('0'),
            'medico': s.medico.nombre_completo,
            'estado_clinico': s.estado_clinico,
            'tratamiento_actual': s.tratamiento_actual,
            'observaciones': s.observaciones,
            'sintomas_actuales': s.sintomas_actuales,
            'medicamentos': s.medicamentos,
            'requiere_hospitalizacion': s.requiere_hospitalizacion,
        })

    context = {
        'titulo_pagina': 'Evolución del Paciente',
        'paciente': paciente_familiar,
        'timeline': timeline,
    }
    return render(request, 'padres/evolucion.html', context)


@login_required
def reportar_sintomas_view(request):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return redirect('home')

    tutor = getattr(request.user, 'perfil_padre', None)
    if not tutor:
        return redirect('auth_app:login_padres')

    paciente = tutor.pacientes.first()
    if not paciente:
        return redirect('padres:estado')

    paciente_familiar = {
        'nombre': paciente.nombre_completo,
        'nombres': paciente.nombres,
        'apellidos': paciente.apellidos,
        'edad': paciente.edad,
        'estado': paciente.get_estado_actual_display(),
        'medico': paciente.medico,
        'hospital': _get_hospital(paciente),
        'diagnostico': paciente.get_estado_actual_display(),
        'grupo_sanguineo': paciente.tipo_sangre or 'N/D',
        'alergias': paciente.alergias or 'Ninguna conocida',
        'iniciales': paciente.iniciales,
    }

    if request.method == 'POST':
        fecha_inicio = request.POST.get('fecha_inicio', '')
        if not fecha_inicio:
            fecha_inicio = timezone.now().strftime('%Y-%m-%d')
        gravedad = request.POST.get('gravedad', 'Leve')
        descripcion = request.POST.get('descripcion', '').strip()
        
        # Obtener los síntomas seleccionados
        sintomas_seleccionados = []
        for key in request.POST.keys():
            if key.startswith('sintoma_'):
                # Traducir los IDs a etiquetas legibles
                lbl = key.replace('sintoma_', '').replace('_', ' ').capitalize()
                sintomas_seleccionados.append(lbl)

        if not sintomas_seleccionados:
            messages.error(request, 'Debe seleccionar al menos un síntoma antes de enviar el reporte.')
            return redirect('padres:reportar_sintomas')
                
        # Persistir el reporte en base de datos
        from apps.padres.models import ReporteSintoma
        import datetime
        try:
            fecha_obj = datetime.date.fromisoformat(fecha_inicio)
        except ValueError:
            fecha_obj = timezone.now().date()
        ReporteSintoma.objects.create(
            paciente=paciente,
            tutor=tutor,
            fecha_inicio=fecha_obj,
            gravedad=gravedad,
            sintomas=sintomas_seleccionados,
            descripcion=descripcion,
        )
            
        messages.success(request, 'Síntomas reportados correctamente. El equipo médico ha sido alertado.')
        return redirect('padres:evolucion')

    context = {
        'titulo_pagina': 'Reportar Síntomas',
        'paciente': paciente_familiar,
        'categorias': [
            {
                'nombre': 'Síntomas Generales', 'icono': 'thermostat',
                'sintomas': [
                    {'id': 'fiebre', 'label': 'Fiebre'},
                    {'id': 'fatiga_extrema', 'label': 'Fatiga extrema'},
                    {'id': 'perdida_de_apetito', 'label': 'Pérdida de apetito'},
                    {'id': 'vomitos', 'label': 'Vómitos'},
                    {'id': 'perdida_de_peso', 'label': 'Pérdida de peso'},
                    {'id': 'irritabilidad', 'label': 'Irritabilidad'}
                ],
            },
            {
                'nombre': 'Dolor', 'icono': 'sentiment_very_dissatisfied',
                'sintomas': [
                    {'id': 'dolor_de_cabeza', 'label': 'Dolor de cabeza'},
                    {'id': 'dolor_abdominal', 'label': 'Dolor abdominal'},
                    {'id': 'dolor_en_huesos', 'label': 'Dolor en huesos'},
                    {'id': 'dolor_al_tragar', 'label': 'Dolor al tragar'}
                ],
            },
            {
                'nombre': 'Cambios Físicos', 'icono': 'visibility',
                'sintomas': [
                    {'id': 'moretones_inexplicados', 'label': 'Moretones inexplicados'},
                    {'id': 'cambios_en_la_piel', 'label': 'Cambios en la piel'},
                    {'id': 'inflamacion', 'label': 'Inflamación'},
                    {'id': 'sangrado_inusual', 'label': 'Sangrado inusual'}
                ],
            },
        ],
    }
    return render(request, 'padres/reportar_sintomas.html', context)


@login_required
def indicaciones_view(request):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return redirect('home')

    tutor = getattr(request.user, 'perfil_padre', None)
    if not tutor:
        return redirect('auth_app:login_padres')

    paciente = tutor.pacientes.first()
    if not paciente:
        return redirect('padres:estado')

    paciente_familiar = {
        'nombre': paciente.nombre_completo,
        'nombres': paciente.nombres,
        'apellidos': paciente.apellidos,
        'edad': paciente.edad,
        'estado': paciente.get_estado_actual_display(),
        'medico': paciente.medico,
        'hospital': _get_hospital(paciente),
        'diagnostico': paciente.get_estado_actual_display(),
        'grupo_sanguineo': paciente.tipo_sangre or 'N/D',
        'alergias': paciente.alergias or 'Ninguna conocida',
        'iniciales': paciente.iniciales,
    }

    ultimo_seguimiento = paciente.seguimientos.order_by('-fecha_seguimiento').first()
    indicaciones_activas = paciente.indicaciones_medicas.filter(activa=True)
    db_indicaciones = indicaciones_activas.filter(visible_padre=True).order_by('prioridad', '-created_at')
    indicaciones = []
    fecha_actualizacion = 'Reciente'

    if db_indicaciones.exists():
        prioridad_map = {
            'ALTA': 'Alta',
            'MEDIA': 'Media',
            'BAJA': 'Baja'
        }
        for ind in db_indicaciones:
            indicaciones.append({
                'titulo': ind.titulo,
                'descripcion': ind.descripcion,
                'icono': ind.icono,
                'prioridad': prioridad_map.get(ind.prioridad, 'Media'),
                'tipo_display': ind.get_tipo_indicacion_display(),
            })

        latest_ind = db_indicaciones.order_by('-updated_at').first()
        if latest_ind:
            d = latest_ind.updated_at
            meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
            fecha_actualizacion = f'{d.day} {meses.get(d.month, "")}, {d.year}'
    elif not indicaciones_activas.exists():
        if ultimo_seguimiento and (ultimo_seguimiento.tratamiento_actual or ultimo_seguimiento.observaciones):
            if ultimo_seguimiento.tratamiento_actual:
                indicaciones.append({
                    'titulo': 'Protocolo Activo',
                    'descripcion': ultimo_seguimiento.tratamiento_actual,
                    'icono': 'assignment',
                    'prioridad': 'Alta'
                })
            if ultimo_seguimiento.observaciones:
                indicaciones.append({
                    'titulo': 'Pauta Médica Específica',
                    'descripcion': ultimo_seguimiento.observaciones,
                    'icono': 'rate_review',
                    'prioridad': 'Alta'
                })

        if ultimo_seguimiento:
            d = ultimo_seguimiento.fecha_seguimiento
            meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
            fecha_actualizacion = f'{d.day} {meses.get(d.month, "")}, {d.year}'

    from apps.core.constants import RESTRICCIONES_GENERALES
    context = {
        'titulo_pagina': 'Indicaciones Médicas',
        'paciente': paciente_familiar,
        'indicaciones': indicaciones,
        'fecha_actualizacion': fecha_actualizacion,
        'restricciones': RESTRICCIONES_GENERALES,
    }
    return render(request, 'padres/indicaciones.html', context)


@login_required
def alertas_view(request):
    # Seed default notifications for the parent if they don't have any yet
    Notificacion.seed_for_user(request.user)
    
    notificaciones = Notificacion.objects.filter(usuario=request.user)
    sin_leer = Notificacion.objects.filter(usuario=request.user, leida=False).count()

    tutor = getattr(request.user, 'perfil_padre', None)
    paciente = tutor.pacientes.first() if tutor else None
    
    paciente_familiar = None
    if paciente:
        paciente_familiar = {
            'nombre': paciente.nombre_completo,
            'nombres': paciente.nombres,
            'apellidos': paciente.apellidos,
            'edad': paciente.edad,
            'estado': paciente.get_estado_actual_display(),
            'medico': paciente.medico,
            'hospital': _get_hospital(paciente),
            'diagnostico': paciente.get_estado_actual_display(),
            'grupo_sanguineo': paciente.tipo_sangre or 'N/D',
            'alergias': paciente.alergias or 'Ninguna conocida',
            'iniciales': paciente.iniciales,
        }

    context = {
        'titulo_pagina': 'Alertas del Paciente',
        'paciente': paciente_familiar,
        'notificaciones': notificaciones,
        'sin_leer': sin_leer,
    }
    return render(request, 'padres/alertas.html', context)


def _get_tutor_or_redirect(request):
    """Devuelve (tutor, paciente, redirect_response). Si retorna redirect != None, úsalo."""
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return None, None, redirect('home')
    tutor = getattr(request.user, 'perfil_padre', None)
    if not tutor:
        return None, None, redirect('auth_app:login_padres')
    paciente = tutor.pacientes.first()
    if not paciente:
        return tutor, None, redirect('padres:estado')
    return tutor, paciente, None


def _paciente_dict(paciente):
    return {
        'nombre': paciente.nombre_completo,
        'nombres': paciente.nombres,
        'apellidos': paciente.apellidos,
        'edad': paciente.edad,
        'estado': paciente.get_estado_actual_display(),
        'medico': paciente.medico,
        'hospital': _get_hospital(paciente),
        'diagnostico': paciente.get_estado_actual_display(),
        'grupo_sanguineo': paciente.tipo_sangre or 'N/D',
        'alergias': paciente.alergias or 'Ninguna conocida',
        'iniciales': paciente.iniciales,
    }


@login_required
def perfil_view(request):
    tutor, paciente, redir = _get_tutor_or_redirect(request)
    if redir:
        return redir

    context = {
        'titulo_pagina': 'Mi Perfil',
        'paciente': _paciente_dict(paciente),
        'tutor': {
            'nombre': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'telefono': request.user.telefono or '—',
            'provincia': tutor.provincia,
            'municipio': tutor.municipio,
            'direccion': tutor.direccion,
            'ocupacion': tutor.ocupacion or '—',
            'cedula': request.user.cedula or '—',
            'tipo_documento': request.user.get_tipo_documento_display() if hasattr(request.user, 'get_tipo_documento_display') else 'Cédula',
            'iniciales': request.user.iniciales,
            'relacion': tutor.get_parentesco_display() or 'Padre / Tutor Principal',
            'estado_civil': tutor.get_estado_civil_display() if tutor.estado_civil else '—',
            'contacto_emergencia': tutor.contacto_emergencia or '—',
            'telefono_emergencia': tutor.telefono_emergencia or '—',
        },
    }
    return render(request, 'padres/perfil.html', context)


@login_required
def editar_perfil_view(request):
    tutor, paciente, redir = _get_tutor_or_redirect(request)
    if redir:
        return redir

    from django.contrib import messages as msg

    if request.method == 'POST':
        user = request.user
        user.email    = request.POST.get('email', user.email).strip()
        user.telefono = request.POST.get('telefono', user.telefono).strip()
        if 'foto_perfil' in request.FILES:
            user.foto_perfil = request.FILES['foto_perfil']
        user.save()

        tutor.direccion           = request.POST.get('direccion', tutor.direccion).strip()
        tutor.provincia           = request.POST.get('provincia', tutor.provincia).strip()
        tutor.municipio           = request.POST.get('municipio', tutor.municipio).strip()
        tutor.ocupacion           = request.POST.get('ocupacion', tutor.ocupacion).strip()
        tutor.contacto_emergencia = request.POST.get('contacto_emergencia', tutor.contacto_emergencia).strip()
        tutor.telefono_emergencia = request.POST.get('telefono_emergencia', tutor.telefono_emergencia).strip()
        tutor.save()

        msg.success(request, 'Perfil actualizado correctamente.')
        return redirect('padres:perfil')

    context = {
        'titulo_pagina': 'Editar Perfil',
        'paciente': _paciente_dict(paciente),
        'tutor': {
            'nombre': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'telefono': request.user.telefono,
            'provincia': tutor.provincia,
            'municipio': tutor.municipio,
            'direccion': tutor.direccion,
            'ocupacion': tutor.ocupacion,
            'cedula': request.user.cedula or '—',
            'tipo_documento': request.user.get_tipo_documento_display() if hasattr(request.user, 'get_tipo_documento_display') else 'Cédula',
            'iniciales': request.user.iniciales,
            'relacion': tutor.get_parentesco_display() or 'Padre / Tutor Principal',
            'contacto_emergencia': tutor.contacto_emergencia,
            'telefono_emergencia': tutor.telefono_emergencia,
        },
    }
    return render(request, 'padres/editar_perfil.html', context)


from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
@require_POST
def marcar_medicamento_view(request):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return JsonResponse({'status': 'error', 'message': 'No autorizado'}, status=403)

    index = request.POST.get('index')
    nombre = request.POST.get('nombre', '').strip()

    if index is None or not nombre:
        return JsonResponse({'status': 'error', 'message': 'Parámetros inválidos'}, status=400)

    try:
        indice_int = int(index)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Índice inválido'}, status=400)

    tutor = getattr(request.user, 'perfil_padre', None)
    paciente = tutor.pacientes.first() if tutor else None
    if not paciente:
        return JsonResponse({'status': 'error', 'message': 'Sin paciente asociado'}, status=400)

    hoy = timezone.now().date()
    RegistroTomaMedicamento.objects.get_or_create(
        paciente=paciente,
        nombre_medicamento=nombre,
        indice=indice_int,
        fecha=hoy,
        defaults={'tutor': tutor},
    )
    return JsonResponse({'status': 'ok'})


@login_required
def documentos_view(request):
    tutor, paciente, redir = _get_tutor_or_redirect(request)
    if redir:
        return redir

    pacientes = tutor.pacientes.all()
    documentos = DocumentoMedico.objects.filter(
        paciente__in=pacientes,
        visible_padre=True,
    ).select_related('paciente', 'subido_por').order_by('-fecha_documento', '-created_at')
    solicitudes = SolicitudDocumento.objects.filter(paciente__in=pacientes).select_related('paciente', 'medico_solicitante', 'documento_asociado').order_by('-created_at')

    context = {
        'titulo_pagina': 'Documentos Médicos',
        'paciente': _paciente_dict(paciente) if paciente else None,
        'pacientes': pacientes,
        'documentos': documentos,
        'solicitudes': solicitudes,
    }
    return render(request, 'padres/documentos.html', context)


@login_required
def subir_documento_view(request, solicitud_id=None):
    tutor, paciente, redir = _get_tutor_or_redirect(request)
    if redir:
        return redir

    pacientes = tutor.pacientes.all()
    solicitud = None

    if solicitud_id:
        solicitud = get_object_or_404(SolicitudDocumento, id=solicitud_id, paciente__in=pacientes)
        paciente_inicial = solicitud.paciente
    else:
        paciente_inicial = paciente

    if request.method == 'POST':
        paciente_id = request.POST.get('paciente')
        tipo_documento = request.POST.get('tipo_documento')
        fecha_estudio = request.POST.get('fecha_estudio')
        descripcion = request.POST.get('descripcion', '').strip()
        archivo = request.FILES.get('archivo')

        try:
            paciente_seleccionado = pacientes.get(id=paciente_id)
        except (Paciente.DoesNotExist, ValueError):
            from django.contrib import messages as msg
            msg.error(request, 'Paciente seleccionado no válido.')
            return redirect('padres:documentos')

        if not archivo:
            from django.contrib import messages as msg
            msg.error(request, 'Debe seleccionar un archivo para subir.')
            return render(request, 'padres/subir_documento.html', {
                'titulo_pagina': 'Subir Documento',
                'paciente': _paciente_dict(paciente) if paciente else None,
                'pacientes': pacientes,
                'tipos': [choice for choice in DocumentoMedico.TipoDocumento.choices if choice[0] != 'LABORATORIO'],
                'solicitud': solicitud,
                'paciente_inicial': paciente_seleccionado,
            })

        doc = DocumentoMedico(
            paciente=paciente_seleccionado,
            subido_por=request.user,
            tipo_documento=tipo_documento,
            archivo=archivo,
            descripcion=descripcion,
            fecha_documento=fecha_estudio or timezone.now().date(),
            estado=DocumentoMedico.EstadoDocumento.PENDIENTE,
            visible_padre=True,
        )
        if solicitud:
            doc._notificaciones_skip_documento = True
        doc.save()

        if solicitud:
            solicitud.documento_asociado = doc
            solicitud.estado = SolicitudDocumento.EstadoSolicitud.SUBIDO
            solicitud.save()

        from django.contrib import messages as msg
        msg.success(request, 'Documento subido correctamente. El equipo médico ha sido notificado para su revisión.')
        return redirect('padres:documentos')

    context = {
        'titulo_pagina': 'Subir Documento',
        'paciente': _paciente_dict(paciente) if paciente else None,
        'pacientes': pacientes,
        'tipos': [choice for choice in DocumentoMedico.TipoDocumento.choices if choice[0] != 'LABORATORIO'],
        'solicitud': solicitud,
        'paciente_inicial': paciente_inicial,
    }
    return render(request, 'padres/subir_documento.html', context)


@login_required
def ver_documento_view(request, doc_id):
    tutor, paciente, redir = _get_tutor_or_redirect(request)
    is_staff = hasattr(request.user, 'rol') and request.user.rol in ['ADMIN', 'PERSONAL_FACCI', 'MEDICO', 'PEDIATRA', 'ONCOLOGO']
    
    if redir and not is_staff:
        return redir

    doc = get_object_or_404(DocumentoMedico, id=doc_id)
    
    if not is_staff:
        if not doc.visible_padre or not tutor.pacientes.filter(id=doc.paciente.id).exists():
            raise Http404("No autorizado para ver este documento.")

    file_path = doc.archivo.path
    if not os.path.exists(file_path):
        raise Http404("El archivo físico no se encuentra disponible.")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'

    as_attachment = request.GET.get('descargar') == '1'

    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
    if as_attachment:
        response['Content-Disposition'] = f'attachment; filename="{doc.nombre}"'
    else:
        response['Content-Disposition'] = f'inline; filename="{doc.nombre}"'

    return response


@login_required
def recursos_educativos_view(request):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return redirect('home')

    categoria = request.GET.get('categoria', '')
    categorias = RecursoEducativo.Categoria.choices

    qs = RecursoEducativo.objects.filter(activo=True)
    if categoria:
        qs = qs.filter(categoria=categoria)

    recursos = qs.order_by('orden', 'titulo')
    for recurso in recursos:
        recurso.imagen_presentacion = _recurso_imagen_url(recurso)

    return render(request, 'padres/recursos_educativos.html', {
        'titulo_pagina': 'Recursos para la Familia',
        'recursos': recursos,
        'categorias': categorias,
        'categoria_activa': categoria,
    })


@login_required
def detalle_recurso_view(request, slug):
    if not hasattr(request.user, 'rol') or request.user.rol != 'PADRE_TUTOR':
        return redirect('home')

    recurso = get_object_or_404(RecursoEducativo, slug=slug, activo=True)
    relacionados = (
        RecursoEducativo.objects
        .filter(activo=True, categoria=recurso.categoria)
        .exclude(pk=recurso.pk)
        .order_by('orden', 'titulo')[:3]
    )

    for relacionado in relacionados:
        relacionado.imagen_presentacion = _recurso_imagen_url(relacionado)

    return render(request, 'padres/recurso_detalle.html', {
        'titulo_pagina': recurso.titulo,
        'recurso': recurso,
        'relacionados': relacionados,
        'imagen_url': _recurso_imagen_url(recurso),
        'video_embed_url': _youtube_embed_url(recurso.video_url),
    })
