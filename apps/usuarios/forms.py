from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from apps.auth_app.models import CustomUser
from apps.core.models import CentroSalud
from apps.padres.models import PadreTutor


class AdminUserEditForm(forms.ModelForm):
    """Datos de cuenta que un administrador puede mantener para otro usuario."""

    password1 = forms.CharField(required=False, strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(required=False, strip=False, widget=forms.PasswordInput)
    eliminar_foto = forms.BooleanField(required=False)

    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'username', 'email', 'tipo_documento',
            'cedula', 'telefono', 'foto_perfil', 'rol', 'especialidad',
            'centro_medico', 'is_active',
        )

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['centro_medico'].queryset = CentroSalud.objects.order_by('nombre')
        input_class = (
            'w-full px-4 py-3 rounded-lg border border-outline-variant bg-surface '
            'focus:outline-none focus:ring-2 focus:ring-primary/50'
        )
        for name, field in self.fields.items():
            if name in ('is_active', 'eliminar_foto'):
                field.widget.attrs['class'] = 'w-4 h-4 rounded border-outline-variant text-primary'
            else:
                field.widget.attrs['class'] = input_class
        self.fields['foto_perfil'].widget.attrs.update({
            'accept': 'image/*',
            'class': (
                f'{input_class} file:mr-3 file:py-1 file:px-3 file:rounded-lg '
                'file:border-0 file:bg-primary-container/30 file:text-primary'
            ),
        })

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if CustomUser.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un usuario con este nombre de usuario.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and CustomUser.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('El correo electrónico ya está registrado.')
        return email

    def clean_cedula(self):
        cedula = (self.cleaned_data.get('cedula') or '').strip()
        if cedula and CustomUser.objects.filter(cedula=cedula).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este documento de identidad ya está registrado.')
        return cedula or None

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1', '')
        password2 = cleaned_data.get('password2', '')

        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            elif password1:
                try:
                    password_validation.validate_password(password1, self.instance)
                except ValidationError as error:
                    self.add_error('password1', error)

        if cleaned_data.get('foto_perfil') and cleaned_data.get('eliminar_foto'):
            self.add_error('eliminar_foto', 'No puedes cargar y eliminar la foto al mismo tiempo.')

        if self.actor and self.instance.pk == self.actor.pk:
            if cleaned_data.get('rol') != CustomUser.Rol.ADMIN:
                self.add_error('rol', 'No puedes quitarte el rol de administrador.')
            if not cleaned_data.get('is_active'):
                self.add_error('is_active', 'No puedes desactivar tu propia cuenta.')

        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('eliminar_foto'):
            usuario.foto_perfil = None
        if self.cleaned_data.get('password1'):
            usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario


class ParentProfileAdminForm(forms.ModelForm):
    """Información adicional de las cuentas con rol Padre/Tutor."""

    class Meta:
        model = PadreTutor
        fields = (
            'parentesco', 'nacionalidad', 'direccion', 'provincia', 'municipio',
            'ocupacion', 'contacto_emergencia', 'telefono_emergencia',
            'estado_civil', 'cantidad_hijos', 'ingresos_aproximados',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_class = (
            'w-full px-4 py-3 rounded-lg border border-outline-variant bg-surface '
            'focus:outline-none focus:ring-2 focus:ring-primary/50'
        )
        for field in self.fields.values():
            field.widget.attrs['class'] = input_class
