from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.auth_app.models import CustomUser
from apps.core.decorators import requiere_acceso
from apps.pacientes.models import Paciente

from .models import CatalogoEstudio, CatalogoParametro, ResultadoLaboratorio, ValorResultado
from .plantillas import NOMBRES_EXAMEN_DEFAULT, PLANTILLAS_EXAMEN


def _parse_decimal(valor_str):
    if not valor_str or not str(valor_str).strip():
        return None
    try:
        return Decimal(str(valor_str).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


def _getlist_any(post_data, *names):
    for name in names:
        values = post_data.getlist(name)
        if values:
            return values
    return []


def _decimal_to_text(valor):
    if valor is None:
        return ''
    return format(valor.normalize(), 'f')


def _serializar_parametro_catalogo(parametro):
    return {
        'id': str(parametro.pk),
        'estudio_id': str(parametro.estudio_id),
        'estudio_nombre': parametro.estudio.nombre,
        'nombre': parametro.nombre,
        'unidad': parametro.unidad,
        'referencia_minima': _decimal_to_text(parametro.referencia_minima),
        'referencia_maxima': _decimal_to_text(parametro.referencia_maxima),
        'referencia_texto': parametro.referencia_texto,
        'requiere_comentario': parametro.requiere_comentario,
        'comentario_sugerido': parametro.comentario_sugerido,
        'alerta_sistema': parametro.alerta_sistema,
        'alerta_critica': parametro.alerta_critica,
        'tipo_valor': parametro.tipo_valor,
    }


def _serializar_estudio(estudio):
    return {
        'id': str(estudio.pk),
        'nombre': estudio.nombre,
        'categoria': estudio.categoria,
    }


def _form_data_from_post(post_data):
    return {
        'paciente': post_data.get('paciente', ''),
        'tipo': post_data.get('tipo', ''),
        'nombre_examen': post_data.get('nombre_examen', ''),
        'fecha_muestra': post_data.get('fecha_muestra', ''),
        'fecha_resultado': post_data.get('fecha_resultado', ''),
        'resultado_narrativo': post_data.get('resultado_narrativo', ''),
        'observaciones': post_data.get('observaciones', ''),
    }


def _serializar_valores_iniciales(valores):
    serializados = []
    for valor in valores:
        parametro_catalogo = valor.get('parametro_catalogo')
        parametro_catalogo_id = valor.get('parametro_catalogo_id', '')
        if not parametro_catalogo_id and hasattr(parametro_catalogo, 'pk'):
            parametro_catalogo_id = str(parametro_catalogo.pk)
        elif not parametro_catalogo_id:
            parametro_catalogo_id = parametro_catalogo or ''

        serializados.append(
            {
                'estudio_catalogo': valor.get('estudio_catalogo', ''),
                'parametro_catalogo': parametro_catalogo_id,
                'parametro': valor.get('parametro', ''),
                'valor': valor.get('valor', ''),
                'unidad': valor.get('unidad', ''),
                'ref_min': valor.get('ref_min', ''),
                'ref_max': valor.get('ref_max', ''),
                'referencia_texto': valor.get('referencia_texto', ''),
                'comentario': valor.get('comentario', ''),
            }
        )
    return serializados


def _leer_valores_post(post_data):
    catalogo_ids = _getlist_any(post_data, 'parametro_catalogo[]', 'parametro_catalogo')
    parametros = _getlist_any(post_data, 'parametro[]', 'parametro')
    valores = _getlist_any(post_data, 'valor[]', 'valor')
    unidades = _getlist_any(post_data, 'unidad[]', 'unidad')
    refs_min = _getlist_any(post_data, 'referencia_minima[]', 'ref_min[]', 'ref_min')
    refs_max = _getlist_any(post_data, 'referencia_maxima[]', 'ref_max[]', 'ref_max')
    refs_texto = _getlist_any(post_data, 'referencia_texto[]', 'referencia_texto')
    comentarios = _getlist_any(post_data, 'comentario_valor[]', 'comentario_valor')

    catalogo_por_id = {}
    catalogo_ids_validos = [pk for pk in catalogo_ids if pk]
    if catalogo_ids_validos:
        catalogo_por_id = {
            str(parametro.pk): parametro
            for parametro in CatalogoParametro.objects.select_related('estudio').filter(
                pk__in=catalogo_ids_validos,
                activo=True,
                estudio__activo=True,
            )
        }

    total = max(
        len(catalogo_ids), len(parametros), len(valores), len(unidades),
        len(refs_min), len(refs_max), len(refs_texto), len(comentarios), 0,
    )
    filas = []
    errores = []

    for i in range(total):
        catalogo_id = catalogo_ids[i].strip() if i < len(catalogo_ids) else ''
        parametro_catalogo = catalogo_por_id.get(catalogo_id) if catalogo_id else None
        comentario = comentarios[i].strip() if i < len(comentarios) else ''
        fila = {
            'parametro_catalogo': catalogo_id,
            'parametro_catalogo_id': catalogo_id,
            'estudio_catalogo': str(parametro_catalogo.estudio_id) if parametro_catalogo else '',
            'parametro': parametros[i].strip() if i < len(parametros) else '',
            'valor': valores[i].strip() if i < len(valores) else '',
            'unidad': unidades[i].strip() if i < len(unidades) else '',
            'ref_min': refs_min[i].strip() if i < len(refs_min) else '',
            'ref_max': refs_max[i].strip() if i < len(refs_max) else '',
            'referencia_texto': refs_texto[i].strip() if i < len(refs_texto) else '',
            'comentario': comentario,
        }

        if not any(fila.values()):
            continue

        if catalogo_id and not parametro_catalogo:
            errores.append(f'Fila {i + 1}: el parametro seleccionado no existe en el catalogo activo.')
            filas.append(fila)
            continue

        if parametro_catalogo:
            fila['parametro_catalogo'] = parametro_catalogo
            fila['parametro_catalogo_id'] = str(parametro_catalogo.pk)
            fila['estudio_catalogo'] = str(parametro_catalogo.estudio_id)
            fila['parametro'] = parametro_catalogo.nombre
            fila['unidad'] = parametro_catalogo.unidad
            fila['ref_min'] = _decimal_to_text(parametro_catalogo.referencia_minima)
            fila['ref_max'] = _decimal_to_text(parametro_catalogo.referencia_maxima)
            fila['referencia_texto'] = parametro_catalogo.referencia_texto

        if not fila['parametro']:
            errores.append(f'Fila {i + 1}: ingrese el nombre del parametro.')
            filas.append(fila)
            continue

        if not fila['valor']:
            errores.append(f'Fila {i + 1}: ingrese el valor medido de {fila["parametro"]}.')

        if parametro_catalogo and parametro_catalogo.requiere_comentario and not fila['comentario']:
            errores.append(f'Fila {i + 1}: {fila["parametro"]} requiere comentario medico.')

        ref_min = _parse_decimal(fila['ref_min'])
        ref_max = _parse_decimal(fila['ref_max'])

        if fila['ref_min'] and ref_min is None:
            errores.append(f'Fila {i + 1}: la referencia minima no es numerica.')
        if fila['ref_max'] and ref_max is None:
            errores.append(f'Fila {i + 1}: la referencia maxima no es numerica.')
        if ref_min is not None and ref_max is not None and ref_min > ref_max:
            errores.append(f'Fila {i + 1}: la referencia minima no puede ser mayor que la maxima.')

        fila['referencia_min'] = ref_min
        fila['referencia_max'] = ref_max
        fila['orden'] = i
        filas.append(fila)

    return filas, errores


def _scope_pacientes(usuario):
    if usuario.rol in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
        return Paciente.objects.filter(medico_asignado=usuario)
    if usuario.rol == CustomUser.Rol.ONCOLOGO:
        return Paciente.objects.filter(
            referencias__especialista_destino=usuario
        ).distinct()
    return Paciente.objects.all()


def _notificar_critico(resultado):
    try:
        from apps.notificaciones.models import Notificacion
        from apps.notificaciones.services import crear_notificacion
        from django.urls import reverse
        url = reverse('laboratorio:detalle', kwargs={'pk': str(resultado.pk)})
        if resultado.solicitado_por:
            crear_notificacion(
                usuario=resultado.solicitado_por,
                tipo=Notificacion.TipoNotificacion.ALERTA_CLINICA,
                modulo='Laboratorio',
                prioridad=Notificacion.Prioridad.CRITICA,
                titulo=f'Valores críticos — {resultado.paciente.nombre_completo}',
                mensaje=(
                    f'{resultado.nombre_examen} del {resultado.fecha_muestra:%d/%m/%Y} '
                    'tiene valores fuera del rango crítico. Revisión urgente.'
                ),
                accion_url=url,
                accion_texto='Ver resultado',
                objeto=resultado,
                icono_nombre='emergency',
                clave_dedupe=f'lab:{resultado.pk}:critico:{resultado.solicitado_por.pk}',
            )
    except Exception:
        pass


def _crear_alertas_valores_laboratorio(resultado):
    try:
        from apps.dashboard.models import AlertaClinica
    except Exception:
        return

    banderas_alerta = [
        ValorResultado.Bandera.BAJO,
        ValorResultado.Bandera.ALTO,
        ValorResultado.Bandera.CRITICO_BAJO,
        ValorResultado.Bandera.CRITICO_ALTO,
    ]
    valores = resultado.valores.filter(bandera__in=banderas_alerta)

    for valor in valores:
        parametro_lower = valor.parametro.lower()
        es_critico = (
            valor.bandera in [ValorResultado.Bandera.CRITICO_BAJO, ValorResultado.Bandera.CRITICO_ALTO]
            or 'critico' in parametro_lower
            or 'crítico' in parametro_lower
        )
        prioridad = AlertaClinica.Prioridad.CRITICA if es_critico else AlertaClinica.Prioridad.ALTA
        tipo_alerta = (
            AlertaClinica.TipoAlerta.CASO_CRITICO
            if es_critico
            else AlertaClinica.TipoAlerta.ALTA_PRIORIDAD_SIN_REVISION
        )
        unidad = f' {valor.unidad}' if valor.unidad else ''
        rango = 'sin referencia'
        if valor.referencia_min is not None and valor.referencia_max is not None:
            rango = f'{valor.referencia_min} - {valor.referencia_max}'
        elif valor.referencia_min is not None:
            rango = f'>= {valor.referencia_min}'
        elif valor.referencia_max is not None:
            rango = f'<= {valor.referencia_max}'

        AlertaClinica.objects.update_or_create(
            clave_dedupe=f'lab:{resultado.pk}:valor:{valor.pk}',
            defaults={
                'paciente': resultado.paciente,
                'tipo_alerta': tipo_alerta,
                'prioridad': prioridad,
                'titulo': 'Valor critico de laboratorio' if es_critico else 'Valor alterado de laboratorio',
                'descripcion': (
                    f'{resultado.nombre_examen} ({resultado.fecha_muestra:%d/%m/%Y}) registra '
                    f'{valor.parametro}: {valor.valor}{unidad}. Rango de referencia: {rango}. '
                    f'Estado: {valor.get_bandera_display()}.'
                ),
                'estado': AlertaClinica.Estado.PENDIENTE,
                'fecha_limite': timezone.now() if es_critico else timezone.now() + timedelta(days=1),
            },
        )


@login_required
@requiere_acceso('puede_ver_laboratorio')
def lista_view(request):
    resultados = ResultadoLaboratorio.objects.select_related('paciente', 'solicitado_por')
    if request.user.rol not in [CustomUser.Rol.ADMIN, CustomUser.Rol.PERSONAL_FACCI]:
        pacientes = _scope_pacientes(request.user)
        resultados = resultados.filter(paciente__in=pacientes)

    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    paciente_pk = request.GET.get('paciente', '')

    if q:
        resultados = resultados.filter(
            Q(nombre_examen__icontains=q) |
            Q(paciente__nombres__icontains=q) |
            Q(paciente__apellidos__icontains=q)
        )
    if tipo and tipo in ResultadoLaboratorio.TipoExamen.values:
        resultados = resultados.filter(tipo=tipo)
    if estado and estado in ResultadoLaboratorio.Estado.values:
        resultados = resultados.filter(estado=estado)
    if paciente_pk:
        resultados = resultados.filter(paciente__pk=paciente_pk)

    resultados = resultados.distinct().order_by('-fecha_muestra', '-created_at')
    total = resultados.count()

    context = {
        'resultados': resultados,
        'total': total,
        'criticos': resultados.filter(hay_valores_criticos=True).count(),
        'pendientes_revision': resultados.filter(
            estado__in=[ResultadoLaboratorio.Estado.RECIBIDO, ResultadoLaboratorio.Estado.CRITICO]
        ).count(),
        'tipos_examen': ResultadoLaboratorio.TipoExamen.choices,
        'estados': ResultadoLaboratorio.Estado.choices,
        'q': q,
        'tipo_actual': tipo,
        'estado_actual': estado,
    }
    return render(request, 'laboratorio/lista.html', context)


@login_required
@requiere_acceso('puede_ver_laboratorio')
def crear_view(request, paciente_pk=None):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    paciente_preseleccionado = None
    if paciente_pk:
        paciente_preseleccionado = get_object_or_404(Paciente, pk=paciente_pk)

    if request.method == 'POST':
        paciente_id = request.POST.get('paciente', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        nombre_examen = request.POST.get('nombre_examen', '').strip()
        fecha_muestra_str = request.POST.get('fecha_muestra', '').strip()
        fecha_resultado_str = request.POST.get('fecha_resultado', '').strip()
        resultado_narrativo = request.POST.get('resultado_narrativo', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        archivo = request.FILES.get('archivo')
        valores_form, valores_errors = _leer_valores_post(request.POST)

        errors = []
        paciente = None
        fecha_muestra = None

        if not paciente_id:
            errors.append('Seleccione un paciente.')
        else:
            try:
                paciente = Paciente.objects.get(pk=paciente_id)
            except Paciente.DoesNotExist:
                errors.append('Paciente no encontrado.')

        if not tipo or tipo not in ResultadoLaboratorio.TipoExamen.values:
            errors.append('Seleccione un tipo de examen válido.')

        if not nombre_examen:
            errors.append('Ingrese el nombre del examen.')

        if not fecha_muestra_str:
            errors.append('Ingrese la fecha de muestra.')
        else:
            try:
                fecha_muestra = date.fromisoformat(fecha_muestra_str)
            except ValueError:
                errors.append('Fecha de muestra inválida.')

        fecha_resultado = None
        if fecha_resultado_str:
            try:
                fecha_resultado = date.fromisoformat(fecha_resultado_str)
            except ValueError:
                pass

        errors.extend(valores_errors)

        if errors:
            for err in errors:
                messages.error(request, err)
            return _render_crear(
                request,
                paciente_preseleccionado,
                form_data=_form_data_from_post(request.POST),
                valores_iniciales=_serializar_valores_iniciales(valores_form),
            )

        with transaction.atomic():
            resultado = ResultadoLaboratorio.objects.create(
                paciente=paciente,
                solicitado_por=request.user,
                tipo=tipo,
                nombre_examen=nombre_examen,
                fecha_muestra=fecha_muestra,
                fecha_resultado=fecha_resultado,
                resultado_narrativo=resultado_narrativo,
                observaciones=observaciones,
                archivo=archivo,
                estado=ResultadoLaboratorio.Estado.RECIBIDO,
            )

            for valor in valores_form:
                parametro_catalogo = valor.get('parametro_catalogo')
                if not hasattr(parametro_catalogo, 'pk'):
                    parametro_catalogo = None
                ValorResultado.objects.create(
                    resultado=resultado,
                    parametro_catalogo=parametro_catalogo,
                    parametro=valor['parametro'],
                    valor=valor['valor'],
                    unidad=valor['unidad'],
                    referencia_min=valor.get('referencia_min'),
                    referencia_max=valor.get('referencia_max'),
                    referencia_texto=valor.get('referencia_texto', ''),
                    comentario=valor.get('comentario', ''),
                    orden=valor.get('orden', 0),
                )

            resultado.actualizar_criticos()

        if resultado.hay_valores_criticos:
            _notificar_critico(resultado)
        _crear_alertas_valores_laboratorio(resultado)

        messages.success(request, f'Resultado {resultado.codigo} registrado correctamente.')
        return redirect('laboratorio:detalle', pk=str(resultado.pk))

    return _render_crear(request, paciente_preseleccionado)


def _render_crear(request, paciente_preseleccionado, form_data=None, valores_iniciales=None):
    pacientes = _scope_pacientes(request.user).order_by('apellidos', 'nombres')
    catalogo_estudios = CatalogoEstudio.objects.filter(activo=True).order_by('categoria', 'nombre')
    form_data = form_data or {}
    if paciente_preseleccionado and not form_data.get('paciente'):
        form_data['paciente'] = str(paciente_preseleccionado.pk)
    context = {
        'pacientes': pacientes,
        'catalogo_estudios': catalogo_estudios,
        'catalogo_estudios_json': [_serializar_estudio(estudio) for estudio in catalogo_estudios],
        'tipos_examen': ResultadoLaboratorio.TipoExamen.choices,
        'plantillas': PLANTILLAS_EXAMEN,
        'nombres_default': NOMBRES_EXAMEN_DEFAULT,
        'valores_iniciales': valores_iniciales or [],
        'form_data': form_data,
        'paciente_preseleccionado': paciente_preseleccionado,
        'hoy': timezone.now().date().isoformat(),
    }
    return render(request, 'laboratorio/crear.html', context)


@login_required
@requiere_acceso('puede_ver_laboratorio')
def catalogo_parametros_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return JsonResponse({'parametros': []}, status=403)

    estudio_id = request.GET.get('estudio_id', '').strip()
    parametros = CatalogoParametro.objects.select_related('estudio').filter(
        activo=True,
        estudio__activo=True,
    )
    if estudio_id:
        parametros = parametros.filter(estudio_id=estudio_id)
    parametros = parametros.order_by('orden', 'nombre')
    return JsonResponse({'parametros': [_serializar_parametro_catalogo(p) for p in parametros]})


@login_required
@requiere_acceso('puede_ver_laboratorio')
def catalogo_parametro_view(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return JsonResponse({'detail': 'No autorizado.'}, status=403)

    parametro = get_object_or_404(
        CatalogoParametro.objects.select_related('estudio'),
        pk=pk,
        activo=True,
        estudio__activo=True,
    )
    return JsonResponse(_serializar_parametro_catalogo(parametro))


@login_required
@requiere_acceso('puede_ver_laboratorio')
def detalle_view(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    resultado = get_object_or_404(
        ResultadoLaboratorio.objects.select_related('paciente', 'solicitado_por', 'revisado_por'),
        pk=pk,
    )
    valores = resultado.valores.select_related('parametro_catalogo__estudio').all()
    n_criticos = valores.filter(
        bandera__in=[ValorResultado.Bandera.CRITICO_BAJO, ValorResultado.Bandera.CRITICO_ALTO]
    ).count()
    n_alterados = valores.filter(
        bandera__in=[ValorResultado.Bandera.BAJO, ValorResultado.Bandera.ALTO]
    ).count()

    context = {
        'resultado': resultado,
        'valores': valores,
        'n_criticos': n_criticos,
        'n_alterados': n_alterados,
        'puede_revisar': (
            resultado.estado != ResultadoLaboratorio.Estado.REVISADO and
            request.user.rol in [
                CustomUser.Rol.ADMIN, CustomUser.Rol.MEDICO,
                CustomUser.Rol.PEDIATRA, CustomUser.Rol.ONCOLOGO,
            ]
        ),
    }
    return render(request, 'laboratorio/detalle.html', context)


@login_required
@requiere_acceso('puede_ver_laboratorio')
def marcar_revisado_view(request, pk):
    if request.method != 'POST':
        return redirect('laboratorio:detalle', pk=pk)
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    resultado = get_object_or_404(ResultadoLaboratorio, pk=pk)
    if resultado.estado != ResultadoLaboratorio.Estado.REVISADO:
        resultado.estado = ResultadoLaboratorio.Estado.REVISADO
        resultado.revisado_por = request.user
        resultado.save(update_fields=['estado', 'revisado_por', 'updated_at'])
        messages.success(request, 'Resultado marcado como revisado.')
    return redirect('laboratorio:detalle', pk=str(pk))
