import datetime

from django.test import TestCase
from django.urls import reverse

from apps.alojamiento.models import EstanciaFamiliar, HabitacionCasa
from apps.auth_app.models import CustomUser
from apps.cribado.models import CuestionarioCribado
from apps.documentos.models import DocumentoMedico
from apps.pacientes.models import Paciente
from apps.padres.models import PadreTutor, ReporteSintoma
from apps.referencias.models import ReferenciaMedica
from apps.seguimiento.models import IndicacionMedica


class UseCaseAlignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = CustomUser.objects.create_user(
            username='admin_test',
            password='password123',
            rol=CustomUser.Rol.ADMIN,
            email='admin@example.com',
        )
        cls.medico = CustomUser.objects.create_user(
            username='medico_test',
            password='password123',
            rol=CustomUser.Rol.MEDICO,
        )
        cls.oncologo = CustomUser.objects.create_user(
            username='oncologo_test',
            password='password123',
            rol=CustomUser.Rol.ONCOLOGO,
        )
        cls.enfermera = CustomUser.objects.create_user(
            username='enfermera_test',
            password='password123',
            rol=CustomUser.Rol.ENFERMERA,
        )
        cls.coordinador = CustomUser.objects.create_user(
            username='coordinador_test',
            password='password123',
            rol=CustomUser.Rol.PERSONAL_FACCI,
        )
        cls.tutor_user = CustomUser.objects.create_user(
            username='tutor_test',
            password='1234',
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        cls.tutor = PadreTutor.objects.create(
            usuario=cls.tutor_user,
            direccion='Santo Domingo',
            provincia='Santo Domingo',
            municipio='Distrito Nacional',
        )
        cls.paciente = Paciente.objects.create(
            codigo_paciente='FACCI-20260001',
            nombres='Paciente',
            apellidos='Prueba',
            fecha_nacimiento=datetime.date(2018, 1, 1),
            sexo=Paciente.Sexo.MASCULINO,
            provincia='Santo Domingo',
            padre_tutor=cls.tutor,
            medico_asignado=cls.medico,
            creado_por=cls.medico,
        )
        cls.referencia = ReferenciaMedica.objects.create(
            paciente=cls.paciente,
            medico_referente=cls.medico,
            especialista_destino=cls.oncologo,
            motivo_referencia='Evaluación especializada',
        )

    def test_inactive_user_gets_specific_login_message(self):
        user = CustomUser.objects.create_user(
            username='inactivo',
            password='password123',
            rol=CustomUser.Rol.MEDICO,
            is_active=False,
        )
        response = self.client.post(reverse('auth_app:login'), {
            'username': user.username,
            'password': 'password123',
        })
        self.assertContains(response, 'La cuenta está deshabilitada')

    def test_duplicate_email_is_rejected_when_admin_creates_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('usuarios:nuevo'), {
            'username': 'otro_usuario',
            'first_name': 'Otro',
            'email': self.admin.email.upper(),
            'password': 'password123',
            'rol': CustomUser.Rol.MEDICO,
        })
        self.assertContains(response, 'El correo electrónico ya está registrado')
        self.assertFalse(CustomUser.objects.filter(username='otro_usuario').exists())

    def test_patient_edit_permissions_follow_clinical_responsibility(self):
        from apps.pacientes.views import _puede_editar_paciente

        self.assertTrue(_puede_editar_paciente(self.admin, self.paciente))
        self.assertTrue(_puede_editar_paciente(self.medico, self.paciente))
        self.assertTrue(_puede_editar_paciente(self.oncologo, self.paciente))
        self.assertFalse(_puede_editar_paciente(self.enfermera, self.paciente))
        self.assertFalse(_puede_editar_paciente(self.coordinador, self.paciente))

    def test_admin_can_open_screening_edit_view(self):
        cribado = CuestionarioCribado.objects.create(
            paciente=self.paciente,
            medico=self.medico,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('cribado:editar', kwargs={'pk': cribado.pk}))
        self.assertEqual(response.status_code, 200)

    def test_coordinator_has_read_only_reference_access(self):
        self.assertTrue(self.coordinador.puede_ver_referencias)
        self.assertFalse(self.coordinador.puede_gestionar_referencias)

    def test_parent_cannot_submit_empty_symptom_report(self):
        self.client.force_login(self.tutor_user)
        response = self.client.post(reverse('padres:reportar_sintomas'), {
            'fecha_inicio': '2026-07-27',
            'gravedad': ReporteSintoma.Gravedad.LEVE,
            'descripcion': '',
        })
        self.assertRedirects(response, reverse('padres:reportar_sintomas'))
        self.assertFalse(ReporteSintoma.objects.exists())

    def test_parent_only_sees_visible_indications_and_documents(self):
        IndicacionMedica.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            titulo='Indicación visible',
            descripcion='Visible para la familia',
            visible_padre=True,
        )
        IndicacionMedica.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            titulo='Indicación interna',
            descripcion='Solo para personal clínico',
            visible_padre=False,
        )
        DocumentoMedico.objects.create(
            paciente=self.paciente,
            subido_por=self.medico,
            tipo_documento=DocumentoMedico.TipoDocumento.INFORME_MEDICO,
            archivo='documentos/visible.pdf',
            fecha_documento=datetime.date.today(),
            visible_padre=True,
        )
        DocumentoMedico.objects.create(
            paciente=self.paciente,
            subido_por=self.medico,
            tipo_documento=DocumentoMedico.TipoDocumento.BIOPSIA,
            archivo='documentos/interno.pdf',
            fecha_documento=datetime.date.today(),
            visible_padre=False,
        )

        self.client.force_login(self.tutor_user)
        indicaciones = self.client.get(reverse('padres:indicaciones'))
        self.assertContains(indicaciones, 'Indicación visible')
        self.assertNotContains(indicaciones, 'Indicación interna')

        documentos = self.client.get(reverse('padres:documentos'))
        self.assertContains(documentos, 'visible.pdf')
        self.assertNotContains(documentos, 'interno.pdf')

    def test_active_stay_can_be_edited(self):
        habitacion_inicial = HabitacionCasa.objects.create(nombre='A', capacidad=2)
        habitacion_nueva = HabitacionCasa.objects.create(nombre='B', capacidad=2)
        estancia = EstanciaFamiliar.objects.create(
            paciente=self.paciente,
            habitacion=habitacion_inicial,
            acompanante_nombre='Tutor Inicial',
            motivo=EstanciaFamiliar.MotivoEstancia.CONSULTA,
            fecha_ingreso=datetime.date(2026, 7, 20),
            registrado_por=self.coordinador,
        )
        self.client.force_login(self.coordinador)
        response = self.client.post(reverse('alojamiento:editar', kwargs={'pk': estancia.pk}), {
            'habitacion': str(habitacion_nueva.pk),
            'acompanante_nombre': 'Tutor Actualizado',
            'acompanante_parentesco': 'Madre',
            'acompanante_telefono': '809-555-0000',
            'motivo': EstanciaFamiliar.MotivoEstancia.QUIMIOTERAPIA,
            'fecha_ingreso': '2026-07-20',
            'fecha_egreso_prevista': '2026-07-30',
            'observaciones': 'Actualizada',
        })
        self.assertRedirects(
            response,
            reverse('alojamiento:detalle', kwargs={'pk': estancia.pk}),
        )
        estancia.refresh_from_db()
        self.assertEqual(estancia.habitacion, habitacion_nueva)
        self.assertEqual(estancia.acompanante_nombre, 'Tutor Actualizado')

    def test_export_screening_without_records_shows_info(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('cribado:exportar'))
        self.assertRedirects(response, reverse('cribado:lista'))

    def test_past_appointment_date_is_rejected(self):
        self.client.force_login(self.medico)
        response = self.client.post(
            reverse('pacientes:expediente', kwargs={'pk': self.paciente.pk}),
            {
                'action': 'registrar_seguimiento',
                'proxima_fecha_seguimiento': '2020-01-01T10:00',
                'observaciones': 'Prueba fecha pasada',
            }
        )
        self.assertRedirects(response, f"{reverse('pacientes:expediente', kwargs={'pk': self.paciente.pk})}?tab=resumen")

    def test_deactivate_indication_sets_active_false(self):
        ind = IndicacionMedica.objects.create(
            paciente=self.paciente,
            medico=self.medico,
            titulo='Indicación a desactivar',
            descripcion='Prueba',
        )
        self.client.force_login(self.medico)
        response = self.client.post(
            reverse('pacientes:expediente', kwargs={'pk': self.paciente.pk}),
            {
                'action': 'desactivar_indicacion',
                'indicacion_id': str(ind.pk),
            }
        )
        self.assertRedirects(response, f"{reverse('pacientes:expediente', kwargs={'pk': self.paciente.pk})}?tab=indicaciones")
        ind.refresh_from_db()
        self.assertFalse(ind.activa)

    def test_document_correction_requires_observations(self):
        doc = DocumentoMedico.objects.create(
            paciente=self.paciente,
            subido_por=self.medico,
            tipo_documento=DocumentoMedico.TipoDocumento.INFORME_MEDICO,
            archivo='documentos/test.pdf',
            fecha_documento=datetime.date.today(),
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('documentos:cambiar_estado', kwargs={'pk': doc.pk}),
            {
                'estado': DocumentoMedico.EstadoDocumento.CORRECCION,
                'observaciones': '',
            }
        )
        self.assertRedirects(response, reverse('documentos:detalle', kwargs={'pk': doc.pk}))
        doc.refresh_from_db()
        self.assertNotEqual(doc.estado, DocumentoMedico.EstadoDocumento.CORRECCION)
