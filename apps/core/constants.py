"""
FACCI Care — Constantes de datos globales del sistema.
"""

# Provincias de la República Dominicana para registro geográfico
PROVINCIAS_RD = [
    "Santo Domingo", "Distrito Nacional", "Santiago", "San Cristóbal", "La Vega",
    "Puerto Plata", "San Pedro de Macorís", "Duarte", "La Altagracia", "La Romana",
    "San Juan", "Espaillat", "Azua", "Barahona", "Monte Plata", "Peravia",
    "Monseñor Nouel", "Valverde", "Sánchez Ramírez", "María Trinidad Sánchez",
    "Montecristi", "Samaná", "Bahoruco", "Hermanas Mirabal", "El Seibo",
    "Hato Mayor", "Dajabón", "Santiago Rodríguez", "San José de Ocoa",
    "Elias Piña", "Independencia", "Pedernales"
]

# Niveles de severidad para el Cribado FACCI
NIVELES_ALERTA = {
    'BAJO': {'color': 'success', 'label': 'Riesgo Bajo'},
    'MEDIO': {'color': 'warning', 'label': 'Riesgo Moderado'},
    'ALTO': {'color': 'error', 'label': 'Alerta Roja / Riesgo Alto'}
}

# Signos vitales — umbrales orientativos para el Módulo de Seguimiento Clínico (CU-19).
# Sirven para generar una advertencia de "valores atípicos" (excepción E.1), no son
# percentiles clínicos oficiales (OMS/CDC) ni sustituyen el criterio médico. Ajustar
# aquí si el equipo clínico del proyecto define rangos más precisos.
TEMPERATURA_FIEBRE_C = 38.0
TEMPERATURA_HIPOTERMIA_C = 35.0

# Rangos orientativos de tensión arterial (mmHg) por banda etaria pediátrica.
# Formato: (edad_maxima_meses, sistolica_min, sistolica_max, diastolica_min, diastolica_max, etiqueta)
RANGOS_TENSION_ARTERIAL_PEDIATRICA = [
    (12,  70,  100, 50, 65, 'lactante (0-1 año)'),
    (60,  80,  110, 55, 70, 'preescolar (1-5 años)'),
    (144, 85,  120, 55, 80, 'escolar (6-12 años)'),
    (216, 95,  135, 60, 85, 'adolescente (13-18 años)'),
]

RESTRICCIONES_GENERALES = [
    'No administrar ibuprofeno ni aspirina sin consultar al médico',
    'Evitar contacto con personas resfriadas o con varicela',
    'No realizar vacunaciones sin autorización médica',
    'Evitar exposición solar prolongada sin protector',
]
