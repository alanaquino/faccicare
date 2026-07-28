from django.test import TestCase

from apps.core.models import CentroSalud
from apps.core.centros_matching import match_centro_por_nombre


class MatchCentroPorNombreTests(TestCase):
    def setUp(self):
        self.central = CentroSalud.objects.create(nombre='Hospital Pediátrico Central')

    def test_match_exacto(self):
        self.assertEqual(match_centro_por_nombre(CentroSalud, 'Hospital Pediátrico Central'), self.central)

    def test_match_case_insensitive_y_espacios(self):
        self.assertEqual(match_centro_por_nombre(CentroSalud, '  hospital pediátrico central '), self.central)

    def test_sin_coincidencia_retorna_none(self):
        self.assertIsNone(match_centro_por_nombre(CentroSalud, 'Clínica Inexistente'))

    def test_vacio_o_none_retorna_none(self):
        self.assertIsNone(match_centro_por_nombre(CentroSalud, ''))
        self.assertIsNone(match_centro_por_nombre(CentroSalud, None))
        self.assertIsNone(match_centro_por_nombre(CentroSalud, '   '))
