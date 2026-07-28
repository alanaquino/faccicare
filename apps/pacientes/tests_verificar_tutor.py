from django.test import TestCase
from django.urls import reverse

from apps.auth_app.models import CustomUser
from apps.padres.models import PadreTutor
from apps.pacientes.models import Paciente


class VerificarTutorCedulaTests(TestCase):
    def setUp(self):
        self.medico = CustomUser.objects.create_user(
            username="dra.medico",
            password="clave12345",
            rol=CustomUser.Rol.MEDICO,
        )
        self.url = reverse("pacientes:verificar_tutor_cedula")

    def test_requiere_login(self):
        response = self.client.get(self.url, {"cedula": "001-1234567-8"})
        self.assertEqual(response.status_code, 302)

    def test_rol_oncologo_no_autorizado(self):
        oncologo = CustomUser.objects.create_user(
            username="dr.oncologo",
            password="clave12345",
            rol=CustomUser.Rol.ONCOLOGO,
        )
        self.client.force_login(oncologo)
        response = self.client.get(self.url, {"cedula": "001-1234567-8"})
        self.assertEqual(response.status_code, 403)

    def test_rol_padre_tutor_no_autorizado(self):
        """PADRE_TUTOR nunca llega a la vista: ControlAccesoPorRolMiddleware lo redirige antes."""
        tutor_user = CustomUser.objects.create_user(
            username="tutor.bloqueado",
            password="clave12345",
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        self.client.force_login(tutor_user)
        response = self.client.get(self.url, {"cedula": "001-1234567-8"})
        self.assertEqual(response.status_code, 302)

    def test_cedula_mal_formada(self):
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": "123"})
        self.assertEqual(response.json(), {"match": False})

    def test_sin_coincidencia(self):
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": "001-1234567-8"})
        self.assertEqual(response.json(), {"match": False})

    def test_tutor_valido_con_perfil(self):
        usuario_tutor = CustomUser.objects.create_user(
            username="juan.perez",
            password="clave12345",
            first_name="Juan",
            last_name="Perez",
            email="juan@example.com",
            telefono="809-555-0000",
            cedula="001-1234567-8",
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        PadreTutor.objects.create(
            usuario=usuario_tutor,
            parentesco=PadreTutor.Parentesco.PADRE,
            direccion="Calle Falsa 123",
            provincia="Santo Domingo",
            municipio="Santo Domingo Este",
        )
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": "001-1234567-8"})
        self.assertEqual(response.json(), {
            "match": True,
            "valido": True,
            "nombre": "Juan Perez",
            "telefono": "809-555-0000",
            "email": "juan@example.com",
            "direccion": "Calle Falsa 123",
            "parentesco": PadreTutor.Parentesco.PADRE,
            "pacientes_asignados": 0,
        })

    def test_tutor_valido_sin_perfil_aun(self):
        CustomUser.objects.create_user(
            username="ana.gomez",
            password="clave12345",
            first_name="Ana",
            last_name="Gomez",
            cedula="002-1234567-9",
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": "002-1234567-9"})
        data = response.json()
        self.assertTrue(data["match"])
        self.assertTrue(data["valido"])
        self.assertEqual(data["direccion"], "")
        self.assertEqual(data["parentesco"], "")
        self.assertEqual(data["pacientes_asignados"], 0)

    def test_cedula_de_personal_no_valida(self):
        CustomUser.objects.create_user(
            username="dr.staff",
            password="clave12345",
            cedula="003-1234567-0",
            rol=CustomUser.Rol.ENFERMERA,
        )
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": "003-1234567-0"})
        self.assertEqual(response.json(), {
            "match": True,
            "valido": False,
            "mensaje": "Esta cédula pertenece a una cuenta de personal y no puede usarse como tutor.",
        })

    def test_cedula_con_espacios_y_guiones_se_normaliza(self):
        usuario_tutor = CustomUser.objects.create_user(
            username="pedro.diaz",
            password="clave12345",
            first_name="Pedro",
            last_name="Diaz",
            cedula="004-1234567-1",
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": " 004 1234567 1 "})
        self.assertTrue(response.json()["match"])

    def test_pacientes_asignados_refleja_conteo_real(self):
        usuario_tutor = CustomUser.objects.create_user(
            username="carla.reyes",
            password="clave12345",
            first_name="Carla",
            last_name="Reyes",
            cedula="005-1234567-2",
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        tutor = PadreTutor.objects.create(
            usuario=usuario_tutor,
            parentesco=PadreTutor.Parentesco.MADRE,
            direccion="Calle Uno 1",
            provincia="Santo Domingo",
            municipio="Santo Domingo Este",
        )
        Paciente.objects.create(
            codigo_paciente="FACCI-TEST-0001",
            nombres="Paciente",
            apellidos="Uno",
            fecha_nacimiento="2015-01-01",
            sexo=Paciente.Sexo.MASCULINO,
            provincia="Santo Domingo",
            padre_tutor=tutor,
        )
        self.client.force_login(self.medico)
        response = self.client.get(self.url, {"cedula": "005-1234567-2"})
        self.assertEqual(response.json()["pacientes_asignados"], 1)
