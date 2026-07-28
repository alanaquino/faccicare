from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse
from django.db import models, transaction
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
import os

from apps.core.decorators import solo_personal, requiere_acceso
from apps.pacientes.models import Paciente
from apps.auth_app.models import CustomUser
from .models import DocumentoMedico, SolicitudDocumento


@login_required
@solo_personal
def lista_view(request):
    tipo_filter = request.GET.get('tipo', '')
    estado_filter = request.GET.get('estado', '')
    search_query = request.GET.get('q', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    # Base queryset según rol
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        documentos = DocumentoMedico.objects.filter(
            Q(paciente__medico_asignado=request.user) | Q(paciente__creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        documentos = DocumentoMedico.objects.filter(
            paciente__referencias__especialista_destino=request.user
        ).distinct()
    else:
        documentos = DocumentoMedico.objects.all()

    documentos = documentos.select_related('paciente', 'subido_por')

    # Filtros
    if tipo_filter:
        documentos = documentos.filter(tipo_documento=tipo_filter)
    if estado_filter:
        documentos = documentos.filter(estado=estado_filter)
    if search_query:
        documentos = documentos.filter(
            Q(paciente__nombres__icontains=search_query) |
            Q(paciente__apellidos__icontains=search_query) |
            Q(descripcion__icontains=search_query)
        )
    if fecha_desde:
        documentos = documentos.filter(fecha_documento__gte=parse_date(fecha_desde))
    if fecha_hasta:
        documentos = documentos.filter(fecha_documento__lte=parse_date(fecha_hasta))

    documentos = documentos.order_by('-fecha_documento')

    # Paginación
    paginator = Paginator(documentos, 12)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    context = {
        'titulo_pagina': 'Documentos Médicos',
        'documentos': page_obj.object_list,
        'page_obj': page_obj,
        'total': paginator.count,
        'tipos_documento': DocumentoMedico.TipoDocumento.choices,
        'estados_documento': DocumentoMedico.EstadoDocumento.choices,
        'filtro_tipo': tipo_filter,
        'filtro_estado': estado_filter,
        'filtro_search': search_query,
        'filtro_fecha_desde': fecha_desde,
        'filtro_fecha_hasta': fecha_hasta,
    }
    return render(request, 'documentos/lista.html', context)


@login_required
@requiere_acceso('puede_subir_documentos')
def subir_view(request):
    if request.method == 'POST':
        return _procesar_subir_documento(request)

    # GET: mostrar formulario
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        pacientes = Paciente.objects.filter(
            Q(medico_asignado=request.user) | Q(creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        pacientes = Paciente.objects.filter(
            referencias__especialista_destino=request.user
        ).distinct()
    else:
        pacientes = Paciente.objects.all()

    paciente_preseleccionado = None
    paciente_id = request.GET.get('paciente')
    if paciente_id:
        paciente_preseleccionado = Paciente.objects.filter(pk=paciente_id).first()

    context = {
        'titulo_pagina': 'Subir Documento',
        'tipos_documento': DocumentoMedico.TipoDocumento.choices,
        'pacientes': pacientes.order_by('nombres', 'apellidos'),
        'paciente_preseleccionado': paciente_preseleccionado,
    }
    return render(request, 'documentos/subir.html', context)


def _procesar_subir_documento(request):
    try:
        paciente_id = request.POST.get('paciente')
        tipo_documento = request.POST.get('tipo_documento')
        fecha_documento = request.POST.get('fecha_documento')
        descripcion = request.POST.get('descripcion', '')
        archivo = request.FILES.get('archivo')
        visible_padre = request.POST.get('visible_padre') == 'on'

        if not all([paciente_id, tipo_documento, fecha_documento, archivo]):
            messages.error(request, 'Todos los campos son requeridos')
            return redirect('documentos:subir')

        paciente = get_object_or_404(Paciente, id=paciente_id)

        # Validar permisos
        if not _puede_subir_documento(request.user, paciente):
            messages.error(request, 'No tienes permisos para subir documentos de este paciente')
            return redirect('documentos:lista')

        # Validar archivo
        if archivo.size > 20 * 1024 * 1024:
            messages.error(request, 'El archivo no puede superar 20 MB')
            return redirect('documentos:subir')

        allowed_ext = ['pdf', 'jpg', 'jpeg', 'png', 'docx', 'xlsx']
        ext = archivo.name.split('.')[-1].lower()
        if ext not in allowed_ext:
            messages.error(request, f'Formato no permitido. Usar: {", ".join(allowed_ext)}')
            return redirect('documentos:subir')

        with transaction.atomic():
            doc = DocumentoMedico.objects.create(
                paciente=paciente,
                subido_por=request.user,
                tipo_documento=tipo_documento,
                fecha_documento=fecha_documento,
                descripcion=descripcion,
                archivo=archivo,
                visible_padre=visible_padre,
            )
            messages.success(request, f'Documento "{doc.nombre}" subido correctamente')

    except Exception as e:
        messages.error(request, f'Error al subir documento: {str(e)}')
        return redirect('documentos:subir')

    return redirect('documentos:lista')


@login_required
@solo_personal
def detalle_view(request, pk):
    documento = get_object_or_404(DocumentoMedico, id=pk)

    # Validar permisos
    if not _puede_ver_documento(request.user, documento):
        messages.error(request, 'No tienes permiso para ver este documento')
        return redirect('documentos:lista')

    context = {
        'titulo_pagina': 'Detalle de Documento',
        'documento': documento,
        'puede_modificar': _puede_modificar_documento(request.user, documento),
    }
    return render(request, 'documentos/detalle.html', context)


@login_required
@solo_personal
def descargar_view(request, pk):
    documento = get_object_or_404(DocumentoMedico, id=pk)

    if not _puede_ver_documento(request.user, documento):
        messages.error(request, 'No tienes permiso')
        return redirect('documentos:lista')

    try:
        return FileResponse(
            documento.archivo.open('rb'),
            as_attachment=True,
            filename=documento.nombre
        )
    except Exception as e:
        messages.error(request, f'Error al descargar: {str(e)}')
        return redirect('documentos:lista')


def vista_previa_view(request, pk):
    """Sirve el archivo inline (sin descarga forzada) para vista previa en navegador."""
    # No redirigir — el iframe no maneja redirects bien. Devolver 403/404 plano.
    if not request.user.is_authenticated:
        return HttpResponse('No autenticado', status=401)

    documento = get_object_or_404(DocumentoMedico, id=pk)

    if not _puede_ver_documento(request.user, documento):
        return HttpResponse('Acceso denegado', status=403)

    try:
        ext = documento.extension.lower()
        content_types = {
            'pdf':  'application/pdf',
            'jpg':  'image/jpeg',
            'jpeg': 'image/jpeg',
            'png':  'image/png',
            'gif':  'image/gif',
            'webp': 'image/webp',
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        f = documento.archivo.open('rb')
        response = FileResponse(f, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{documento.nombre}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Cache-Control'] = 'private, no-cache'
        return response
    except FileNotFoundError:
        return HttpResponse('Archivo no encontrado en el servidor', status=404)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)


@login_required
@requiere_acceso('puede_subir_documentos')
@require_POST
def eliminar_view(request, pk):
    documento = get_object_or_404(DocumentoMedico, id=pk)

    if not _puede_modificar_documento(request.user, documento):
        messages.error(request, 'No tienes permisos')
        return redirect('documentos:lista')

    try:
        if documento.archivo:
            documento.archivo.delete()
        documento.delete()
        messages.success(request, 'Documento eliminado correctamente')
    except Exception as e:
        messages.error(request, f'Error al eliminar: {str(e)}')

    return redirect('documentos:lista')


@login_required
@requiere_acceso('puede_subir_documentos')
@require_POST
def cambiar_estado_view(request, pk):
    documento = get_object_or_404(DocumentoMedico, id=pk)
    nuevo_estado = request.POST.get('estado')

    if not _puede_modificar_documento(request.user, documento):
        messages.error(request, 'No tienes permisos')
        return redirect('documentos:lista')

    if nuevo_estado not in dict(DocumentoMedico.EstadoDocumento.choices):
        messages.error(request, 'Estado inválido')
        return redirect('documentos:detalle', pk=pk)

    observaciones = request.POST.get('observaciones', '').strip()
    if nuevo_estado == DocumentoMedico.EstadoDocumento.CORRECCION and not observaciones:
        messages.error(request, 'Debe ingresar las observaciones antes de marcar que requiere corrección.')
        return redirect('documentos:detalle', pk=pk)

    documento.estado = nuevo_estado
    if observaciones:
        documento.descripcion = f"{documento.descripcion}\n[Observación de corrección]: {observaciones}".strip()
    documento.save(update_fields=['estado', 'descripcion', 'updated_at'])
    messages.success(request, 'Estado actualizado correctamente')

    return redirect('documentos:detalle', pk=pk)


@login_required
@requiere_acceso('puede_subir_documentos')
@require_POST
def cambiar_visibilidad_view(request, pk):
    documento = get_object_or_404(DocumentoMedico, id=pk)
    if not _puede_modificar_documento(request.user, documento):
        messages.error(request, 'No tienes permisos para cambiar la visibilidad.')
        return redirect('documentos:lista')

    documento.visible_padre = request.POST.get('visible_padre') == 'on'
    documento.save(update_fields=['visible_padre', 'updated_at'])
    estado = 'visible' if documento.visible_padre else 'oculto'
    messages.success(request, f'El documento ahora está {estado} en el Portal Padres.')
    return redirect('documentos:detalle', pk=pk)


# Solicitudes de documentos
@login_required
@solo_personal
def solicitudes_view(request):
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        solicitudes = SolicitudDocumento.objects.filter(
            Q(paciente__medico_asignado=request.user) |
            Q(paciente__creado_por=request.user) |
            Q(medico_solicitante=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        solicitudes = SolicitudDocumento.objects.filter(
            Q(paciente__referencias__especialista_destino=request.user) |
            Q(medico_solicitante=request.user)
        ).distinct()
    else:
        solicitudes = SolicitudDocumento.objects.all()

    solicitudes = solicitudes.select_related('paciente', 'medico_solicitante')
    estado_filter = request.GET.get('estado', '')

    if estado_filter:
        solicitudes = solicitudes.filter(estado=estado_filter)

    context = {
        'titulo_pagina': 'Solicitudes de Documentos',
        'solicitudes': solicitudes.order_by('-created_at'),
        'estados': SolicitudDocumento.EstadoSolicitud.choices,
        'filtro_estado': estado_filter,
    }
    return render(request, 'documentos/solicitudes.html', context)


def _puede_subir_documento(user, paciente):
    if user.rol == CustomUser.Rol.ADMIN:
        return True
    if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        return paciente.medico_asignado == user or paciente.creado_por == user
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return paciente.referencias.filter(especialista_destino=user).exists()
    return False


def _puede_ver_documento(user, documento):
    if user.rol in [CustomUser.Rol.ADMIN, CustomUser.Rol.PERSONAL_FACCI]:
        return True
    if _puede_subir_documento(user, documento.paciente):
        return True
    if documento.subido_por == user:
        return True
    return False


def _puede_modificar_documento(user, documento):
    if user.rol in [CustomUser.Rol.ADMIN, CustomUser.Rol.PERSONAL_FACCI]:
        return True
    if documento.subido_por == user:
        return True
    if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        return (documento.paciente.medico_asignado == user or
                documento.paciente.creado_por == user)
    return False
