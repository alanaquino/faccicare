import datetime
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.auth_app.models import CustomUser
from apps.padres.models import PadreTutor, RecursoEducativo
from apps.pacientes.models import Paciente, NotaClinica
from apps.cribado.models import CuestionarioCribado
from apps.documentos.models import DocumentoMedico
from apps.core.models import CentroSalud
from apps.referencias.models import ReferenciaMedica, Contrarreferencia, ReferenciaIngresoCasaFACCI
from apps.seguimiento.models import SeguimientoPaciente, IndicacionMedica
from apps.alojamiento.models import HabitacionCasa, EstanciaFamiliar
from apps.laboratorio.models import CatalogoEstudio, ResultadoLaboratorio, ValorResultado
from apps.psicosocial.models import EvaluacionPsicosocial

def _seed_password(env_var: str, fallback: str) -> str:
    """Lee contraseña desde variable de entorno; usa fallback solo en DEBUG."""
    return os.environ.get(env_var, fallback)


class Command(BaseCommand):
    help = 'Poblar la base de datos con datos de prueba realistas para FACCI Care.'

    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            self.stderr.write(self.style.ERROR(
                'seed_data no puede ejecutarse en producción (DEBUG=False). '
                'Establece DEBUG=True o usa fixtures verificadas.'
            ))
            return

        self.stdout.write(self.style.WARNING('Iniciando la limpieza de base de datos...'))

        # Desactivar FK checks para poder limpiar en cualquier orden (SQLite dev)
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute('PRAGMA foreign_keys = OFF')

        CentroSalud.objects.all().delete()
        EvaluacionPsicosocial.objects.all().delete()
        ResultadoLaboratorio.objects.all().delete()
        EstanciaFamiliar.objects.all().delete()
        ReferenciaIngresoCasaFACCI.objects.all().delete()
        Contrarreferencia.objects.all().delete()
        ReferenciaMedica.objects.all().delete()
        SeguimientoPaciente.objects.all().delete()
        IndicacionMedica.objects.all().delete()
        DocumentoMedico.objects.all().delete()
        CuestionarioCribado.objects.all().delete()
        NotaClinica.objects.all().delete()
        Paciente.objects.all().delete()
        PadreTutor.objects.all().delete()
        CustomUser.objects.all().delete()
        RecursoEducativo.objects.all().delete()

        with connection.cursor() as cur:
            cur.execute('PRAGMA foreign_keys = ON')

        self.stdout.write(self.style.SUCCESS('Base de datos limpia.'))

        # 1. Centros de Salud (deben existir antes de crear usuarios)
        self.stdout.write(self.style.WARNING('Creando centros de salud...'))
        CS = CentroSalud
        centros = [
            CS(nombre='Hospital Pediátrico Central',         tipo=CS.Tipo.HOSPITAL,    provincia='Distrito Nacional', municipio='Santo Domingo',  esp_oncologia_pediatrica=True,  esp_pediatria_general=True,  camas_total=120, camas_disponibles=30, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE,  medicos_titulares=18, entrenados_facci=10),
            CS(nombre='Centro Oncológico Nacional',          tipo=CS.Tipo.HOSPITAL,    provincia='Distrito Nacional', municipio='Santo Domingo',  esp_oncologia_pediatrica=True,  esp_laboratorio_avanzado=True, camas_total=80, camas_disponibles=15, estado_derivacion=CS.EstadoDerivacion.LIMITADO,    medicos_titulares=12, entrenados_facci=8),
            CS(nombre='Hospital Ney Arias Lora',             tipo=CS.Tipo.HOSPITAL,    provincia='Distrito Nacional', municipio='Santo Domingo',  esp_pediatria_general=True,     esp_imagenes_diagnosticas=True, camas_total=200, camas_disponibles=50, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE, medicos_titulares=30, entrenados_facci=5),
            CS(nombre='Hospital Infantil Robert Reid Cabral',tipo=CS.Tipo.HOSPITAL,    provincia='Distrito Nacional', municipio='Santo Domingo',  esp_oncologia_pediatrica=True,  esp_pediatria_general=True,  esp_imagenes_diagnosticas=True, camas_total=150, camas_disponibles=40, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE, medicos_titulares=25, entrenados_facci=12),
            CS(nombre='Hospital General Plaza de la Salud',  tipo=CS.Tipo.HOSPITAL,    provincia='Distrito Nacional', municipio='Santo Domingo',  esp_pediatria_general=True,     esp_laboratorio_avanzado=True, camas_total=300, camas_disponibles=70, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE, medicos_titulares=40, entrenados_facci=6),
            CS(nombre='Hospital Regional de Santiago',       tipo=CS.Tipo.HOSPITAL,    provincia='Santiago',          municipio='Santiago',       esp_oncologia_pediatrica=True,  esp_pediatria_general=True,  camas_total=90,  camas_disponibles=20, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE,  medicos_titulares=14, entrenados_facci=7),
            CS(nombre='Hospital Docente Padre Billini',      tipo=CS.Tipo.HOSPITAL,    provincia='Distrito Nacional', municipio='Santo Domingo',  esp_pediatria_general=True,     camas_total=100, camas_disponibles=25, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE, medicos_titulares=16, entrenados_facci=3),
            CS(nombre='Centro Diagnóstico CEDIMAT',          tipo=CS.Tipo.DIAGNOSTICO, provincia='Distrito Nacional', municipio='Santo Domingo',  esp_imagenes_diagnosticas=True, esp_laboratorio_avanzado=True, camas_total=0, camas_disponibles=0, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE, medicos_titulares=8, entrenados_facci=2),
            CS(nombre='Hospital Regional Universitario José María Cabral y Báez', tipo=CS.Tipo.HOSPITAL, provincia='Santiago', municipio='Santiago', esp_oncologia_pediatrica=True, esp_pediatria_general=True, camas_total=180, camas_disponibles=45, estado_derivacion=CS.EstadoDerivacion.DISPONIBLE, medicos_titulares=22, entrenados_facci=9),
            CS(nombre='Casa FACCI', tipo=CS.Tipo.OTRO, provincia='Santiago', municipio='Santiago'),
        ]
        CentroSalud.objects.bulk_create(centros)
        _centros = {c.nombre: c for c in CentroSalud.objects.all()}
        def centro(nombre):
            return _centros.get(nombre)
        self.stdout.write(self.style.SUCCESS(f'{len(centros)} centros de salud creados.'))

        self.stdout.write(self.style.WARNING('Creando usuarios clínicos...'))

        # 2. Crear Administradores y Médicos
        admin_user = CustomUser.objects.create(
            username='admin',
            email='admin@faccicare.org',
            first_name='Ana',
            last_name='Flores',
            rol=CustomUser.Rol.ADMIN,
            cedula='001-0000000-0',
            is_staff=True,
            is_superuser=True
        )
        admin_user.set_password(_seed_password('SEED_ADMIN_PASSWORD', 'adminpassword123'))
        admin_user.save()

        pediatra_1 = CustomUser.objects.create(
            username='jmartinez',
            email='jmartinez@faccicare.org',
            first_name='Juan',
            last_name='Martínez',
            rol=CustomUser.Rol.PEDIATRA,
            cedula='001-0000000-1',
            especialidad='Pediatría Clínica',
            centro_medico=centro('Hospital Regional de Santiago')
        )
        pediatra_1.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        pediatra_1.save()

        pediatra_2 = CustomUser.objects.create(
            username='elopez',
            email='elopez@faccicare.org',
            first_name='Elena',
            last_name='López',
            rol=CustomUser.Rol.PEDIATRA,
            cedula='001-0000000-2',
            especialidad='Medicina Pediátrica Infantil',
            centro_medico=centro('Hospital Infantil Robert Reid Cabral')
        )
        pediatra_2.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        pediatra_2.save()

        oncologo = CustomUser.objects.create(
            username='evargas',
            email='evargas@oncologia.org',
            first_name='Elena',
            last_name='Vargas',
            rol=CustomUser.Rol.ONCOLOGO,
            cedula='001-0000000-3',
            especialidad='Oncología Pediátrica',
            centro_medico=centro('Hospital Pediátrico Central')
        )
        oncologo.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        oncologo.save()

        personal_facci = CustomUser.objects.create(
            username='msantos',
            email='msantos@faccicare.org',
            first_name='María',
            last_name='Santos',
            rol=CustomUser.Rol.PERSONAL_FACCI,
            cedula='001-0000000-4',
            centro_medico=None
        )
        personal_facci.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        personal_facci.save()

        medico_general = CustomUser.objects.create(
            username='rgomez',
            email='rgomez@faccicare.org',
            first_name='Roberto',
            last_name='Gómez',
            rol=CustomUser.Rol.MEDICO,
            cedula='001-0000000-5',
            especialidad='Medicina General',
            centro_medico=centro('Hospital Regional de Santiago')
        )
        medico_general.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        medico_general.save()

        trabajadora_social = CustomUser.objects.create(
            username='lperez',
            email='lperez@faccicare.org',
            first_name='Laura',
            last_name='Pérez',
            rol=CustomUser.Rol.TRABAJADORA_SOCIAL,
            cedula='001-0000000-6',
            especialidad='Trabajo Social / Psicología',
            centro_medico=None
        )
        trabajadora_social.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        trabajadora_social.save()

        enfermera = CustomUser.objects.create(
            username='cgonzalez',
            email='cgonzalez@faccicare.org',
            first_name='Carmen',
            last_name='González',
            rol=CustomUser.Rol.ENFERMERA,
            cedula='001-0000000-7',
            especialidad='Enfermería Pediátrica',
            centro_medico=centro('Hospital Infantil Robert Reid Cabral')
        )
        enfermera.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
        enfermera.save()

        self.stdout.write(self.style.SUCCESS('Usuarios clínicos creados con éxito.'))
        self.stdout.write(self.style.WARNING('Creando tutores y pacientes...'))

        # 2. Datos de Tutores
        tutores_data = [
            {'username': 'carlos_r', 'first_name': 'Carlos', 'last_name': 'Rodríguez', 'email': 'carlos.rodriguez@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Calle Duarte #45, Los Jardines, Santiago', 'provincia': 'Santiago', 'municipio': 'Santiago de los Caballeros', 'cedula': '001-1234567-8', 'telefono': '809-555-1234'},
            {'username': 'maria_v', 'first_name': 'María', 'last_name': 'Vargas', 'email': 'maria.vargas@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Av. Independencia #78, Gazcue, D.N.', 'provincia': 'Santo Domingo', 'municipio': 'Distrito Nacional', 'cedula': '002-9876543-1', 'telefono': '809-555-2345'},
            {'username': 'ana_p', 'first_name': 'Ana', 'last_name': 'Peña', 'email': 'ana.pena@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Calle Restauración #12, La Vega', 'provincia': 'La Vega', 'municipio': 'Concepción de La Vega', 'cedula': '003-5554321-2', 'telefono': '809-555-3456'},
            {'username': 'pedro_d', 'first_name': 'Pedro', 'last_name': 'Díaz', 'email': 'pedro.diaz@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Los Frailes #89, San Cristóbal', 'provincia': 'San Cristóbal', 'municipio': 'San Cristóbal', 'cedula': '004-7778899-3', 'telefono': '809-555-4567'},
            {'username': 'luis_m', 'first_name': 'Luis', 'last_name': 'Morales', 'email': 'luis.morales@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Calle Separación #3, Puerto Plata', 'provincia': 'Puerto Plata', 'municipio': 'San Felipe de Puerto Plata', 'cedula': '005-3332211-0', 'telefono': '809-555-5678'},
            {'username': 'sandra_g', 'first_name': 'Sandra', 'last_name': 'Gómez', 'email': 'sandra.gomez@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Calle del Sol #45, Santiago', 'provincia': 'Santiago', 'municipio': 'Santiago de los Caballeros', 'cedula': '054-0011223-4', 'telefono': '809-555-6789'},
            {'username': 'ramon_j', 'first_name': 'Ramón', 'last_name': 'Jiménez', 'email': 'ramon.jimenez@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Av. San Francisco #102, San Francisco de Macorís', 'provincia': 'Duarte', 'municipio': 'San Francisco de Macorís', 'cedula': '063-0022334-5', 'telefono': '809-555-7890'},
            {'username': 'gloria_f', 'first_name': 'Gloria', 'last_name': 'Fernández', 'email': 'gloria.fernandez@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Calle Marginal #56, Santo Domingo Este', 'provincia': 'Santo Domingo', 'municipio': 'Santo Domingo Este', 'cedula': '026-0033445-6', 'telefono': '809-555-8901'},
            {'username': 'jose_r', 'first_name': 'José', 'last_name': 'Reyes', 'email': 'jose.reyes@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Calle Restauración #18, La Vega', 'provincia': 'La Vega', 'municipio': 'Concepción de La Vega', 'cedula': '023-0044556-7', 'telefono': '809-555-9012'},
            {'username': 'yaneris_m', 'first_name': 'Yaneris', 'last_name': 'Martínez', 'email': 'yaneris.martinez@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Calle General Cabral #7, San Cristóbal', 'provincia': 'San Cristóbal', 'municipio': 'San Cristóbal', 'cedula': '018-0055667-8', 'telefono': '809-555-0123'},
            {'username': 'franklin_t', 'first_name': 'Franklin', 'last_name': 'Torres', 'email': 'franklin.torres@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Calle 12 de Julio #33, Puerto Plata', 'provincia': 'Puerto Plata', 'municipio': 'San Felipe de Puerto Plata', 'cedula': '028-0066778-9', 'telefono': '809-555-1230'},
            {'username': 'wanda_n', 'first_name': 'Wanda', 'last_name': 'Núñez', 'email': 'wanda.nunez@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Calle Castillo #48, San Francisco de Macorís', 'provincia': 'Duarte', 'municipio': 'San Francisco de Macorís', 'cedula': '013-0077889-0', 'telefono': '809-555-2341'},
            {'username': 'hector_r', 'first_name': 'Héctor', 'last_name': 'Ramírez', 'email': 'hector.ramirez@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Calle Benito Monción #9, Santiago', 'provincia': 'Santiago', 'municipio': 'Santiago de los Caballeros', 'cedula': '041-0088990-1', 'telefono': '809-555-3452'},
            {'username': 'rosa_p', 'first_name': 'Rosa', 'last_name': 'Polanco', 'email': 'rosa.polanco@correo.com', 'parentesco': PadreTutor.Parentesco.MADRE, 'direccion': 'Calle Duarte #14, Santo Domingo Norte', 'provincia': 'Santo Domingo', 'municipio': 'Santo Domingo Norte', 'cedula': '012-0099001-2', 'telefono': '809-555-4563'},
            {'username': 'miguel_h', 'first_name': 'Miguel', 'last_name': 'Herrera', 'email': 'miguel.herrera@correo.com', 'parentesco': PadreTutor.Parentesco.PADRE, 'direccion': 'Calle Sánchez #2, La Vega', 'provincia': 'La Vega', 'municipio': 'Concepción de La Vega', 'cedula': '065-0100112-3', 'telefono': '809-555-5674'},
        ]

        tutores_list = []
        for t in tutores_data:
            user = CustomUser.objects.create(
                username=t['username'],
                email=t['email'],
                first_name=t['first_name'],
                last_name=t['last_name'],
                rol=CustomUser.Rol.PADRE_TUTOR,
                cedula=t['cedula'],
                telefono=t['telefono']
            )
            user.set_password(_seed_password('SEED_DEFAULT_PASSWORD', 'password123'))
            user.save()

            tutor = PadreTutor.objects.create(
                usuario=user,
                parentesco=t['parentesco'],
                direccion=t['direccion'],
                provincia=t['provincia'],
                municipio=t['municipio'],
                ocupacion='Comercio Independiente',
                estado_civil=PadreTutor.EstadoCivil.CASADO,
                cantidad_hijos=2,
                ingresos_aproximados='RD$15,000–25,000'
            )
            tutores_list.append(tutor)

        self.stdout.write(self.style.SUCCESS('Padres y tutores creados con éxito.'))
        self.stdout.write(self.style.WARNING('Creando expedientes de pacientes infantiles...'))

        # 3. Pacientes
        pacientes_data = [
            {'codigo': 'FACCI-MR01', 'nombres': 'Mateo', 'apellidos': 'Rodríguez', 'fecha_nacimiento': datetime.date(2021, 8, 15), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.O_POS, 'provincia': 'Santiago', 'municipio': 'Santiago', 'alergias': 'Amoxicilina', 'estado': Paciente.EstadoPaciente.EN_TRATAMIENTO, 'tutor': tutores_list[0], 'medico': pediatra_1},
            {'codigo': 'FACCI-SV02', 'nombres': 'Sofía', 'apellidos': 'Vargas', 'fecha_nacimiento': datetime.date(2019, 10, 22), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.A_POS, 'provincia': 'Santo Domingo', 'municipio': 'Gazcue', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.FINALIZADO, 'tutor': tutores_list[1], 'medico': pediatra_2},
            {'codigo': 'FACCI-LP03', 'nombres': 'Lucas', 'apellidos': 'Peña', 'fecha_nacimiento': datetime.date(2022, 11, 5), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.B_POS, 'provincia': 'La Vega', 'municipio': 'La Vega', 'alergias': 'Ibuprofeno', 'estado': Paciente.EstadoPaciente.EN_TRATAMIENTO, 'tutor': tutores_list[2], 'medico': pediatra_1},
            {'codigo': 'FACCI-ID04', 'nombres': 'Isabel', 'apellidos': 'Díaz', 'fecha_nacimiento': datetime.date(2020, 10, 30), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.AB_POS, 'provincia': 'San Cristóbal', 'municipio': 'San Cristóbal', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.FINALIZADO, 'tutor': tutores_list[3], 'medico': pediatra_2},
            {'codigo': 'FACCI-CM05', 'nombres': 'Carlos', 'apellidos': 'Morales', 'fecha_nacimiento': datetime.date(2022, 4, 14), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.O_NEG, 'provincia': 'Puerto Plata', 'municipio': 'Separación', 'alergias': 'Penicilina', 'estado': Paciente.EstadoPaciente.REFERIDO, 'tutor': tutores_list[4], 'medico': pediatra_1, 'diagnostico': Paciente.Diagnostico.LEUCEMIA},
            {'codigo': 'FACCI-AG06', 'nombres': 'Andrea', 'apellidos': 'Gómez', 'fecha_nacimiento': datetime.date(2018, 3, 9), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.A_POS, 'provincia': 'Santiago', 'municipio': 'Santiago de los Caballeros', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.EN_ESTUDIO, 'tutor': tutores_list[5], 'medico': pediatra_2, 'diagnostico': ''},
            {'codigo': 'FACCI-DJ07', 'nombres': 'Diego', 'apellidos': 'Jiménez', 'fecha_nacimiento': datetime.date(2016, 7, 27), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.O_POS, 'provincia': 'Duarte', 'municipio': 'San Francisco de Macorís', 'alergias': 'Sulfas', 'estado': Paciente.EstadoPaciente.CONFIRMADO, 'tutor': tutores_list[6], 'medico': oncologo, 'diagnostico': Paciente.Diagnostico.TUMORES_SNC},
            {'codigo': 'FACCI-VF08', 'nombres': 'Valentina', 'apellidos': 'Fernández', 'fecha_nacimiento': datetime.date(2019, 12, 3), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.B_POS, 'provincia': 'Santo Domingo', 'municipio': 'Santo Domingo Este', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.EN_TRATAMIENTO, 'tutor': tutores_list[7], 'medico': oncologo, 'diagnostico': Paciente.Diagnostico.LEUCEMIA},
            {'codigo': 'FACCI-SR09', 'nombres': 'Samuel', 'apellidos': 'Reyes', 'fecha_nacimiento': datetime.date(2015, 5, 18), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.AB_POS, 'provincia': 'La Vega', 'municipio': 'Concepción de La Vega', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.EN_REMISION, 'tutor': tutores_list[8], 'medico': medico_general, 'diagnostico': Paciente.Diagnostico.OTRO},
            {'codigo': 'FACCI-CM10', 'nombres': 'Camila', 'apellidos': 'Martínez', 'fecha_nacimiento': datetime.date(2021, 1, 22), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.O_NEG, 'provincia': 'San Cristóbal', 'municipio': 'San Cristóbal', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.SOSPECHOSO, 'tutor': tutores_list[9], 'medico': pediatra_1, 'diagnostico': ''},
            {'codigo': 'FACCI-JT11', 'nombres': 'Joel', 'apellidos': 'Torres', 'fecha_nacimiento': datetime.date(2017, 9, 11), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.A_NEG, 'provincia': 'Puerto Plata', 'municipio': 'San Felipe de Puerto Plata', 'alergias': 'Amoxicilina', 'estado': Paciente.EstadoPaciente.REFERIDO, 'tutor': tutores_list[10], 'medico': pediatra_1, 'diagnostico': Paciente.Diagnostico.NEUROBLASTOMA},
            {'codigo': 'FACCI-LN12', 'nombres': 'Laura', 'apellidos': 'Núñez', 'fecha_nacimiento': datetime.date(2020, 6, 30), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.B_NEG, 'provincia': 'Duarte', 'municipio': 'San Francisco de Macorís', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.EN_TRATAMIENTO, 'tutor': tutores_list[11], 'medico': oncologo, 'diagnostico': Paciente.Diagnostico.TUMOR_WILMS},
            {'codigo': 'FACCI-ER13', 'nombres': 'Emmanuel', 'apellidos': 'Ramírez', 'fecha_nacimiento': datetime.date(2019, 2, 8), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.O_POS, 'provincia': 'Santiago', 'municipio': 'Santiago de los Caballeros', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.DESCARTADO, 'tutor': tutores_list[12], 'medico': medico_general, 'diagnostico': ''},
            {'codigo': 'FACCI-NP14', 'nombres': 'Natalia', 'apellidos': 'Polanco', 'fecha_nacimiento': datetime.date(2022, 8, 1), 'sexo': Paciente.Sexo.FEMENINO, 'tipo_sangre': Paciente.TipoSangre.A_POS, 'provincia': 'Santo Domingo', 'municipio': 'Santo Domingo Norte', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.EN_TRATAMIENTO, 'tutor': tutores_list[13], 'medico': oncologo, 'diagnostico': Paciente.Diagnostico.RETINOBLASTOMA},
            {'codigo': 'FACCI-KH15', 'nombres': 'Kevin', 'apellidos': 'Herrera', 'fecha_nacimiento': datetime.date(2014, 11, 19), 'sexo': Paciente.Sexo.MASCULINO, 'tipo_sangre': Paciente.TipoSangre.O_POS, 'provincia': 'La Vega', 'municipio': 'Concepción de La Vega', 'alergias': 'Ninguna conocida', 'estado': Paciente.EstadoPaciente.FINALIZADO, 'tutor': tutores_list[14], 'medico': pediatra_2, 'diagnostico': Paciente.Diagnostico.LEUCEMIA},
        ]

        pacientes_list = []
        for idx, p in enumerate(pacientes_data):
            paciente = Paciente.objects.create(
                codigo_paciente=p['codigo'],
                nombres=p['nombres'],
                apellidos=p['apellidos'],
                fecha_nacimiento=p['fecha_nacimiento'],
                sexo=p['sexo'],
                tipo_sangre=p['tipo_sangre'],
                peso=14.50 + idx,
                altura=95.00 + idx * 2,
                direccion=p['tutor'].direccion,
                provincia=p['provincia'],
                municipio=p['municipio'],
                alergias=p.get('alergias', ''),
                estado_actual=p['estado'],
                diagnostico=p.get('diagnostico', ''),
                padre_tutor=p['tutor'],
                medico_asignado=p['medico']
            )
            pacientes_list.append(paciente)

        self.stdout.write(self.style.SUCCESS('Pacientes creados con éxito.'))
        self.stdout.write(self.style.WARNING('Creando cribados y documentos médicos...'))

        # 4. Cribados
        CuestionarioCribado.objects.create(
            paciente=pacientes_list[0], # Mateo
            medico=pediatra_1,
            fiebre_persistente=True,
            dolor_huesos=True,
            palidez=True,
            ganglios=True,
            nivel_riesgo=CuestionarioCribado.NivelRiesgo.MEDIO,
            resultado=CuestionarioCribado.Resultado.SOSPECHA_MODERADA,
            requiere_referencia=True,
            observaciones='Linfoadenopatía cervical y fiebre persistente. Se sugiere referir para ecografía cervical.'
        )

        CuestionarioCribado.objects.create(
            paciente=pacientes_list[4], # Carlos
            medico=pediatra_1,
            fiebre_persistente=True,
            perdida_peso=True,
            dolor_huesos=True,
            palidez=True,
            moretones=True,
            sangrado=True,
            ganglios=True,
            infecciones_recurrentes=True,
            nivel_riesgo=CuestionarioCribado.NivelRiesgo.ALTO,
            resultado=CuestionarioCribado.Resultado.SOSPECHA_ALTA,
            requiere_referencia=True,
            observaciones='Múltiples signos de alerta roja hematológica. Referido urgente a oncología.'
        )

        # 5. Documentos Médicos
        # Nota: Simularemos los archivos con un archivo en memoria simple para evitar subir PDFs reales
        dummy_file = ContentFile("Contenido del reporte medico simulado de FACCI Care.", name="Resultado_RM_Cerebral_Oct2023.pdf")
        DocumentoMedico.objects.create(
            paciente=pacientes_list[0], # Mateo
            subido_por=pediatra_1,
            tipo_documento=DocumentoMedico.TipoDocumento.INFORME_MEDICO,
            archivo=dummy_file,
            descripcion="Resultado de resonancia magnética cerebral.",
            fecha_documento=datetime.date(2023, 10, 19)
        )

        dummy_file_2 = ContentFile("Contenido de analitica de laboratorio simulado.", name="BHC_Laboratorio_Oct2023.pdf")
        DocumentoMedico.objects.create(
            paciente=pacientes_list[0], # Mateo
            subido_por=pediatra_1,
            tipo_documento=DocumentoMedico.TipoDocumento.LABORATORIO,
            archivo=dummy_file_2,
            descripcion="Hemograma completo BHC de laboratorio clínico.",
            fecha_documento=datetime.date(2023, 10, 14)
        )

        dummy_file_3 = ContentFile("Plan terapeutico oncológico.", name="Plan_Tratamiento_Quimio.pdf")
        DocumentoMedico.objects.create(
            paciente=pacientes_list[4], # Carlos
            subido_por=oncologo,
            tipo_documento=DocumentoMedico.TipoDocumento.INFORME_MEDICO,
            archivo=dummy_file_3,
            descripcion="Protocolo de quimioterapia inicial.",
            fecha_documento=datetime.date(2023, 11, 1)
        )

        self.stdout.write(self.style.SUCCESS('Cribados y documentos creados con éxito.'))

        # 6. Referencias Médicas
        self.stdout.write(self.style.WARNING('Creando referencias médicas...'))
        ReferenciaMedica.objects.create(
            paciente=pacientes_list[0], # Mateo
            medico_referente=pediatra_1,
            especialista_destino=oncologo,
            hospital_destino=centro('Hospital Pediátrico Central'),
            motivo_referencia='Linfoadenopatía cervical y fiebre persistente. Se sugiere referir para ecografía cervical.',
            prioridad=ReferenciaMedica.Prioridad.ALTA,
            estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
            observaciones='Paciente con sospecha moderada en el cribado.'
        )

        ReferenciaMedica.objects.create(
            paciente=pacientes_list[4], # Carlos
            medico_referente=pediatra_1,
            especialista_destino=oncologo,
            hospital_destino=centro('Hospital Infantil Robert Reid Cabral'),
            motivo_referencia='Múltiples signos de alerta roja hematológica. Referido urgente a oncología.',
            prioridad=ReferenciaMedica.Prioridad.URGENTE,
            estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
            observaciones='Paciente con sospecha alta en el cribado.'
        )

        # Referencias de pediatra_2 (Elena López)
        ReferenciaMedica.objects.create(
            paciente=pacientes_list[1], # Sofía
            medico_referente=pediatra_2,
            especialista_destino=oncologo,
            hospital_destino=centro('Hospital Pediátrico Central'),
            motivo_referencia='Control semestral post-remisión. Vigilancia activa recomendada por oncología.',
            prioridad=ReferenciaMedica.Prioridad.MEDIA,
            estado=ReferenciaMedica.EstadoReferencia.ACEPTADA,
            observaciones='Paciente en fase de vigilancia. Sin síntomas activos.'
        )
        ReferenciaMedica.objects.create(
            paciente=pacientes_list[3], # Isabel
            medico_referente=pediatra_2,
            especialista_destino=oncologo,
            hospital_destino=centro('Centro Oncológico Nacional'),
            motivo_referencia='Seguimiento oncológico semestral. Control de marcadores tumorales.',
            prioridad=ReferenciaMedica.Prioridad.MEDIA,
            estado=ReferenciaMedica.EstadoReferencia.EN_PROCESO,
            observaciones='Paciente estable. Continuar vigilancia según protocolo.'
        )
        self.stdout.write(self.style.SUCCESS('Referencias médicas creadas con éxito.'))

        # 7. Seguimientos Médicos de Pacientes
        self.stdout.write(self.style.WARNING('Creando seguimientos médicos...'))
        
        # Mateo (pediatra_1) - Inducción: fase de evaluación diagnóstica inicial
        SeguimientoPaciente.objects.create(
            paciente=pacientes_list[0],
            medico=pediatra_1,
            fase_protocolo=SeguimientoPaciente.FaseProtocolo.INDUCCION,
            estado_clinico='Estable, bajo observación.',
            sintomas_actuales='Linfoadenopatía cervical y fiebre persistente controlada.',
            tratamiento_actual='Fase de evaluación diagnóstica',
            medicamentos='Vitaminas pediátricas: 5 ml cada mañana\nHierro pediátrico: 2 ml al mediodía\nÁcido fólico: 1 tableta a las 8:00 PM',
            observaciones='Paciente tolera bien el tratamiento. Seguir pautas de higiene y reportar si presenta fiebre.',
            proxima_fecha_seguimiento=timezone.now() + datetime.timedelta(days=2),
            requiere_hospitalizacion=False
        )

        # Sofía (pediatra_2) - Vigilancia: control post-tratamiento
        SeguimientoPaciente.objects.create(
            paciente=pacientes_list[1],
            medico=pediatra_2,
            fase_protocolo=SeguimientoPaciente.FaseProtocolo.VIGILANCIA,
            estado_clinico='Evolución clínica satisfactoria, en fase de control clínico rutinario.',
            sintomas_actuales='Sin síntomas activos de cuidado.',
            tratamiento_actual='Vigilancia activa post-tratamiento',
            medicamentos='Complejo vitamínico infantil: 1 tableta cada mañana\nCalcio masticable: 1 gomita al mediodía',
            observaciones='Paciente activa y con excelente apetito. Control rutinario en un mes.',
            proxima_fecha_seguimiento=timezone.now() + datetime.timedelta(days=7),
            requiere_hospitalizacion=False
        )

        # Lucas (pediatra_1) - Mantenimiento: quimioterapia ciclo 2
        SeguimientoPaciente.objects.create(
            paciente=pacientes_list[2],
            medico=pediatra_1,
            fase_protocolo=SeguimientoPaciente.FaseProtocolo.MANTENIMIENTO,
            estado_clinico='Paciente estable, cursando ciclo 2 de tratamiento.',
            sintomas_actuales='Náuseas leves, controlado con antiemético.',
            tratamiento_actual='Esquema de quimioterapia en curso',
            medicamentos='Ondansetrón pediátrico: 4 mg cada 8 horas\nVitaminas con zinc: 5 ml cada mañana',
            observaciones='Evitar aglomeraciones y asegurar lavado frecuente de manos.',
            proxima_fecha_seguimiento=timezone.now() + datetime.timedelta(days=3),
            requiere_hospitalizacion=False
        )

        # Isabel (pediatra_2) - Consolidación: post-remisión semestral
        SeguimientoPaciente.objects.create(
            paciente=pacientes_list[3],
            medico=pediatra_2,
            fase_protocolo=SeguimientoPaciente.FaseProtocolo.CONSOLIDACION,
            estado_clinico='Control de seguimiento post-remisión completo.',
            sintomas_actuales='Sin síntomas. Paciente activa y en perfecto estado general.',
            tratamiento_actual='Vigilancia clínica semestral',
            medicamentos='Vitamina C infantil: 1 tableta masticable cada mañana',
            observaciones='Continuar alimentación balanceada y actividad física normal.',
            proxima_fecha_seguimiento=timezone.now() + datetime.timedelta(days=15),
            requiere_hospitalizacion=False
        )

        # Carlos (pediatra_1) - Inducción: referencia urgente, inicio de protocolo
        SeguimientoPaciente.objects.create(
            paciente=pacientes_list[4],
            medico=pediatra_1,
            fase_protocolo=SeguimientoPaciente.FaseProtocolo.INDUCCION,
            estado_clinico='Paciente referido urgente para confirmación diagnóstica oncológica.',
            sintomas_actuales='Múltiples moretones inexplicados, palidez y fatiga.',
            tratamiento_actual='Referencia a oncología pediátrica',
            medicamentos='Reposo absoluto en casa\nAbundante hidratación oral: 1.5 litros diarios',
            observaciones='Paciente debe evitar juegos bruscos y golpes por riesgo de sangrado. Cita urgente asignada.',
            proxima_fecha_seguimiento=timezone.now() + datetime.timedelta(days=1),
            requiere_hospitalizacion=False
        )
        self.stdout.write(self.style.SUCCESS('Seguimientos clínicos creados con éxito.'))

        # 8. Indicaciones Médicas
        self.stdout.write(self.style.WARNING('Creando indicaciones médicas...'))
        indicaciones_data = [
            # Mateo
            (pacientes_list[0], [
                {'titulo': 'Hidratación', 'descripcion': 'Asegure que Mateo tome al menos 1.5 litros de agua al día. Incluya jugos naturales sin azúcar.', 'tipo': 'HIGIENE', 'prioridad': 'ALTA'},
                {'titulo': 'Reposo', 'descripcion': 'Garantice 10-12 horas de sueño nocturno. Evite actividades físicas intensas hasta nueva orden.', 'tipo': 'ACTIVIDAD_FISICA', 'prioridad': 'ALTA'},
                {'titulo': 'Medicamentos', 'descripcion': 'Administre Vitaminas pediátricas (5 ml) cada mañana, Hierro pediátrico (2 ml) al mediodía, Ácido fólico (1 tableta) a las 8 PM.', 'tipo': 'MEDICAMENTOS', 'prioridad': 'ALTA'},
            ]),
            # Sofía
            (pacientes_list[1], [
                {'titulo': 'Alimentación Balanceada', 'descripcion': 'Dieta rica en proteínas: pollo, pescado, huevos. Verduras crudas y cocidas. Frutas frescas diarias.', 'tipo': 'ALIMENTACION', 'prioridad': 'MEDIA'},
                {'titulo': 'Actividades Normales', 'descripcion': 'Sofía puede realizar actividades normales. Permita juego moderado e interacción social supervisa.', 'tipo': 'ACTIVIDAD_FISICA', 'prioridad': 'MEDIA'},
                {'titulo': 'Control Mensual', 'descripcion': 'Mantener citas de seguimiento cada mes. Reportar cualquier síntoma anormal inmediatamente.', 'tipo': 'PREGUNTAS_FRECUENTES', 'prioridad': 'ALTA'},
            ]),
            # Lucas
            (pacientes_list[2], [
                {'titulo': 'Protocolo de Quimioterapia', 'descripcion': 'Ciclo 2 de quimioterapia en curso. Controlar náuseas con Ondansetrón pediátrico (4 mg cada 8 horas).', 'tipo': 'MEDICAMENTOS', 'prioridad': 'ALTA'},
                {'titulo': 'Higiene Estricta', 'descripcion': 'Lavado de manos frecuente. Baño diario. Evite aglomeraciones y personas resfriadas.', 'tipo': 'HIGIENE', 'prioridad': 'ALTA'},
                {'titulo': 'Alimentación Específica', 'descripcion': 'Comidas pequeñas y frecuentes. Preferir alimentos fríos o a temperatura ambiente. Evitar olores fuertes.', 'tipo': 'ALIMENTACION', 'prioridad': 'ALTA'},
            ]),
            # Isabel
            (pacientes_list[3], [
                {'titulo': 'Vigilancia Post-Remisión', 'descripcion': 'Vigilancia clínica semestral. Control de marcadores tumorales cada 6 meses.', 'tipo': 'PREGUNTAS_FRECUENTES', 'prioridad': 'ALTA'},
                {'titulo': 'Vida Cotidiana Normal', 'descripcion': 'Isabel puede realizar actividades escolares y recreativas normales. Mantener estilo de vida saludable.', 'tipo': 'ACTIVIDAD_FISICA', 'prioridad': 'MEDIA'},
                {'titulo': 'Vitamina Infantil', 'descripcion': 'Vitamina C infantil masticable cada mañana para reforzar inmunidad.', 'tipo': 'MEDICAMENTOS', 'prioridad': 'MEDIA'},
            ]),
            # Carlos
            (pacientes_list[4], [
                {'titulo': 'Reposo Absoluto', 'descripcion': 'Reposo completo en casa. No realizar juegos bruscos ni actividades que causen golpes.', 'tipo': 'ACTIVIDAD_FISICA', 'prioridad': 'ALTA'},
                {'titulo': 'Hidratación Urgente', 'descripcion': 'Abundante hidratación oral: mínimo 1.5 litros de agua diaria. Evitar bebidas con cafeína.', 'tipo': 'ALIMENTACION', 'prioridad': 'ALTA'},
                {'titulo': 'Alerta por Sangrado', 'descripcion': 'Contacte inmediatamente si presenta sangrado, hematomas nuevos, o fiebre mayor a 38°C.', 'tipo': 'PREGUNTAS_FRECUENTES', 'prioridad': 'ALTA'},
            ]),
        ]

        for paciente, indicaciones in indicaciones_data:
            for idx, ind_data in enumerate(indicaciones):
                IndicacionMedica.objects.create(
                    paciente=paciente,
                    medico=paciente.medico_asignado or pediatra_1,
                    titulo=ind_data['titulo'],
                    descripcion=ind_data['descripcion'],
                    tipo_indicacion=IndicacionMedica.TipoIndicacion.OTRA,
                    prioridad=ind_data['prioridad'],
                    activa=True,
                )
        self.stdout.write(self.style.SUCCESS('Indicaciones médicas creadas con éxito.'))

        # ============================================================
        # 9. REGISTROS ADICIONALES PARA LOS PACIENTES 6–15
        #    Genera datos en todos los módulos para un demo bien poblado.
        # ============================================================
        self.stdout.write(self.style.WARNING('Generando registros clínicos para pacientes adicionales...'))

        E = Paciente.EstadoPaciente
        pacientes_extra = pacientes_list[5:]

        # -- 9a. Cribados de detección --
        cribado_sintomas = {
            'ALTO':  dict(fiebre_persistente=True, perdida_peso=True, dolor_huesos=True, palidez=True, moretones=True, ganglios=True),
            'MEDIO': dict(fiebre_persistente=True, palidez=True, fatiga=True, ganglios=True),
            'BAJO':  dict(fatiga=True),
        }

        def _nivel_por_estado(estado):
            if estado in (E.CONFIRMADO, E.EN_TRATAMIENTO, E.REFERIDO):
                return 'ALTO'
            if estado in (E.SOSPECHOSO, E.EN_ESTUDIO):
                return 'MEDIO'
            return 'BAJO'
        cribadores = [pediatra_1, pediatra_2, medico_general]
        cribados_por_paciente = {}
        for i, pac in enumerate(pacientes_extra):
            nivel = _nivel_por_estado(pac.estado_actual)
            cribado = CuestionarioCribado.objects.create(
                paciente=pac,
                medico=cribadores[i % len(cribadores)],
                observaciones=(
                    f'Cribado de detección temprana de {pac.nombres} {pac.apellidos}. '
                    f'Clasificación de riesgo {nivel} según protocolo PENCI-RD.'
                ),
                **cribado_sintomas[nivel],
            )
            # Offset date to the past
            dias_atras = 10 + i * 3
            fecha_eval = timezone.now() - datetime.timedelta(days=dias_atras)
            CuestionarioCribado.objects.filter(pk=cribado.pk).update(fecha_evaluacion=fecha_eval)
            cribado.refresh_from_db()
            cribados_por_paciente[pac.id] = cribado

        # -- 9b. Documentos médicos --
        tipos_doc = [
            (DocumentoMedico.TipoDocumento.HEMOGRAMA,      'Hemograma completo con conteo diferencial.'),
            (DocumentoMedico.TipoDocumento.ANALITICA,      'Panel metabólico y química sanguínea.'),
            (DocumentoMedico.TipoDocumento.RADIOGRAFIA,    'Radiografía de tórax PA y lateral.'),
            (DocumentoMedico.TipoDocumento.SONOGRAFIA,     'Sonografía abdominal de control.'),
            (DocumentoMedico.TipoDocumento.INFORME_MEDICO, 'Informe de evolución clínica.'),
            (DocumentoMedico.TipoDocumento.RECETA,         'Receta médica de tratamiento vigente.'),
        ]
        for i, pac in enumerate(pacientes_extra):
            tipo, desc = tipos_doc[i % len(tipos_doc)]
            archivo = ContentFile(
                f'Documento simulado ({desc}) para {pac.codigo_paciente}.',
                name=f'{tipo}_{pac.codigo_paciente}.pdf',
            )
            DocumentoMedico.objects.create(
                paciente=pac,
                subido_por=pac.medico_asignado or pediatra_1,
                tipo_documento=tipo,
                archivo=archivo,
                descripcion=desc,
                fecha_documento=timezone.now().date() - datetime.timedelta(days=(i + 1) * 4),
                estado=DocumentoMedico.EstadoDocumento.REVISADO if i % 2 == 0 else DocumentoMedico.EstadoDocumento.PENDIENTE,
            )

        # -- 9c. Referencias médicas --
        hospitales_destino = [
            centro('Hospital Pediátrico Central'),
            centro('Hospital Infantil Robert Reid Cabral'),
            centro('Centro Oncológico Nacional'),
            centro('Hospital Regional Universitario José María Cabral y Báez'),
        ]
        prioridad_estado = {
            E.REFERIDO:       ReferenciaMedica.Prioridad.ALTA,
            E.CONFIRMADO:     ReferenciaMedica.Prioridad.URGENTE,
            E.EN_TRATAMIENTO: ReferenciaMedica.Prioridad.ALTA,
            E.EN_ESTUDIO:     ReferenciaMedica.Prioridad.MEDIA,
        }
        estado_ref_ciclo = [
            ReferenciaMedica.EstadoReferencia.PENDIENTE,
            ReferenciaMedica.EstadoReferencia.ACEPTADA,
            ReferenciaMedica.EstadoReferencia.EN_PROCESO,
            ReferenciaMedica.EstadoReferencia.COMPLETADA,
            ReferenciaMedica.EstadoReferencia.COMPLETADA,
            ReferenciaMedica.EstadoReferencia.ACEPTADA,
        ]
        referencias_extra = []
        for i, pac in enumerate(pacientes_extra):
            if pac.estado_actual not in prioridad_estado:
                continue
            # El estado se asigna por orden de creación para repartir todos los
            # estados posibles (incluidos COMPLETADA → contrarreferencia).
            estado_ref = estado_ref_ciclo[len(referencias_extra) % len(estado_ref_ciclo)]
            crib = cribados_por_paciente.get(pac.id)
            ref = ReferenciaMedica.objects.create(
                paciente=pac,
                cuestionario=crib,
                medico_referente=pac.medico_asignado or pediatra_1,
                especialista_destino=oncologo,
                hospital_destino=hospitales_destino[i % len(hospitales_destino)],
                motivo_referencia=(
                    f'Evaluación oncológica especializada para {pac.nombres} '
                    f'({pac.get_estado_actual_display()}). Requiere valoración por subespecialidad.'
                ),
                prioridad=prioridad_estado[pac.estado_actual],
                estado=estado_ref,
                observaciones='Referencia generada a partir del cribado de detección temprana.',
            )
            if crib:
                delay = 2 + (i % 5) # 2 a 6 días
                fecha_ref = crib.fecha_evaluacion + datetime.timedelta(days=delay)
                ReferenciaMedica.objects.filter(pk=ref.pk).update(fecha_referencia=fecha_ref)
                ref.refresh_from_db()
            referencias_extra.append(ref)

        # -- 9d. Seguimientos clínicos --
        fase_estado = {
            E.EN_TRATAMIENTO: SeguimientoPaciente.FaseProtocolo.MANTENIMIENTO,
            E.CONFIRMADO:     SeguimientoPaciente.FaseProtocolo.INDUCCION,
            E.EN_REMISION:    SeguimientoPaciente.FaseProtocolo.CONSOLIDACION,
            E.REFERIDO:       SeguimientoPaciente.FaseProtocolo.INDUCCION,
        }
        for i, pac in enumerate(pacientes_extra):
            fase = fase_estado.get(pac.estado_actual, SeguimientoPaciente.FaseProtocolo.VIGILANCIA)
            SeguimientoPaciente.objects.create(
                paciente=pac,
                medico=pac.medico_asignado or pediatra_1,
                fase_protocolo=fase,
                estado_clinico=f'Paciente {pac.get_estado_actual_display().lower()}, evolución dentro de lo esperado.',
                sintomas_actuales='Sin signos de alarma nuevos en esta consulta.',
                tratamiento_actual=f'Seguimiento según fase de protocolo {fase.label}.',
                medicamentos='Complejo vitamínico infantil: 1 dosis cada mañana.',
                observaciones='Reforzar adherencia al tratamiento y pautas de higiene en el hogar.',
                proxima_fecha_seguimiento=timezone.now() + datetime.timedelta(days=7 + i),
                peso_kg=16 + i,
                talla_cm=100 + i * 2,
                requiere_hospitalizacion=(pac.estado_actual == E.CONFIRMADO),
            )

        # -- 9e. Indicaciones médicas (2 por paciente) --
        for pac in pacientes_extra:
            medico_pac = pac.medico_asignado or pediatra_1
            IndicacionMedica.objects.create(
                paciente=pac, medico=medico_pac,
                tipo_indicacion=IndicacionMedica.TipoIndicacion.MEDICACION,
                titulo='Adherencia a medicamentos',
                descripcion=(
                    f'Administrar los medicamentos indicados a {pac.nombres} en los horarios establecidos, '
                    f'sin interrumpir dosis sin autorización médica.'
                ),
                prioridad=IndicacionMedica.Prioridad.ALTA,
            )
            IndicacionMedica.objects.create(
                paciente=pac, medico=medico_pac,
                tipo_indicacion=IndicacionMedica.TipoIndicacion.ALIMENTACION,
                titulo='Alimentación e hidratación',
                descripcion='Dieta balanceada rica en proteínas y frutas. Mantener hidratación de al menos 1.5 litros diarios.',
                prioridad=IndicacionMedica.Prioridad.MEDIA,
            )

        # -- 9f. Notas clínicas (todas los pacientes, incluidos los 5 originales) --
        tipos_nota = [
            NotaClinica.TipoNota.EVOLUCION,
            NotaClinica.TipoNota.DIAGNOSTICO,
            NotaClinica.TipoNota.TRATAMIENTO,
            NotaClinica.TipoNota.OBSERVACION,
            NotaClinica.TipoNota.ALERTA,
        ]
        for i, pac in enumerate(pacientes_list):
            tipo = tipos_nota[i % len(tipos_nota)]
            NotaClinica.objects.create(
                paciente=pac,
                autor=pac.medico_asignado or pediatra_1,
                tipo=tipo,
                texto=(
                    f'{tipo.label}: {pac.nombres} {pac.apellidos} — {pac.get_estado_actual_display()}. '
                    f'Se documenta la evolución clínica y el plan de manejo correspondiente.'
                ),
                es_importante=(tipo == NotaClinica.TipoNota.ALERTA),
            )

        # -- 9g. Contrarreferencias (respuesta del especialista) --
        for ref in referencias_extra:
            if ref.estado != ReferenciaMedica.EstadoReferencia.COMPLETADA:
                continue
            Contrarreferencia.objects.create(
                referencia=ref,
                medico_contrarreferente=oncologo,
                fecha_atencion=timezone.now().date() - datetime.timedelta(days=5),
                diagnostico=f'Valoración completada para {ref.paciente.nombres}. Hallazgos compatibles con seguimiento oncológico.',
                tipo_cancer=Contrarreferencia.TipoCancer.LEUCEMIA,
                estadio=Contrarreferencia.Estadio.II,
                tratamiento_realizado='Inicio de protocolo de quimioterapia y soporte hematológico.',
                estudios_realizados='Hemograma completo, frotis de sangre periférica y aspirado de médula ósea. Radiografía de tórax.',
                medicamentos_indicados='Según protocolo institucional. Control hematológico semanal.',
                resultado_atencion=Contrarreferencia.ResultadoAtencion.CONFIRMADO_SEGUIMIENTO,
                recomendaciones='Continuar seguimiento en FACCI. Reportar fiebre o sangrado de inmediato.',
                requiere_seguimiento_facci=True,
                proxima_cita=timezone.now().date() + datetime.timedelta(days=30),
            )

        self.stdout.write(self.style.SUCCESS('Registros clínicos adicionales creados con éxito.'))

        # 10. Recursos Educativos
        self.stdout.write(self.style.WARNING('Creando recursos educativos...'))
        call_command('cargar_recursos_familia', stdout=self.stdout)

        # 11. Habitaciones Casa FACCI (requeridas para CU-34/35/36)
        self.stdout.write(self.style.WARNING('Creando habitaciones Casa FACCI...'))
        habitaciones_data = [
            {'nombre': 'Habitación 1 — Planta Baja', 'capacidad': 3, 'descripcion': 'Planta baja, acceso sin escaleras, baño compartido.'},
            {'nombre': 'Habitación 2 — Planta Baja', 'capacidad': 2, 'descripcion': 'Planta baja, baño privado.'},
            {'nombre': 'Habitación 3 — Planta Alta', 'capacidad': 4, 'descripcion': 'Planta alta, vista al jardín, baño compartido.'},
            {'nombre': 'Habitación 4 — Planta Alta', 'capacidad': 2, 'descripcion': 'Planta alta, uso preferencial para madres lactantes.'},
            {'nombre': 'Habitación 5 — Ala Norte',   'capacidad': 3, 'descripcion': 'Ala norte, baño privado, aire acondicionado.'},
        ]
        habitaciones_list = []
        for h in habitaciones_data:
            habitacion, _ = HabitacionCasa.objects.get_or_create(
                nombre=h['nombre'],
                defaults={'capacidad': h['capacidad'], 'descripcion': h['descripcion'], 'activa': True},
            )
            habitaciones_list.append(habitacion)
        self.stdout.write(self.style.SUCCESS(f'{len(habitaciones_data)} habitaciones Casa FACCI creadas.'))

        # 12. Referencias de ingreso y estancias en Casa FACCI
        self.stdout.write(self.style.WARNING('Creando referencias de ingreso y estancias en Casa FACCI...'))

        # 12a. Referencias de ingreso pendientes / asignadas (CU-34)
        referencias_casa_data = [
            {'paciente': pacientes_list[4],  'estado': ReferenciaIngresoCasaFACCI.Estado.PENDIENTE, 'habitacion': None,                    'motivo': 'Traslado desde Puerto Plata para inicio de quimioterapia. Familia sin alojamiento en la capital.', 'tiempo': '2 semanas'},
            {'paciente': pacientes_list[7],  'estado': ReferenciaIngresoCasaFACCI.Estado.PENDIENTE, 'habitacion': None,                    'motivo': 'Ciclos de quimioterapia programados. Requiere hospedaje cercano al centro oncológico.', 'tiempo': '1 mes'},
            {'paciente': pacientes_list[10], 'estado': ReferenciaIngresoCasaFACCI.Estado.APROBADA,  'habitacion': habitaciones_list[2],    'motivo': 'Radioterapia programada. Aprobada asignación en planta alta.', 'tiempo': '3 semanas'},
            {'paciente': pacientes_list[12], 'estado': ReferenciaIngresoCasaFACCI.Estado.INGRESADO, 'habitacion': habitaciones_list[0],    'motivo': 'Ingreso confirmado para acompañamiento durante hospitalización prolongada.', 'tiempo': '10 días'},
        ]
        for r in referencias_casa_data:
            pac = r['paciente']
            tutor = pac.padre_tutor
            ReferenciaIngresoCasaFACCI.objects.create(
                paciente=pac,
                centro_origen=centro('Hospital Regional de Santiago'),
                hospital_destino=centro('Casa FACCI'),
                motivo_ingreso=r['motivo'],
                fecha_entrada=timezone.now().date() + datetime.timedelta(days=3),
                tiempo_estadia=r['tiempo'],
                habitacion=r['habitacion'],
                estado=r['estado'],
                responsable_paciente=tutor.usuario.nombre_completo,
                parentesco_responsable=tutor.get_parentesco_display(),
                telefono_responsable=tutor.usuario.telefono or '809-000-0000',
                direccion_responsable=tutor.direccion,
                ocupacion_responsable=tutor.ocupacion,
                observaciones='Referencia registrada por el equipo de Trabajo Social.',
                creado_por=trabajadora_social,
            )

        # 12b. Estancias familiares en las habitaciones (CU-35)
        estancias_data = [
            {'paciente': pacientes_list[3],  'habitacion': habitaciones_list[0], 'motivo': EstanciaFamiliar.MotivoEstancia.QUIMIOTERAPIA,   'estado': EstanciaFamiliar.Estado.ACTIVA,     'dias_ingreso': 5,  'egreso_real': None},
            {'paciente': pacientes_list[7],  'habitacion': habitaciones_list[2], 'motivo': EstanciaFamiliar.MotivoEstancia.QUIMIOTERAPIA,   'estado': EstanciaFamiliar.Estado.ACTIVA,     'dias_ingreso': 12, 'egreso_real': None},
            {'paciente': pacientes_list[11], 'habitacion': habitaciones_list[4], 'motivo': EstanciaFamiliar.MotivoEstancia.RADIOTERAPIA,    'estado': EstanciaFamiliar.Estado.ACTIVA,     'dias_ingreso': 3,  'egreso_real': None},
            {'paciente': pacientes_list[8],  'habitacion': habitaciones_list[1], 'motivo': EstanciaFamiliar.MotivoEstancia.CONSULTA,        'estado': EstanciaFamiliar.Estado.COMPLETADA, 'dias_ingreso': 30, 'egreso_real': 6},
            {'paciente': pacientes_list[14], 'habitacion': habitaciones_list[3], 'motivo': EstanciaFamiliar.MotivoEstancia.HOSPITALIZACION, 'estado': EstanciaFamiliar.Estado.COMPLETADA, 'dias_ingreso': 45, 'egreso_real': 20},
        ]
        for e in estancias_data:
            pac = e['paciente']
            tutor = pac.padre_tutor
            fecha_ingreso = timezone.now().date() - datetime.timedelta(days=e['dias_ingreso'])
            EstanciaFamiliar.objects.create(
                paciente=pac,
                habitacion=e['habitacion'],
                acompanante_nombre=tutor.usuario.nombre_completo,
                acompanante_parentesco=tutor.get_parentesco_display(),
                acompanante_telefono=tutor.usuario.telefono or '809-000-0000',
                motivo=e['motivo'],
                fecha_ingreso=fecha_ingreso,
                fecha_egreso_prevista=fecha_ingreso + datetime.timedelta(days=14),
                fecha_egreso_real=(
                    timezone.now().date() - datetime.timedelta(days=e['egreso_real'])
                    if e['egreso_real'] is not None else None
                ),
                estado=e['estado'],
                observaciones='Estancia registrada en Casa FACCI para acompañamiento del tratamiento.',
                registrado_por=personal_facci,
            )
        self.stdout.write(self.style.SUCCESS(
            f"{len(referencias_casa_data)} referencias de ingreso y {len(estancias_data)} estancias creadas."
        ))

        # ============================================================
        # 13. RESULTADOS DE LABORATORIO
        #     Carga el catálogo clínico y crea resultados por paciente.
        # ============================================================
        self.stdout.write(self.style.WARNING('Cargando catálogo y resultados de laboratorio...'))
        call_command('cargar_catalogo_laboratorio', stdout=self.stdout)

        # Índice {estudio: {parámetro: CatalogoParametro}} para enlazar valores al catálogo.
        _cat_cache = {}

        def _params_de(estudio_nombre):
            if estudio_nombre not in _cat_cache:
                est = CatalogoEstudio.objects.filter(nombre=estudio_nombre).first()
                _cat_cache[estudio_nombre] = {p.nombre: p for p in est.parametros.all()} if est else {}
            return _cat_cache[estudio_nombre]

        def crear_resultado(paciente, estudio_nombre, tipo, medico, dias, valores, narrativo='', revisor=None, obs=''):
            params = _params_de(estudio_nombre)
            fecha_muestra = timezone.now().date() - datetime.timedelta(days=dias)
            resultado = ResultadoLaboratorio.objects.create(
                paciente=paciente,
                solicitado_por=medico,
                revisado_por=revisor,
                tipo=tipo,
                nombre_examen=estudio_nombre,
                fecha_muestra=fecha_muestra,
                fecha_resultado=fecha_muestra + datetime.timedelta(days=1),
                estado=ResultadoLaboratorio.Estado.REVISADO if revisor else ResultadoLaboratorio.Estado.RECIBIDO,
                resultado_narrativo=narrativo,
                observaciones=obs,
            )
            for orden, (nombre_param, valor) in enumerate(valores, start=1):
                cat = params.get(nombre_param)
                ValorResultado.objects.create(
                    resultado=resultado,
                    parametro_catalogo=cat,
                    parametro=nombre_param,
                    valor=str(valor),
                    unidad=cat.unidad if cat else '',
                    referencia_min=cat.referencia_minima if cat else None,
                    referencia_max=cat.referencia_maxima if cat else None,
                    referencia_texto=cat.referencia_texto if cat else '',
                    orden=orden,
                )
            # Recalcula banderas críticas y ajusta el estado a CRÍTICO si aplica.
            resultado.actualizar_criticos()
            return resultado

        HEMO  = 'Hemograma, diferencial y frotis'
        QUIM  = 'Quimica sanguinea y metabolismo'
        COAG  = 'Coagulacion y hemostasia'
        ORINA = 'Orina y funcion renal complementaria'
        MARC  = 'Marcadores tumorales en sangre/orina'
        TE = ResultadoLaboratorio.TipoExamen

        hemo_normal = [('Hemoglobina', '12.5'), ('Hematocrito', '37'), ('Leucocitos / WBC', '7.5'),
                       ('Neutrofilos absolutos / ANC', '3.5'), ('Linfocitos absolutos', '2.8'),
                       ('Plaquetas', '285'), ('Blastos en sangre periferica', '0')]
        hemo_critico = [('Hemoglobina', '7.2'), ('Hematocrito', '22'), ('Leucocitos / WBC', '45'),
                        ('Neutrofilos absolutos / ANC', '0.3'), ('Linfocitos absolutos', '1.1'),
                        ('Plaquetas', '35'), ('Blastos en sangre periferica', '22')]
        quim_normal = [('Glucosa en ayunas', '88'), ('Urea / BUN', '12'), ('Creatinina', '0.5'),
                       ('Sodio', '138'), ('Potasio', '4.2'), ('Calcio total', '9.6'),
                       ('LDH / DHL', '210'), ('Acido urico', '3.8')]
        quim_lisis = [('Glucosa en ayunas', '92'), ('Creatinina', '0.7'), ('Sodio', '136'),
                      ('Potasio', '5.0'), ('Acido urico', '6.8'), ('LDH / DHL', '360'),
                      ('Fosforo', '5.9'), ('Calcio total', '8.9')]
        coag_normal = [('TP / PT', '13'), ('INR', '1.1'), ('TTPa / aPTT', '32'),
                       ('Fibrinogeno', '240'), ('Dimero D', '0.4')]
        orina_wilms = [('Densidad urinaria', '1.018'), ('pH urinario', '6.0'),
                       ('Proteinas en orina', 'Positivo (++)'), ('Sangre en orina', 'Positivo'),
                       ('Glucosa en orina', 'Negativo')]
        marc_neuro = [('NSE / Enolasa neuronal especifica', '20'), ('Cromogranina A', '110'),
                      ('LDH', '360'), ('VMA urinario', 'Elevado'), ('HVA urinario', 'Elevado')]
        marc_snc = [('AFP / Alfa-fetoproteina', '12'), ('beta-hCG cuantitativa', '6'), ('LDH', '280')]

        P = pacientes_list
        crear_resultado(P[0],  HEMO, TE.HEMOGRAMA,  pediatra_1,    5,  hemo_normal,  'Serie roja, blanca y plaquetaria dentro de parámetros.', revisor=pediatra_1)
        crear_resultado(P[0],  QUIM, TE.QUIMICA,    pediatra_1,    5,  quim_normal,  'Química sanguínea sin alteraciones significativas.', revisor=pediatra_1)
        crear_resultado(P[1],  HEMO, TE.HEMOGRAMA,  pediatra_2,    9,  hemo_normal,  'Control post-tratamiento normal.', revisor=pediatra_2)
        crear_resultado(P[4],  HEMO, TE.HEMOGRAMA,  pediatra_1,    2,  hemo_critico, 'Pancitopenia con blastos circulantes — ALERTA ROJA. Referir urgente a oncología.')
        crear_resultado(P[6],  HEMO, TE.HEMOGRAMA,  oncologo,      6,  hemo_normal,  'Hemograma de base previo a protocolo.', revisor=oncologo)
        crear_resultado(P[6],  MARC, TE.MARCADORES, oncologo,      6,  marc_snc,     'Marcadores de células germinales levemente elevados.', revisor=oncologo)
        crear_resultado(P[7],  HEMO, TE.HEMOGRAMA,  oncologo,      1,  hemo_critico, 'Neutropenia febril con trombocitopenia severa durante quimioterapia.')
        crear_resultado(P[7],  COAG, TE.COAGULACION, oncologo,     1,  coag_normal,  'Perfil de coagulación conservado.', revisor=oncologo)
        crear_resultado(P[8],  HEMO, TE.HEMOGRAMA,  medico_general, 12, hemo_normal, 'Recuperación hematológica en remisión.', revisor=medico_general)
        crear_resultado(P[10], MARC, TE.MARCADORES, oncologo,      3,  marc_neuro,   'Marcadores neuroendocrinos elevados, compatibles con neuroblastoma.', revisor=oncologo)
        crear_resultado(P[10], QUIM, TE.QUIMICA,    oncologo,      3,  quim_lisis,   'Ácido úrico y LDH elevados; vigilar síndrome de lisis tumoral.', revisor=oncologo)
        crear_resultado(P[11], QUIM, TE.QUIMICA,    oncologo,      4,  quim_normal,  'Función renal y hepática conservadas.', revisor=oncologo)
        crear_resultado(P[11], ORINA, TE.ORINA,     oncologo,      4,  orina_wilms,  'Proteinuria y hematuria; correlacionar con masa renal.', revisor=oncologo)
        crear_resultado(P[13], HEMO, TE.HEMOGRAMA,  oncologo,      7,  hemo_normal,  'Hemograma dentro de parámetros durante seguimiento.', revisor=oncologo)
        crear_resultado(P[14], HEMO, TE.HEMOGRAMA,  pediatra_2,    20, hemo_normal,  'Control de alta, valores normales.', revisor=pediatra_2)

        total_lab = ResultadoLaboratorio.objects.count()
        criticos_lab = ResultadoLaboratorio.objects.filter(hay_valores_criticos=True).count()
        self.stdout.write(self.style.SUCCESS(
            f'{total_lab} resultados de laboratorio creados ({criticos_lab} con valores críticos).'
        ))

        # ============================================================
        # 14. EVALUACIONES PSICOSOCIALES (los 4 niveles de riesgo)
        # ============================================================
        self.stdout.write(self.style.WARNING('Creando evaluaciones psicosociales...'))
        Psi = EvaluacionPsicosocial
        perfil_bajo = dict(
            ingreso_mensual=Psi.IngresoMensual.SUFICIENTE, tiene_seguro_medico=True,
            condicion_vivienda=Psi.CondicionVivienda.ADECUADA, apoyo_familiar=Psi.ApoyoFamiliar.BUENO,
            estado_emocional_cuidador=Psi.EstadoEmocional.ESTABLE, tipo_vivienda=Psi.TipoVivienda.PROPIA,
            impacto_emocional_paciente=Psi.ImpactoEmocional.LEVE,
        )
        perfil_medio = dict(
            ingreso_mensual=Psi.IngresoMensual.BAJO, tiene_seguro_medico=False,
            dificultad_medicamentos=Psi.Dificultad.MODERADA, condicion_vivienda=Psi.CondicionVivienda.REGULAR,
            apoyo_familiar=Psi.ApoyoFamiliar.REGULAR, tipo_vivienda=Psi.TipoVivienda.ALQUILADA,
            impacto_emocional_paciente=Psi.ImpactoEmocional.MODERADO,
        )
        perfil_alto = dict(
            ingreso_mensual=Psi.IngresoMensual.NINGUNO, tiene_seguro_medico=False,
            dificultad_medicamentos=Psi.Dificultad.SEVERA, dificultad_transporte=Psi.Dificultad.SEVERA,
            condicion_vivienda=Psi.CondicionVivienda.PRECARIA, apoyo_familiar=Psi.ApoyoFamiliar.LIMITADO,
            estado_emocional_cuidador=Psi.EstadoEmocional.VULNERABLE, tipo_vivienda=Psi.TipoVivienda.PRESTADA,
            impacto_emocional_paciente=Psi.ImpactoEmocional.MODERADO,
        )
        perfil_critico = dict(
            ingreso_mensual=Psi.IngresoMensual.NINGUNO, tiene_seguro_medico=False,
            dificultad_medicamentos=Psi.Dificultad.SEVERA, dificultad_transporte=Psi.Dificultad.SEVERA,
            condicion_vivienda=Psi.CondicionVivienda.PRECARIA, hacinamiento=True, servicios_basicos_ausentes=True,
            apoyo_familiar=Psi.ApoyoFamiliar.NINGUNO, cuidador_es_unico=True,
            estado_emocional_cuidador=Psi.EstadoEmocional.EN_CRISIS, cuidador_perdio_trabajo=True,
            cuidador_requiere_apoyo_psicologico=True, abandono_escolar=True,
            impacto_emocional_paciente=Psi.ImpactoEmocional.SEVERO, tipo_vivienda=Psi.TipoVivienda.OTRO,
        )
        _parentesco_psico = {
            PadreTutor.Parentesco.MADRE: Psi.Parentesco.MADRE,
            PadreTutor.Parentesco.PADRE: Psi.Parentesco.PADRE,
            PadreTutor.Parentesco.ABUELO: Psi.Parentesco.ABUELO_A,
            PadreTutor.Parentesco.TIO: Psi.Parentesco.TIO_A,
        }

        def crear_psico(paciente, perfil, necesidades, acciones, requiere_seg=False):
            tutor = paciente.padre_tutor
            Psi.objects.create(
                paciente=paciente,
                evaluador=trabajadora_social,
                cuidador_principal_nombre=tutor.usuario.nombre_completo,
                parentesco_cuidador=_parentesco_psico.get(tutor.parentesco, Psi.Parentesco.OTRO),
                personas_en_hogar=4,
                necesidades_identificadas=necesidades,
                acciones_recomendadas=acciones,
                observaciones='Evaluación registrada por Trabajo Social durante el acompañamiento familiar.',
                requiere_seguimiento_social=requiere_seg,
                proxima_evaluacion=(timezone.now().date() + datetime.timedelta(days=30)) if requiere_seg else None,
                **perfil,
            )

        crear_psico(P[1],  perfil_bajo,    'Familia estable, sin necesidades urgentes.', 'Mantener seguimiento de rutina.')
        crear_psico(P[3],  perfil_bajo,    'Situación socioeconómica adecuada.', 'Reforzar educación sobre la enfermedad.')
        crear_psico(P[8],  perfil_bajo,    'Red de apoyo sólida.', 'Seguimiento semestral.')
        crear_psico(P[0],  perfil_medio,   'Dificultad parcial para costear medicamentos.', 'Gestionar apoyo de farmacia solidaria.')
        crear_psico(P[5],  perfil_medio,   'Ingresos limitados y sin seguro médico.', 'Tramitar afiliación a SENASA.')
        crear_psico(P[9],  perfil_medio,   'Transporte difícil desde zona rural.', 'Coordinar apoyo de transporte al hospital.')
        crear_psico(P[10], perfil_alto,    'Sin ingresos ni seguro; vivienda precaria.', 'Activar red de asistencia social y Casa FACCI.', requiere_seg=True)
        crear_psico(P[7],  perfil_alto,    'Alta carga sobre el cuidador único.', 'Referir a apoyo psicológico y respiro familiar.', requiere_seg=True)
        crear_psico(P[4],  perfil_critico, 'Crisis socioeconómica y emocional severa.', 'Intervención social urgente y apoyo psicológico.', requiere_seg=True)
        crear_psico(P[13], perfil_critico, 'Hacinamiento y pérdida de empleo del cuidador.', 'Gestionar ayuda económica y alojamiento en Casa FACCI.', requiere_seg=True)

        conteo_psico = {n: Psi.objects.filter(nivel_riesgo=n).count() for n in ['BAJO', 'MEDIO', 'ALTO', 'CRITICO']}
        self.stdout.write(self.style.SUCCESS(
            f'{Psi.objects.count()} evaluaciones psicosociales creadas {conteo_psico}.'
        ))

        # ============================================================
        # 15. DISTRIBUCIÓN TEMPORAL (mayo → hoy)
        #     Reparte el registro de pacientes y su actividad clínica en el
        #     rango para que los reportes por período (PENCI-RD) y las
        #     tendencias mensuales muestren datos. Los campos auto_now_add
        #     (created_at, fecha_evaluacion, fecha_referencia, fecha_seguimiento)
        #     se ajustan con .update(), que los omite.
        # ============================================================
        self.stdout.write(self.style.WARNING('Distribuyendo fechas de pacientes y actividad (mayo - hoy)...'))
        fin_dt = timezone.now()
        inicio_naive = datetime.datetime(fin_dt.year, 5, 1, 8, 0)
        inicio_dt = timezone.make_aware(inicio_naive) if timezone.is_aware(fin_dt) else inicio_naive
        if inicio_dt >= fin_dt:
            inicio_dt = fin_dt - datetime.timedelta(days=60)
        span = fin_dt - inicio_dt

        # Registro de pacientes distribuido uniformemente en todo el rango.
        reg_map = {}
        n_pac = len(pacientes_list)
        for idx, pac in enumerate(pacientes_list):
            reg = inicio_dt + span * (idx / max(1, n_pac - 1))
            reg_map[pac.pk] = reg
            Paciente.objects.filter(pk=pac.pk).update(created_at=reg)

        def _fecha_act(paciente_id, paso):
            """Fecha de una actividad, situada tras el registro del paciente."""
            reg = reg_map.get(paciente_id, inicio_dt)
            disponible = fin_dt - reg
            factor = min(0.95, 0.1 + paso * 0.18)
            return reg + disponible * factor

        for c in CuestionarioCribado.objects.all():
            CuestionarioCribado.objects.filter(pk=c.pk).update(fecha_evaluacion=_fecha_act(c.paciente_id, 0))
        for r in ReferenciaMedica.objects.all():
            ReferenciaMedica.objects.filter(pk=r.pk).update(fecha_referencia=_fecha_act(r.paciente_id, 1))
        for s in SeguimientoPaciente.objects.all():
            SeguimientoPaciente.objects.filter(pk=s.pk).update(fecha_seguimiento=_fecha_act(s.paciente_id, 2))
        for d in DocumentoMedico.objects.all():
            DocumentoMedico.objects.filter(pk=d.pk).update(fecha_documento=_fecha_act(d.paciente_id, 1).date())
        for lab in ResultadoLaboratorio.objects.all():
            fm = _fecha_act(lab.paciente_id, 2)
            ResultadoLaboratorio.objects.filter(pk=lab.pk).update(
                fecha_muestra=fm.date(), fecha_resultado=(fm + datetime.timedelta(days=1)).date()
            )
        for ev in EvaluacionPsicosocial.objects.all():
            EvaluacionPsicosocial.objects.filter(pk=ev.pk).update(fecha_evaluacion=_fecha_act(ev.paciente_id, 3))

        self.stdout.write(self.style.SUCCESS(
            f'Actividad distribuida entre {inicio_dt.date()} y {fin_dt.date()}.'
        ))

        self.stdout.write(self.style.SUCCESS('La base de datos SQLite se ha poblado exitosamente.'))
