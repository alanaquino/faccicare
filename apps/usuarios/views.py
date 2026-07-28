from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.auth_app.models import CustomUser
from apps.core.audit import registrar_actividad
from apps.core.decorators import solo_personal, roles_requeridos
from apps.core.models import CentroSalud, LogActividad
from apps.padres.models import PadreTutor

from .forms import AdminUserEditForm, ParentProfileAdminForm


ROLES_SISTEMA = [
    {
        'valor': 'ADMIN',
        'nombre': 'Administrador',
        'descripcion': 'Acceso total al sistema. Gestión de usuarios, configuración y todos los reportes.',
        'color': 'error', 'icono': 'admin_panel_settings',
        'permisos': ['Gestión de usuarios', 'Configuración del sistema', 'Todos los reportes', 'Acceso a todos los módulos'],
    },
    {
        'valor': 'MEDICO',
        'nombre': 'Médico General (Primer Nivel)',
        'descripcion': 'Médico de UNAP o clínica. Registra pacientes, realiza cribado y crea referimientos.',
        'color': 'primary', 'icono': 'stethoscope',
        'permisos': ['Registro de pacientes', 'Cribado FACCI', 'Crear referencias al Pediatra', 'Citas', 'Documentos'],
    },
    {
        'valor': 'PEDIATRA',
        'nombre': 'Pediatra (Segundo Nivel)',
        'descripcion': 'Recibe referencias del primer nivel, evalúa y refiere al oncólogo si hay sospecha confirmada.',
        'color': 'primary', 'icono': 'pediatrics',
        'permisos': ['Registro de pacientes', 'Cribado FACCI', 'Referencias (recibir y enviar)', 'Seguimiento clínico', 'Laboratorio', 'Documentos', 'Reportes propios'],
    },
    {
        'valor': 'ONCOLOGO',
        'nombre': 'Oncólogo Pediátrico (Tercer Nivel)',
        'descripcion': 'Recibe referencias del pediatra. Diagnóstica, confirma y gestiona el tratamiento oncológico.',
        'color': 'secondary', 'icono': 'local_hospital',
        'permisos': ['Ver referencias recibidas', 'Casos clínicos', 'Seguimiento oncológico', 'Laboratorio', 'Documentos', 'Reportes propios'],
    },
    {
        'valor': 'PERSONAL_FACCI',
        'nombre': 'Coordinador FACCI',
        'descripcion': 'Coordinación administrativa y logística de FACCI. Gestiona recursos, reportes al MSP y Casa FACCI.',
        'color': 'tertiary', 'icono': 'badge',
        'permisos': ['Ver pacientes', 'Citas', 'Referencias (lectura)', 'Casa FACCI', 'Reportes PENCI-RD', 'Documentos'],
    },
    {
        'valor': 'TRABAJADORA_SOCIAL',
        'nombre': 'Trabajo Social / Psicología',
        'descripcion': 'Realiza evaluaciones psicosociales, gestiona alojamiento en Casa FACCI y apoyo familiar.',
        'color': 'tertiary', 'icono': 'social_work',
        'permisos': ['Ver pacientes', 'Evaluación psicosocial', 'Casa FACCI', 'Citas', 'Documentos sociales', 'Mensajes'],
    },
    {
        'valor': 'ENFERMERA',
        'nombre': 'Enfermera / Técnico de Salud',
        'descripcion': 'Registra signos vitales, peso/talla y toma de muestras. Apoya el seguimiento clínico.',
        'color': 'primary', 'icono': 'medical_services',
        'permisos': ['Ver pacientes', 'Seguimiento clínico (signos vitales)', 'Laboratorio', 'Citas', 'Documentos'],
    },
    {
        'valor': 'PADRE_TUTOR',
        'nombre': 'Padre / Tutor',
        'descripcion': 'Acceso exclusivo al portal de padres para seguir el estado de su hijo.',
        'color': 'outline', 'icono': 'family_restroom',
        'permisos': ['Portal de padres', 'Reporte de síntomas', 'Consultar indicaciones'],
    },
]

@login_required
@roles_requeridos('ADMIN')
def gestion_view(request):
    # Los padres/tutores se gestionan desde el expediente del paciente y su
    # portal. Esta pantalla corresponde exclusivamente a cuentas del sistema.
    usuarios_base = CustomUser.objects.exclude(rol=CustomUser.Rol.PADRE_TUTOR)
    roles_gestion = [choice for choice in CustomUser.Rol.choices if choice[0] != CustomUser.Rol.PADRE_TUTOR]
    usuarios = usuarios_base
    search_query = request.GET.get('q', '').strip()
    rol_filtro = request.GET.get('rol', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    if search_query:
        usuarios = usuarios.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(telefono__icontains=search_query) |
            Q(cedula__icontains=search_query) |
            Q(especialidad__icontains=search_query) |
            Q(centro_medico__nombre__icontains=search_query)
        )
    if rol_filtro in CustomUser.Rol.values:
        usuarios = usuarios.filter(rol=rol_filtro)
    if estado_filtro == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        usuarios = usuarios.filter(is_active=False)
    activos = usuarios.filter(is_active=True).count()
    roles_stats = [
        {
            'value': value,
            'label': label,
            'count': usuarios_base.filter(rol=value).count(),
        }
        for value, label in roles_gestion
    ]
    
    context = {
        'titulo_pagina': 'Gestión de Usuarios',
        'usuarios': usuarios.order_by('first_name', 'last_name', 'username'),
        'total': usuarios.count(),
        'activos': activos,
        'roles': roles_gestion,
        'roles_stats': roles_stats,
        'filtros': {
            'q': search_query,
            'rol': rol_filtro,
            'estado': estado_filtro,
        },
    }
    return render(request, 'usuarios/gestion.html', context)

@login_required
@roles_requeridos('ADMIN')
def nuevo_usuario_view(request):
    """CU-03: Registrar nuevo usuario en el sistema."""
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        rol        = request.POST.get('rol', CustomUser.Rol.MEDICO)
        password   = request.POST.get('password', '')
        cedula     = request.POST.get('cedula', '').strip() or None
        especialidad  = request.POST.get('especialidad', '').strip()
        centro_medico_id = request.POST.get('centro_medico', '').strip() or None
        centro_medico = CentroSalud.objects.filter(pk=centro_medico_id).first() if centro_medico_id else None

        errors = []
        if not username:
            errors.append('El nombre de usuario es requerido.')
        elif CustomUser.objects.filter(username__iexact=username).exists():
            errors.append(f'El usuario "{username}" ya existe.')
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            errors.append('El correo electrónico ya está registrado.')
        if not first_name:
            errors.append('El nombre es requerido.')
        if not password or len(password) < 8:
            errors.append('La contraseña debe tener al menos 8 caracteres.')
        if rol not in CustomUser.Rol.values:
            errors.append('Rol inválido.')
        if cedula and CustomUser.objects.filter(cedula=cedula).exists():
            errors.append(f'La cédula {cedula} ya está registrada.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'usuarios/nuevo.html', {
                'titulo_pagina': 'Nuevo Usuario',
                'roles': CustomUser.Rol.choices,
                'centros': CentroSalud.objects.filter(activo=True).order_by('nombre'),
                'form': request.POST,
            })

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            rol=rol,
            cedula=cedula,
            especialidad=especialidad,
            centro_medico=centro_medico,
        )
        messages.success(request, f'Usuario {user.get_full_name() or user.username} creado correctamente.')
        return redirect('usuarios:gestion')

    return render(request, 'usuarios/nuevo.html', {
        'titulo_pagina': 'Nuevo Usuario',
        'roles': CustomUser.Rol.choices,
        'centros': CentroSalud.objects.filter(activo=True).order_by('nombre'),
        'form': {},
    })


@login_required
@roles_requeridos('ADMIN')
def editar_usuario_view(request, pk):
    """CU-04: editar la ficha completa de cualquier usuario."""
    usuario = get_object_or_404(CustomUser, pk=pk)
    perfil_padre = PadreTutor.objects.filter(usuario=usuario).first()
    rol_enviado = request.POST.get('rol', usuario.rol)
    requiere_perfil_padre = rol_enviado == CustomUser.Rol.PADRE_TUTOR

    form = AdminUserEditForm(
        request.POST or None,
        request.FILES or None,
        instance=usuario,
        actor=request.user,
    )
    parent_form = ParentProfileAdminForm(
        request.POST or None,
        instance=perfil_padre,
    )

    if request.method == 'POST':
        form_valido = form.is_valid()
        perfil_valido = parent_form.is_valid() if requiere_perfil_padre else True
        if form_valido and perfil_valido:
            campos_modificados = [
                'contraseña' if campo in ('password1', 'password2') else campo
                for campo in form.changed_data
                if campo != 'password2'
            ]
            if requiere_perfil_padre:
                campos_modificados.extend(
                    f'perfil_padre.{campo}' for campo in parent_form.changed_data
                )

            with transaction.atomic():
                usuario = form.save()
                if requiere_perfil_padre:
                    perfil_padre = parent_form.save(commit=False)
                    perfil_padre.usuario = usuario
                    perfil_padre.save()

                registrar_actividad(
                    usuario=request.user,
                    request=request,
                    accion='Editar usuario',
                    tipo_accion=LogActividad.TipoAccion.EDICION,
                    modelo='CustomUser',
                    modulo='Usuarios',
                    objeto_id=usuario.pk,
                    objeto_repr=usuario.nombre_completo,
                    descripcion=(
                        f'Ficha de {usuario.username} actualizada por '
                        f'{request.user.username}. Campos: '
                        f'{", ".join(campos_modificados) or "sin cambios"}.'
                    ),
                    dedupe_seconds=0,
                )

            messages.success(
                request,
                f'Usuario {usuario.nombre_completo} actualizado correctamente.',
            )
            return redirect('usuarios:gestion')

    return render(request, 'usuarios/editar.html', {
        'titulo_pagina': f'Editar usuario: {usuario.nombre_completo}',
        'usuario_editado': usuario,
        'form': form,
        'parent_form': parent_form,
        'requiere_perfil_padre': requiere_perfil_padre,
    })


@login_required
@roles_requeridos('ADMIN')
@require_POST
def toggle_usuario_view(request, pk):
    """CU-06: Activar o desactivar un usuario."""
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario == request.user:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
        return redirect('usuarios:gestion')
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    estado = 'activado' if usuario.is_active else 'desactivado'
    messages.success(request, f'Usuario {usuario.get_full_name() or usuario.username} {estado} correctamente.')
    return redirect('usuarios:gestion')


@login_required
@roles_requeridos('ADMIN')
def roles_view(request):
    context = {
        'titulo_pagina': 'Gestión de Roles',
        'roles': ROLES_SISTEMA,
    }
    return render(request, 'usuarios/roles.html', context)

@login_required
@roles_requeridos('ADMIN')
def configuracion_view(request):
    context = {
        'titulo_pagina': 'Configuración del Sistema',
        'config': {
            'nombre_sistema': 'FACCI Care',
            'version': '2.1.0',
            'pais': 'República Dominicana',
            'idioma': 'Español',
            'zona_horaria': 'America/Santo_Domingo (UTC-4)',
            'notificaciones_email': True,
            'notificaciones_sms': True,
            'backup_automatico': True,
            'frecuencia_backup': 'Diario (2:00 AM)',
        },
    }
    return render(request, 'usuarios/configuracion.html', context)

@login_required
@solo_personal
def perfil_view(request):
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'editar_perfil':
            user.first_name = request.POST.get('first_name', user.first_name).strip()
            user.last_name = request.POST.get('last_name', user.last_name).strip()
            user.email = request.POST.get('email', user.email).strip()
            user.especialidad = request.POST.get('especialidad', user.especialidad).strip()
            centro_id = request.POST.get('centro_medico', '').strip() or None
            user.centro_medico = CentroSalud.objects.filter(pk=centro_id).first() if centro_id else None
            if 'foto_perfil' in request.FILES:
                user.foto_perfil = request.FILES['foto_perfil']
            sms_activo = request.POST.get('notif_sms') == 'on'
            if sms_activo:
                user.telefono = request.POST.get('telefono', user.telefono).strip()
            user.save()
            messages.success(request, 'Perfil actualizado correctamente.')
        elif action == 'cambiar_password':
            from django.contrib.auth import update_session_auth_hash
            old = request.POST.get('old_password', '')
            new1 = request.POST.get('new_password1', '')
            new2 = request.POST.get('new_password2', '')
            if not user.check_password(old):
                messages.error(request, 'La contraseña actual es incorrecta.')
            elif new1 != new2:
                messages.error(request, 'Las contraseñas nuevas no coinciden.')
            elif len(new1) < 8:
                messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            else:
                user.set_password(new1)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada correctamente.')
        return redirect('usuarios:perfil')

    actividad_reciente = (
        LogActividad.objects
        .filter(usuario=user)
        .exclude(tipo_accion__in=[LogActividad.TipoAccion.LOGIN, LogActividad.TipoAccion.LOGOUT])
        .order_by('-fecha')[:15]
    )

    context = {
        'titulo_pagina': 'Mi Perfil',
        'user': user,
        'actividad_reciente': actividad_reciente,
        'centros': CentroSalud.objects.filter(activo=True).order_by('nombre'),
    }
    return render(request, 'usuarios/perfil.html', context)
