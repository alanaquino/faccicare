# FACCI Care — Sistema de Detección Temprana de Cáncer Pediátrico

**FACCI Care** es una aplicación web desarrollada con **Python**, **Django** y **Django REST Framework** para apoyar la **detección temprana, referencia oportuna y seguimiento clínico** de pacientes pediátricos con posibles signos de riesgo oncológico, en el contexto de la República Dominicana.

Este proyecto forma parte de una propuesta académica de monográfico enfocada en la atención pediátrica y el acompañamiento a las familias.

---

## Descripción del Proyecto

FACCI Care integra en un solo sistema:

- El **portal clínico** (personal médico y equipo FACCI), con dashboard por rol, expediente del paciente, cribado, referencias, seguimiento e indicaciones médicas.
- El **portal de padres/tutores**, donde la familia consulta el estado del paciente, las indicaciones, el seguimiento, los recursos educativos y puede reportar síntomas.
- La **gestión operativa de FACCI**: evaluaciones psicosociales, administración de la Casa FACCI (alojamiento) y reportes estadísticos (PENCI-RD).

El acceso a cada módulo se controla mediante una **matriz de permisos por rol** definida en el modelo de usuario, que mantiene sincronizados el menú lateral y las vistas.

---

## Objetivo General

Desarrollar un sistema clínico que permita gestionar el cribado, las referencias médicas, el seguimiento clínico, las alertas, la documentación y el acompañamiento a las familias, para apoyar el monitoreo y la atención temprana de pacientes pediátricos.

---

## Funcionalidades Principales

- Registro y administración de pacientes pediátricos y sus tutores.
- Cuestionario de **cribado** con clasificación de nivel de riesgo.
- Gestión de **referencias médicas** (MSP) con control de prioridad/urgencia y generación de PDF.
- **Seguimiento clínico** por fases de protocolo e **indicaciones médicas**.
- Gestión de **documentos médicos** (informes, laboratorio) por paciente.
- Módulo **psicosocial** (Trabajo Social / Psicología).
- Administración de la **Casa FACCI** (alojamiento de familias).
- **Alertas clínicas** y notificaciones.
- **Reportes estadísticos** y matrices operativas (exportación).
- Gestión de **centros de salud**.
- **Portal de padres/tutores** con acceso por código de paciente + PIN.
- **API REST** protegida por autenticación (JWT / sesión).
- Panel de administración vía **Django Admin**.

---

## Tecnologías Utilizadas

- **Python** / **Django 6.0**
- **Django REST Framework** + **SimpleJWT** (API)
- **SQLite** (desarrollo) / **MySQL** (producción, opcional vía `DB_ENGINE`)
- **Argon2** para el hash de contraseñas
- **Fernet (cryptography)** para el cifrado de datos sensibles
- **ReportLab** (PDF) y **openpyxl** (Excel) para reportes
- **Pillow** para imágenes / fotos de perfil
- Plantillas Django + **Django Admin**
- Git / GitHub

---

## Instalación y Puesta en Marcha (desarrollo)

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones
python manage.py migrate

# 4. Poblar datos de prueba (solo funciona con DEBUG=True)
python manage.py seed_data

# 5. Levantar el servidor de desarrollo
python manage.py runserver
```

- Portal clínico: `http://127.0.0.1:8000/login/`
- Portal de padres: `http://127.0.0.1:8000/` → login de padres (código de paciente + PIN)
- Django Admin: `http://127.0.0.1:8000/admin/`

### Variables de entorno relevantes

La configuración usa `python-decouple`; puedes definir un archivo `.env`:

| Variable | Descripción | Valor por defecto (dev) |
|---|---|---|
| `DJANGO_DEBUG` | Modo depuración | `True` |
| `DJANGO_SECRET_KEY` | Clave secreta de Django | clave insegura de dev |
| `DB_ENGINE` | Motor de BD (`sqlite3` o `mysql`) | `sqlite3` |
| `FACCI_ENCRYPTION_KEY` | Clave Fernet para cifrar datos sensibles | vacío |
| `SEED_ADMIN_PASSWORD` | Contraseña del admin en `seed_data` | `adminpassword123` |
| `SEED_DEFAULT_PASSWORD` | Contraseña del resto de usuarios de prueba | `password123` |

---

## Roles y Usuarios de Prueba

El comando `python manage.py seed_data` crea los siguientes usuarios. Las contraseñas provienen de las variables `SEED_ADMIN_PASSWORD` / `SEED_DEFAULT_PASSWORD`; los valores mostrados son los que se usan por defecto en **DEBUG**.

> ⚠️ Estas credenciales son **solo para desarrollo/pruebas**. `seed_data` no se ejecuta con `DEBUG=False`.

| Rol | Usuario(s) | Contraseña | Portal de acceso |
|---|---|---|---|
| **Administrador** (`ADMIN`) | `admin` (Ana Flores) | `adminpassword123` | Login clínico |
| **Pediatra** (`PEDIATRA`) | `jmartinez` (Juan Martínez), `elopez` (Elena López) | `password123` | Login clínico |
| **Oncólogo** (`ONCOLOGO`) | `evargas` (Elena Vargas) | `password123` | Login clínico |
| **Médico General** (`MEDICO`) | `rgomez` (Roberto Gómez) | `password123` | Login clínico |
| **Coordinador FACCI** (`PERSONAL_FACCI`) | `msantos` (María Santos) | `password123` | Login clínico |
| **Trabajo Social / Psicología** (`TRABAJADORA_SOCIAL`) | `lperez` (Laura Pérez) | `password123` | Login clínico |
| **Enfermera / Técnico** (`ENFERMERA`) | `cgonzalez` (Carmen González) | `password123` | Login clínico |
| **Padre / Tutor** (`PADRE_TUTOR`) | `carlos_r`, `maria_v`, `ana_p`, `pedro_d`, `luis_m` | PIN: `password123` | Portal de padres |

**Portal de padres:** los tutores ingresan con el **código de paciente** (ej. `FACCI-MR01`) o su correo, más el **PIN** (internamente es su contraseña).

---

## Matriz de Permisos por Rol

Qué puede **ver** y **hacer** cada rol, y **qué registros** ve (solo los propios/asignados o todos). Fuente de verdad: la matriz de acceso en `apps/auth_app/models.py` y el filtrado de las vistas.

| Rol | Qué puede ver | Qué puede hacer (escritura) | Qué NO puede ver / hacer | Alcance de datos (qué registros ve) |
|---|---|---|---|---|
| **Administrador** | Todo: pacientes, alertas, cribado, referencias, seguimiento, indicaciones, laboratorio, psicosocial, Casa FACCI, reportes, matrices y gestión de usuarios | Todo: gestionar referencias, indicaciones, psicosocial y alojamiento; subir documentos; **generar/exportar reportes**; administrar usuarios | **No puede crear cribados** (exclusivo de Médico General y Pediatra). Sin otras restricciones | **Todos** los registros (visión global) |
| **Pediatra** | Pacientes, alertas, cribado, referencias, seguimiento, indicaciones, laboratorio, Casa FACCI (lectura), reportes | **Crear cribados**, gestionar referencias e indicaciones, subir documentos | No ve ni gestiona **psicosocial**; no ve **matrices**; no gestiona **Casa FACCI**; no **genera/exporta reportes** | **Solo los que creó o tiene asignados** (`medico_asignado` / `creado_por`); en referencias, además las que él emitió |
| **Médico General** | Igual que Pediatra | **Crear cribados**, gestionar referencias e indicaciones, subir documentos | Igual que Pediatra (no psicosocial, no matrices, no Casa FACCI, no genera reportes) | **Solo los que creó o tiene asignados** (igual que Pediatra) |
| **Oncólogo** | Pacientes, alertas, cribado (lectura), referencias, seguimiento, indicaciones, laboratorio, Casa FACCI (lectura), reportes | Gestionar referencias e indicaciones, subir documentos | **No crea cribados** (solo lectura); no ve ni gestiona **psicosocial**; no ve **matrices**; no gestiona **Casa FACCI**; no **genera reportes** | **Solo los que le han sido referidos/asignados** como especialista destino |
| **Enfermera / Técnico** | Pacientes, alertas, cribado, referencias (lectura), seguimiento (lectura), indicaciones (lectura), laboratorio, reportes | Subir documentos, registrar en laboratorio | **No crea cribados**; no **gestiona referencias ni indicaciones** (solo lectura); no ve **psicosocial**, **Casa FACCI** ni **matrices**; no **genera reportes** | **Solo los que creó o tiene asignados** (`medico_asignado` / `creado_por`) |
| **Trabajo Social / Psicología** | Pacientes (lectura), alertas, referencias/seguimiento (lectura), **psicosocial**, Casa FACCI, reportes | **Gestionar evaluaciones psicosociales**, gestionar Casa FACCI, subir documentos | No ve **cribado, indicaciones ni laboratorio**; no ve **matrices**; no **crea cribados**; no **gestiona referencias ni indicaciones** (solo lectura); no **genera reportes** | **Todos** los registros (visión global para coordinación) |
| **Coordinador FACCI** | Pacientes y referencias (lectura), **psicosocial**, Casa FACCI, reportes, **matrices operativas** | **Gestionar Casa FACCI**, **generar/exportar reportes** | No ve **alertas, cribado, seguimiento, indicaciones ni laboratorio**; no **crea cribados**; no **gestiona referencias/indicaciones**; no **edita psicosocial** (solo lectura); no **sube documentos** | **Todos** los registros (visión global para coordinación) |
| **Padre / Tutor** | Su portal: estado del paciente, indicaciones y documentos compartidos, seguimiento, recursos educativos | **Reportar síntomas** y subir documentos de su hijo/a | No accede a **ningún módulo del personal** (pacientes de otros, cribado, referencias, seguimiento interno, laboratorio, psicosocial, Casa FACCI, reportes, matrices, usuarios) | **Solo su(s) propio(s) paciente(s)** (su hijo/a a cargo) |

**Notas clave:**
- **Alcance de datos**: los roles clínicos de detección (Pediatra, Médico) y Enfermera solo ven los pacientes/registros que **crearon** o que tienen **asignados**; el Oncólogo ve únicamente los que le fueron **referidos**; Administrador, Coordinador FACCI y Trabajo Social tienen **visión global** de todos los registros; el Padre/Tutor solo ve **su propio paciente**.
- **Crear cribados**: solo Médico General y Pediatra (ni siquiera el Administrador puede crearlos).
- **Generar/exportar reportes** (PENCI-RD): solo Administrador y Coordinador FACCI; el resto los ve en solo lectura.
- **Matrices operativas**: solo Administrador y Coordinador FACCI.
- **Módulo psicosocial**: solo equipo FACCI (Coordinador + Trabajo Social) y Administrador.

---

## Flujo de Trabajo y Roles

FACCI Care sigue la ruta de la **detección temprana de cáncer pediátrico**. El estado del paciente avanza así:

```
Sospechoso → Referido → En estudio → Confirmado / Descartado → En tratamiento → En remisión → Finalizado
```

Y las etapas del sistema encadenan a los roles:

```
1. Cribado (detección)  →  2. Referencia (derivación)  →  3. Seguimiento clínico (tratamiento por fases)
        →  4. Indicaciones (pautas para la familia)  →  5. Psicosocial + Casa FACCI (acompañamiento)
        →  6. Reportes (estadística / PENCI-RD)
```

En paralelo, el **portal de padres** mantiene informada a la familia.

### 1. Médico General / Pediatra — *Detección y puerta de entrada*

Son quienes **inician el caso**.

1. Registran al paciente y a su tutor → el paciente queda asociado a ellos (`medico_asignado` / `creado_por`).
2. Aplican el **cuestionario de cribado** (fiebre persistente, dolor de huesos, palidez, moretones, ganglios…). El sistema calcula el **nivel de riesgo** (`Bajo` / `Moderado` / `Alerta roja`) y el **resultado** (`Sin sospecha` / `Sospecha moderada` / `Sospecha alta`).
3. Si el cribado marca `requiere_referencia`, **crean la referencia médica** eligiendo al especialista destino y la **prioridad** (Baja → Urgente). El paciente pasa a estado **Referido**.
4. Como médico referente, hacen **seguimiento** y cargan **documentos** (laboratorios, informes). Pueden **cancelar** su propia referencia mientras esté Pendiente/Aceptada.

> Solo estos dos roles (y no el Administrador) pueden **crear cribados**.

### 2. Oncólogo — *Especialista receptor*

Recibe las referencias dirigidas a él y decide la atención especializada. **No crea cribados.**

Proceso (máquina de estados de la referencia):

1. Ve solo los pacientes **referidos a él** (`especialista_destino`).
2. Sobre una referencia `Pendiente`: **Aceptar** o **Rechazar**.
3. `Aceptada` → **Iniciar atención** (`En proceso`).
4. `En proceso` → **Marcar completada**.
5. Lleva el **seguimiento clínico** del paciente confirmado y registra **indicaciones** y **documentos** (p. ej. protocolo de quimioterapia).

### 3. Enfermera / Técnico de Salud — *Apoyo asistencial*

Apoya al equipo clínico con datos, pero **sin autoridad de decisión clínica**.

- Ve los pacientes que creó o tiene asignados.
- Registra en **laboratorio** (muestras/signos) y **sube documentos**.
- Ve cribado, referencias, seguimiento e indicaciones **en solo lectura** (no las crea ni edita).
- No accede a psicosocial, Casa FACCI ni matrices.

### Seguimiento clínico (transversal a los roles clínicos)

Cuando el diagnóstico se confirma, el clínico responsable registra el **seguimiento por fases del protocolo**:

```
Inducción → Consolidación → Mantenimiento → Vigilancia
```

En cada seguimiento anota: estado clínico, síntomas actuales, tratamiento, medicamentos, próxima cita y si requiere hospitalización. De ahí derivan las **indicaciones médicas** (medicación, hidratación, higiene, alimentación, descanso…) con prioridad Alta/Media/Baja, que son las que **ve la familia** en su portal.

### 4. Trabajo Social / Psicología — *Acompañamiento psicosocial*

Evalúa el contexto de la familia y gestiona su alojamiento. Tiene **visión global** de los pacientes (lectura clínica).

1. Realiza la **evaluación psicosocial**: nivel de ingresos, tipo de vivienda, apoyo familiar, **estado emocional** (Estable / Vulnerable / En crisis) y calcula un **nivel de riesgo psicosocial** (Bajo → Crítico).
2. Gestiona la **Casa FACCI**: crea la estancia familiar, asigna habitación, registra el **motivo** (quimioterapia, cirugía, radioterapia…) y la **entrega de habitación** con inventario.
3. Sube documentos de apoyo. No ve cribado, indicaciones ni laboratorio.

### 5. Coordinador FACCI — *Coordinación operativa*

Gestiona la operación institucional, no la clínica. Es el rol **más restringido en lo clínico**.

- **Visión global** de pacientes y referencias (ambos en lectura), Casa FACCI y **matrices operativas**.
- **Gestiona la Casa FACCI** (junto con Trabajo Social).
- **Genera y exporta reportes** (PENCI-RD, estadísticas).
- **Solo ve** el módulo psicosocial (no lo edita) y **no sube documentos**.
- No ve alertas clínicas, cribado, seguimiento, indicaciones ni laboratorio; las referencias son de **solo lectura**.

### 6. Administrador — *Supervisión total*

Acceso completo al sistema y a la **gestión de usuarios**. Visión global de todos los módulos y registros.

Puede gestionar referencias, indicaciones, psicosocial y alojamiento; subir documentos; generar/exportar reportes; administrar usuarios y roles. **Única restricción: no puede crear cribados** (exclusivo de Médico General y Pediatra).

### 7. Padre / Tutor — *La familia*

Accede a un **portal separado** (código de paciente o correo + PIN) y solo ve **su propio hijo/a**.

1. Consulta el **estado del paciente**, las **indicaciones médicas**, el **seguimiento** y los **recursos educativos**.
2. Puede **reportar síntomas** que observa en casa, lo que retroalimenta al equipo clínico.
3. No tiene acceso a ningún módulo interno del personal.

---

## Módulos del Sistema

Cada módulo es una **app de Django** ubicada en `apps/`. La tabla resume la función de cada uno.

| Módulo (`app`) | Función |
|---|---|
| **core** | Base del sistema: utilidades, **middleware de acceso por rol**, cifrado de datos sensibles (Fernet), gestión de **centros de salud**, configuración del sistema y el comando `seed_data`. |
| **auth_app** | Modelo de usuario personalizado (`CustomUser`), **roles** y **matriz de permisos**, y autenticación para el **portal clínico** y el **portal de padres**. |
| **dashboard** | **Dashboards por rol** (indicadores y accesos según el usuario) y **matrices operativas** de coordinación. |
| **pacientes** | Registro y administración de **pacientes pediátricos**, sus tutores y el **expediente clínico**. |
| **cribado** | **Cuestionario de cribado** (detección temprana) con cálculo automático de **nivel de riesgo** y resultado. |
| **referencias** | **Referencias médicas (MSP)** con máquina de estados (prioridad/urgencia, aceptar/rechazar/completar) y **generación de PDF**. |
| **seguimiento** | **Seguimiento clínico por fases** del protocolo e **indicaciones médicas** para la familia. |
| **casos** | **Casos clínicos oncológicos** (apertura, estado, tipo de cáncer, protocolo) y **notas de evolución** del caso. |
| **laboratorio** | Registro de **laboratorio**, muestras y signos clínicos de apoyo. |
| **psicosocial** | **Evaluaciones psicosociales** (Trabajo Social / Psicología): contexto familiar, estado emocional y riesgo psicosocial. |
| **alojamiento** | **Casa FACCI**: gestión de **habitaciones**, admisiones y estancia de las familias. |
| **documentos** | Gestión de **documentos médicos** (informes, laboratorio) asociados a cada paciente. |
| **reportes** | **Reportes estadísticos (PENCI-RD)** y **exportación** a PDF/Excel. |
| **notificaciones** | **Alertas clínicas** y notificaciones internas del sistema. |
| **padres** | **Portal de padres/tutores**: estado del paciente, indicaciones, seguimiento, **recursos educativos** y **reporte de síntomas**. |
| **usuarios** | **Gestión de usuarios** y perfiles (administración de cuentas del personal). |

---

## Estructura del Proyecto

```
faccicare/
├── config/            # Configuración Django (settings, urls, wsgi/asgi)
├── apps/
│   ├── core/          # Utilidades, middleware, cifrado, seed_data, centros de salud
│   ├── auth_app/      # CustomUser, roles y autenticación (portal clínico y de padres)
│   ├── dashboard/     # Dashboards por rol y matrices operativas
│   ├── pacientes/     # Pacientes y expediente clínico
│   ├── cribado/       # Cuestionario de cribado y nivel de riesgo
│   ├── referencias/   # Referencias médicas (MSP) y PDF
│   ├── seguimiento/   # Seguimiento clínico e indicaciones médicas
│   ├── casos/         # Casos clínicos oncológicos y notas de evolución
│   ├── padres/        # Portal de padres/tutores y recursos educativos
│   ├── psicosocial/   # Evaluaciones psicosociales
│   ├── alojamiento/   # Casa FACCI (habitaciones y admisiones)
│   ├── documentos/    # Documentos médicos
│   ├── laboratorio/   # Laboratorio / muestras
│   ├── reportes/      # Reportes estadísticos y exportación
│   ├── notificaciones/# Notificaciones y alertas
│   └── usuarios/      # Gestión de usuarios y perfiles
├── templates/         # Plantillas HTML
├── static/            # Archivos estáticos
├── manage.py
└── requirements.txt
```

---

## Seguridad

- Contraseñas con **Argon2** (con PBKDF2 como respaldo para hashes antiguos).
- **Cifrado de campos sensibles** con Fernet (`FACCI_ENCRYPTION_KEY`).
- **Middleware de control de acceso por rol** y login requerido.
- **Rate limiting** en la API (30/min anónimo, 200/min autenticado).
- Cabeceras de seguridad (HSTS, SSL redirect, cookies seguras) activas cuando `DEBUG=False`.
