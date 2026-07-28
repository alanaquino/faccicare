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

RESTRICCIONES_GENERALES = [
    'No administrar ibuprofeno ni aspirina sin consultar al médico',
    'Evitar contacto con personas resfriadas o con varicela',
    'No realizar vacunaciones sin autorización médica',
    'Evitar exposición solar prolongada sin protector',
]
