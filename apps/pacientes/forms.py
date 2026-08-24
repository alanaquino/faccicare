from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.auth_app.models import CustomUser
from apps.core.constants import PROVINCIAS_RD
from apps.padres.models import PadreTutor
from apps.pacientes.models import NotaClinica, Paciente


INPUT_CLASSES = (
    "w-full px-4 py-3 rounded-lg border border-outline-variant bg-surface "
    "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary "
    "transition-all font-body-md text-body-md placeholder:text-outline"
)


class RegistroPacienteForm(forms.Form):
    nombres = forms.CharField(max_length=150, label="Nombre")
    apellidos = forms.CharField(max_length=150, label="Apellido")
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    sexo = forms.ChoiceField(choices=[("", "Seleccionar...")] + list(Paciente.Sexo.choices))
    provincia = forms.ChoiceField(choices=[("", "Seleccionar provincia...")] + [(p, p) for p in PROVINCIAS_RD])
    municipio = forms.CharField(max_length=100, required=False)
    direccion = forms.CharField(required=False, widget=forms.TextInput())
    tipo_sangre = forms.ChoiceField(
        choices=[("", "Seleccionar...")] + list(Paciente.TipoSangre.choices),
        required=False,
    )
    alergias = forms.CharField(required=False, widget=forms.Textarea())
    antecedentes_medicos = forms.CharField(required=False, widget=forms.Textarea())
    peso = forms.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0)
    altura = forms.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0)
    escuela = forms.CharField(max_length=200, required=False)
    seguro_medico = forms.CharField(max_length=100, required=False)
    numero_seguro = forms.CharField(max_length=50, required=False)

    tutor_nombre = forms.CharField(max_length=150, label="Nombre del tutor")
    tutor_tipo_documento = forms.ChoiceField(
        choices=CustomUser.TipoDocumento.choices,
        initial=CustomUser.TipoDocumento.CEDULA,
        required=False,
        label="Tipo de documento",
    )
    tutor_cedula = forms.CharField(max_length=20, required=False, label="Número de documento")
    tutor_telefono = forms.CharField(max_length=20, label="Telefono")
    tutor_email = forms.EmailField(required=False, label="Correo electronico")
    tutor_direccion = forms.CharField(widget=forms.TextInput(), label="Direccion")
    parentesco = forms.ChoiceField(choices=PadreTutor.Parentesco.choices)
    medico_asignado = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        empty_label="Sin asignar",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medico_asignado"].queryset = CustomUser.objects.filter(
            rol__in=["MEDICO", "PEDIATRA", "ONCOLOGO", "PERSONAL_FACCI"]
        ).order_by("first_name", "last_name", "username")
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", INPUT_CLASSES)
            if name in {"alergias", "antecedentes_medicos"}:
                field.widget.attrs.setdefault("rows", 3)
                field.widget.attrs["class"] += " resize-none"
        if self.is_bound:
            for name in self.errors:
                if name in self.fields:
                    self.fields[name].widget.attrs["class"] += (
                        " border-error focus:border-error focus:ring-error/50"
                    )

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data["fecha_nacimiento"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de nacimiento no puede estar en el futuro.")
        return fecha

    def clean_tutor_tipo_documento(self):
        return self.cleaned_data.get("tutor_tipo_documento") or CustomUser.TipoDocumento.CEDULA

    def clean_tutor_cedula(self):
        tipo_doc = self.cleaned_data.get("tutor_tipo_documento")
        cedula = (self.cleaned_data.get("tutor_cedula") or "").strip() or None
        if tipo_doc == "CEDULA" and cedula:
            cleaned_ced = cedula.replace(" ", "").replace("-", "")
            if not (len(cleaned_ced) == 11 and cleaned_ced.isdigit()):
                raise forms.ValidationError("La cédula dominicana debe tener 11 dígitos.")
            return f"{cleaned_ced[:3]}-{cleaned_ced[3:10]}-{cleaned_ced[10]}"
        return cedula

    def clean(self):
        cleaned = super().clean()
        cedula = cleaned.get("tutor_cedula")
        email = cleaned.get("tutor_email")

        usuarios_coincidentes = CustomUser.objects.none()
        if cedula:
            usuarios_coincidentes = usuarios_coincidentes | CustomUser.objects.filter(cedula=cedula)
        if email:
            usuarios_coincidentes = usuarios_coincidentes | CustomUser.objects.filter(email__iexact=email)

        usuario_no_tutor = usuarios_coincidentes.filter(
            Q(is_staff=True)
            | Q(is_superuser=True)
            | ~Q(rol=CustomUser.Rol.PADRE_TUTOR)
        ).first()
        if usuario_no_tutor is not None:
            raise forms.ValidationError(
                "La cedula o el correo del tutor pertenece a una cuenta del personal. "
                "Use los datos de la cuenta del padre o tutor correspondiente."
            )

        if cedula and email:
            usuario_por_cedula = CustomUser.objects.filter(cedula=cedula).first()
            usuario_por_email = CustomUser.objects.filter(email__iexact=email).first()
            if usuario_por_cedula and usuario_por_email and usuario_por_cedula.pk != usuario_por_email.pk:
                raise forms.ValidationError(
                    "La cedula y el correo pertenecen a usuarios distintos. Verifique los datos del tutor."
                )
        return cleaned


class NotaClinicaForm(forms.ModelForm):
    class Meta:
        model = NotaClinica
        fields = ("tipo", "texto", "es_importante")
        widgets = {
            "texto": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT_CLASSES)
        self.fields["es_importante"].widget.attrs["class"] = "h-4 w-4 rounded border-outline-variant text-primary focus:ring-primary"
        self.fields["texto"].widget.attrs["class"] += " resize-none"
