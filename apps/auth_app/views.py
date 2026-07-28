from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import redirect, render


def login_view(request):
    """Login administrativo y medico — acepta username o email."""
    if request.user.is_authenticated:
        return redirect(request.GET.get('next') or 'home')

    if request.method == 'POST':
        credential = (request.POST.get('username') or '').strip()
        password   = request.POST.get('password', '')

        # Intentar autenticar directamente con el valor ingresado (username)
        user = authenticate(request, username=credential, password=password)

        # Si falla y parece un email, buscar el username real y reintentar
        if user is None and '@' in credential:
            User = get_user_model()
            try:
                user_obj = User.objects.get(email__iexact=credential)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            return redirect(request.POST.get('next') or request.GET.get('next') or 'home')

        # Django rechaza las cuentas inactivas durante authenticate(). Detectar
        # ese caso por separado permite mostrar el mensaje definido en CU-01.
        User = get_user_model()
        lookup = {'email__iexact': credential} if '@' in credential else {'username__iexact': credential}
        try:
            inactive_user = User.objects.get(**lookup)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            inactive_user = None
        if (
            inactive_user is not None
            and not inactive_user.is_active
            and inactive_user.check_password(password)
        ):
            messages.error(request, 'La cuenta está deshabilitada. Contacte al administrador.')
            return render(
                request,
                'auth_app/login.html',
                {'titulo': 'Iniciar Sesion', 'next': request.GET.get('next', '')},
            )

        messages.error(request, 'Credenciales incorrectas. Verifica el usuario o correo y la contraseña.')

    return render(
        request,
        'auth_app/login.html',
        {
            'titulo': 'Iniciar Sesion',
            'next': request.GET.get('next', ''),
        },
    )


def logout_view(request):
    was_padre = False
    if request.user.is_authenticated and hasattr(request.user, 'rol') and request.user.rol == 'PADRE_TUTOR':
        was_padre = True
        
    logout(request)
    
    if was_padre:
        return redirect('auth_app:login_padres')
    return redirect('auth_app:login')


def login_padres_view(request):
    """Login del portal de padres/tutores."""
    User = get_user_model()
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'rol') and request.user.rol == 'PADRE_TUTOR':
            return redirect('padres:estado')
        else:
            return redirect('home')

    if request.method == 'POST':
        codigo = (request.POST.get('codigo') or '').strip()
        pin = request.POST.get('pin', '')

        user_obj = None

        # 1. Intentar buscar por correo directo en CustomUser con rol PADRE_TUTOR
        if '@' in codigo:
            try:
                user_obj = User.objects.get(email__iexact=codigo, rol='PADRE_TUTOR')
            except User.DoesNotExist:
                pass
        
        # 2. Intentar buscar por código de paciente
        if not user_obj:
            from apps.pacientes.models import Paciente
            try:
                paciente = Paciente.objects.get(codigo_paciente__iexact=codigo)
                if paciente.padre_tutor and paciente.padre_tutor.usuario:
                    user_obj = paciente.padre_tutor.usuario
            except Paciente.DoesNotExist:
                pass

        # 3. Intentar buscar por username directo
        if not user_obj:
            try:
                user_obj = User.objects.get(username__iexact=codigo, rol='PADRE_TUTOR')
            except User.DoesNotExist:
                pass

        if user_obj is not None:
            user = authenticate(request, username=user_obj.username, password=pin)
            if user is not None:
                login(request, user)
                return redirect('padres:estado')
            else:
                messages.error(request, 'El PIN de acceso ingresado es incorrecto.')
        else:
            messages.error(request, 'No se encontró ningún paciente o tutor asociado a ese código o correo.')

    context = {
        'titulo': 'Portal de Padres - FACCI Care',
    }
    return render(request, 'auth_app/login_padres.html', context)


def recuperar_view(request):
    """Recuperacion de contrasena."""
    context = {
        'titulo': 'Recuperar Contrasena',
    }
    return render(request, 'auth_app/recuperar.html', context)
