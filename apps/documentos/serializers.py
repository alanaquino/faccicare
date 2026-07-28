from rest_framework import serializers
from .models import DocumentoMedico, SolicitudDocumento
from apps.pacientes.models import Paciente
from apps.auth_app.models import CustomUser


class DocumentoMedicoListSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    subido_por_nombre = serializers.CharField(source='subido_por.get_full_name', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = DocumentoMedico
        fields = (
            'id', 'paciente', 'paciente_nombre', 'tipo_documento', 'tipo_display',
            'estado', 'estado_display', 'fecha_documento', 'subido_por',
            'subido_por_nombre', 'visible_padre', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class DocumentoMedicoDetailSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    subido_por_nombre = serializers.CharField(source='subido_por.get_full_name', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    nombre_archivo = serializers.CharField(read_only=True)
    extension = serializers.CharField(read_only=True)
    tamano = serializers.CharField(read_only=True)
    icono = serializers.CharField(read_only=True)
    color = serializers.CharField(read_only=True)

    class Meta:
        model = DocumentoMedico
        fields = (
            'id', 'paciente', 'paciente_nombre', 'tipo_documento', 'tipo_display',
            'archivo', 'descripcion', 'fecha_documento', 'estado', 'estado_display',
            'subido_por', 'subido_por_nombre', 'visible_padre', 'created_at', 'updated_at',
            'nombre_archivo', 'extension', 'tamano', 'icono', 'color'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'subido_por')


class DocumentoMedicoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoMedico
        fields = (
            'paciente', 'tipo_documento', 'archivo',
            'descripcion', 'fecha_documento', 'visible_padre'
        )

    def validate_archivo(self, value):
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("El archivo no puede superar 20 MB")

        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'docx', 'xlsx']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Formato no permitido. Usar: {', '.join(allowed_extensions)}"
            )
        return value

    def create(self, validated_data):
        validated_data['subido_por'] = self.context['request'].user
        return super().create(validated_data)


class SolicitudDocumentoListSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    medico_nombre = serializers.CharField(source='medico_solicitante.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = SolicitudDocumento
        fields = (
            'id', 'paciente', 'paciente_nombre', 'titulo', 'estado', 'estado_display',
            'medico_solicitante', 'medico_nombre', 'created_at'
        )
        read_only_fields = ('id', 'created_at')


class SolicitudDocumentoDetailSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    medico_nombre = serializers.CharField(source='medico_solicitante.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    documento_info = DocumentoMedicoListSerializer(source='documento_asociado', read_only=True)

    class Meta:
        model = SolicitudDocumento
        fields = (
            'id', 'paciente', 'paciente_nombre', 'titulo', 'descripcion', 'estado',
            'estado_display', 'medico_solicitante', 'medico_nombre', 'documento_asociado',
            'documento_info', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class SolicitudDocumentoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolicitudDocumento
        fields = ('paciente', 'titulo', 'descripcion')

    def create(self, validated_data):
        validated_data['medico_solicitante'] = self.context['request'].user
        return super().create(validated_data)
