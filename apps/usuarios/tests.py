from django.test import TestCase
from django.urls import reverse

from apps.auth_app.models import CustomUser
from apps.core.models import CentroSalud, LogActividad
from apps.padres.models import PadreTutor


class AdminUserEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = CustomUser.objects.create_user(
            username='admin_cu04',
            password='ClaveAdmin!456',
            first_name='Ana',
            email='admin@example.com',
            rol=CustomUser.Rol.ADMIN,
        )
        cls.centro = CentroSalud.objects.create(
            nombre='Hospital de Prueba',
            provincia='Santiago',
        )
        cls.medico = CustomUser.objects.create_user(
            username='medico_cu04',
            password='ClaveMedico!456',
            first_name='Carlos',
            email='carlos@example.com',
            rol=CustomUser.Rol.MEDICO,
        )
        cls.no_admin = CustomUser.objects.create_user(
            username='enfermera_cu04',
            password='ClaveEnfermera!456',
            rol=CustomUser.Rol.ENFERMERA,
        )
        cls.tutor_user = CustomUser.objects.create_user(
            username='tutor_cu04',
            password='ClaveTutor!456',
            first_name='Marta',
            rol=CustomUser.Rol.PADRE_TUTOR,
        )
        cls.tutor = PadreTutor.objects.create(
            usuario=cls.tutor_user,
            parentesco=PadreTutor.Parentesco.MADRE,
            direccion='Dirección anterior',
            provincia='Santo Domingo',
            municipio='Distrito Nacional',
        )

    def _post_data(self, usuario, **changes):
        data = {
            'first_name': usuario.first_name or 'Nombre',
            'last_name': usuario.last_name,
            'username': usuario.username,
            'email': usuario.email,
            'tipo_documento': usuario.tipo_documento,
            'cedula': usuario.cedula or '',
            'telefono': usuario.telefono or '',
            'rol': usuario.rol,
            'especialidad': usuario.especialidad,
            'centro_medico': str(usuario.centro_medico_id or ''),
            'is_active': 'on' if usuario.is_active else '',
        }
        data.update(changes)
        return data

    def test_management_only_lists_system_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('usuarios:gestion'))

        listed_ids = set(response.context['usuarios'].values_list('pk', flat=True))
        self.assertIn(self.medico.pk, listed_ids)
        self.assertNotIn(self.tutor_user.pk, listed_ids)
        self.assertNotContains(response, 'value="PADRE_TUTOR"')
        self.assertEqual(response.context['total'], 3)

    def test_management_edit_link_opens_selected_user(self):
        self.client.force_login(self.admin)
        edit_url = reverse('usuarios:editar', kwargs={'pk': self.medico.pk})
        list_response = self.client.get(reverse('usuarios:gestion'))
        self.assertContains(list_response, edit_url)

        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.medico.username)

    def test_admin_can_edit_account_and_reset_password(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('usuarios:editar', kwargs={'pk': self.medico.pk}),
            self._post_data(
                self.medico,
                first_name='Carlos actualizado',
                last_name='Rodríguez',
                username='carlos.actualizado',
                email='nuevo@example.com',
                tipo_documento=CustomUser.TipoDocumento.PASAPORTE,
                cedula='P-123456',
                telefono='809-555-0199',
                rol=CustomUser.Rol.PEDIATRA,
                especialidad='Pediatría',
                centro_medico=str(self.centro.pk),
                password1='NuevaClaveSegura!456',
                password2='NuevaClaveSegura!456',
            ),
        )
        self.assertRedirects(response, reverse('usuarios:gestion'))

        self.medico.refresh_from_db()
        self.assertEqual(self.medico.username, 'carlos.actualizado')
        self.assertEqual(self.medico.first_name, 'Carlos actualizado')
        self.assertEqual(self.medico.rol, CustomUser.Rol.PEDIATRA)
        self.assertEqual(self.medico.centro_medico, self.centro)
        self.assertEqual(self.medico.telefono, '809-555-0199')
        self.assertTrue(self.medico.check_password('NuevaClaveSegura!456'))
        self.assertTrue(LogActividad.objects.filter(
            usuario=self.admin,
            accion='Editar usuario',
            objeto_id=str(self.medico.pk),
        ).exists())

    def test_admin_can_edit_parent_profile_data_by_direct_url(self):
        self.client.force_login(self.admin)
        data = self._post_data(
            self.tutor_user,
            parentesco=PadreTutor.Parentesco.TUTOR,
            nacionalidad='Dominicana',
            direccion='Nueva dirección',
            provincia='La Vega',
            municipio='Concepción de La Vega',
            ocupacion='Docente',
            contacto_emergencia='Juan Pérez',
            telefono_emergencia='809-555-0101',
            estado_civil=PadreTutor.EstadoCivil.CASADO,
            cantidad_hijos='2',
            ingresos_aproximados='RD$20,000-30,000',
        )
        response = self.client.post(
            reverse('usuarios:editar', kwargs={'pk': self.tutor_user.pk}),
            data,
        )
        self.assertRedirects(response, reverse('usuarios:gestion'))

        self.tutor.refresh_from_db()
        self.assertEqual(self.tutor.direccion, 'Nueva dirección')
        self.assertEqual(self.tutor.provincia, 'La Vega')
        self.assertEqual(self.tutor.parentesco, PadreTutor.Parentesco.TUTOR)
        self.assertEqual(self.tutor.cantidad_hijos, 2)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('usuarios:editar', kwargs={'pk': self.medico.pk}),
            self._post_data(self.medico, email=self.admin.email.upper()),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El correo electrónico ya está registrado.')

    def test_non_admin_cannot_edit_another_user(self):
        self.client.force_login(self.no_admin)
        response = self.client.get(
            reverse('usuarios:editar', kwargs={'pk': self.medico.pk}),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    def test_admin_cannot_demote_or_deactivate_self(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('usuarios:editar', kwargs={'pk': self.admin.pk}),
            self._post_data(
                self.admin,
                rol=CustomUser.Rol.MEDICO,
                is_active='',
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No puedes quitarte el rol de administrador.')
        self.assertContains(response, 'No puedes desactivar tu propia cuenta.')

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol, CustomUser.Rol.ADMIN)
        self.assertTrue(self.admin.is_active)
