import sys
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from apps.pacientes.models import Paciente
from apps.cribado.models import CuestionarioCribado
from apps.referencias.models import ReferenciaMedica
from apps.padres.models import PadreTutor

User = get_user_model()

# Setup test data
medico = User.objects.filter(rol=User.Rol.MEDICO).first()
if not medico:
    medico = User.objects.create_user(username='medicotest', password='123', rol=User.Rol.MEDICO)

tutor_user = User.objects.filter(rol=User.Rol.PADRE_TUTOR).first()
if not tutor_user:
    tutor_user = User.objects.create_user(username='tutortest', password='123', rol=User.Rol.PADRE_TUTOR)

tutor, _ = PadreTutor.objects.get_or_create(usuario=tutor_user, defaults={'direccion':'SD', 'provincia':'SD', 'municipio':'DN'})
paciente, _ = Paciente.objects.get_or_create(codigo_paciente='FACCI-TEST-1', defaults={'nombres':'P', 'apellidos':'T', 'sexo':'M', 'padre_tutor':tutor, 'medico_asignado':medico, 'creado_por':medico, 'fecha_nacimiento': '2010-01-01'})

# Crear un nuevo cribado
cribado = CuestionarioCribado.objects.create(paciente=paciente, medico=medico, nivel_riesgo='ALTO', dolor_cabeza=True)

# Crear la primera referencia directamente
ReferenciaMedica.objects.create(paciente=paciente, cuestionario=cribado, medico_referente=medico, motivo_referencia='Primera Ref')

client = Client()
client.force_login(medico)

print("\n--- INTENTANDO CREAR REFERENCIA DUPLICADA (Excepcion E.1) ---")
# Intentar acceder a la vista de creacion con el mismo cribado_id (GET)
response_get = client.get(reverse('referencias:crear') + f'?cribado={cribado.id}')
print(f"GET Status Code: {response_get.status_code}")
if response_get.status_code == 302:
    print(f"Redirige a: {response_get.url}")
    messages = list(get_messages(response_get.wsgi_request))
    for m in messages:
        print(f"Mensaje GET: [{m.level_tag}] {m.message}")

# Intentar POST
response_post = client.post(reverse('referencias:crear'), {'cribado_id': str(cribado.id), 'motivo_referencia': 'Intento 2'})
print(f"POST Status Code: {response_post.status_code}")
if response_post.status_code == 302:
    print(f"Redirige a: {response_post.url}")
    messages = list(get_messages(response_post.wsgi_request))
    for m in messages:
        print(f"Mensaje POST: [{m.level_tag}] {m.message}")

# Verificar si se creo una segunda referencia
num_refs = ReferenciaMedica.objects.filter(cuestionario=cribado).count()
print(f"Numero de referencias asociadas al cribado: {num_refs}")

if num_refs == 1:
    print("Excepcion E.1 FUNCIONA CORRECTAMENTE: Se bloqueo la duplicacion.")
else:
    print("FALLO: Se permitio la duplicacion.")
