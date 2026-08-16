# Documentación del Proyecto — FACCI Care

**Sistema de Detección Temprana de Cáncer Pediátrico**
Fundación de Apoyo Contra el Cáncer Infantil (FACCI) — República Dominicana

| Campo | Detalle |
|---|---|
| **Nombre del sistema** | FACCI Care |
| **Tipo de entregable** | Documentación del proyecto |
| **Versión del documento** | 1.0 |
| **Fecha de emisión** | Agosto 2026 |
| **Dirigido a** | Responsables de FACCI, tribunal evaluador y equipo técnico de mantenimiento |
| **Repositorio** | `alanaquino/faccicare` |
| **Documento complementario** | *Manual de Usuario — Herramientas de Administración del Sitio Web* |

---

## Tabla de contenido

1. [Introducción](#1-introducción)
2. [Planteamiento y justificación](#2-planteamiento-y-justificación)
3. [Objetivos del proyecto](#3-objetivos-del-proyecto)
4. [Alcance y limitaciones](#4-alcance-y-limitaciones)
5. [Metodología de desarrollo](#5-metodología-de-desarrollo)
6. [Arquitectura del sistema](#6-arquitectura-del-sistema)
7. [Tecnologías utilizadas](#7-tecnologías-utilizadas)
8. [Estructura del proyecto](#8-estructura-del-proyecto)
9. [Modelo de datos](#9-modelo-de-datos)
10. [Descripción funcional de los módulos](#10-descripción-funcional-de-los-módulos)
11. [Roles y matriz de permisos](#11-roles-y-matriz-de-permisos)
12. [Flujos de negocio](#12-flujos-de-negocio)
13. [Reglas de negocio implementadas](#13-reglas-de-negocio-implementadas)
14. [Interfaz de programación (API REST)](#14-interfaz-de-programación-api-rest)
15. [Seguridad y protección de datos](#15-seguridad-y-protección-de-datos)
16. [Auditoría y trazabilidad](#16-auditoría-y-trazabilidad)
17. [Instalación y puesta en marcha](#17-instalación-y-puesta-en-marcha)
18. [Despliegue en producción](#18-despliegue-en-producción)
19. [Pruebas y control de calidad](#19-pruebas-y-control-de-calidad)
20. [Mantenimiento y evolución](#20-mantenimiento-y-evolución)
21. [Riesgos identificados](#21-riesgos-identificados)
22. [Entregables del proyecto](#22-entregables-del-proyecto)
23. [Glosario](#23-glosario)
24. [Anexos](#24-anexos)

---

## 1. Introducción

**FACCI Care** es una aplicación web desarrollada con Python, Django y Django REST Framework cuyo propósito es apoyar la **detección temprana, la referencia oportuna y el seguimiento clínico** de pacientes pediátricos con posibles signos de riesgo oncológico en la República Dominicana.

El sistema nace como propuesta académica de monográfico y responde a una necesidad concreta de la Fundación de Apoyo Contra el Cáncer Infantil (FACCI): disponer de una herramienta única que conecte al médico de primer nivel que detecta la sospecha, al especialista que confirma el diagnóstico, al equipo psicosocial que acompaña a la familia y a la coordinación que reporta las estadísticas institucionales.

El presente documento detalla todos los pormenores del proyecto: su justificación, objetivos, alcance, arquitectura, modelo de datos, funcionalidades, reglas de negocio, seguridad, procedimientos de instalación y despliegue, esquema de pruebas y plan de mantenimiento. Está pensado tanto para los responsables de FACCI, que necesitan comprender qué hace el sistema y bajo qué reglas opera, como para cualquier equipo técnico que en el futuro deba mantenerlo o ampliarlo.

FACCI Care integra en una sola plataforma tres grandes ámbitos:

- **Portal clínico** — personal médico y equipo FACCI: dashboard por rol, expediente del paciente, cribado, referencias, seguimiento e indicaciones médicas.
- **Portal de padres/tutores** — la familia consulta el estado del paciente, sus indicaciones, el seguimiento, los recursos educativos y puede reportar síntomas observados en casa.
- **Gestión operativa de FACCI** — evaluaciones psicosociales, administración de la Casa FACCI (alojamiento de familias) y reportes estadísticos con formato PENCI-RD.

---

## 2. Planteamiento y justificación

### 2.1 Problema

El cáncer pediátrico es, en la mayoría de sus formas, altamente curable cuando se detecta a tiempo. En la práctica, sin embargo, la ruta entre la primera consulta y la atención especializada presenta varios puntos de fricción:

1. **Dispersión de la información.** Los datos del paciente quedan repartidos entre expedientes en papel, hojas de cálculo y sistemas independientes de cada centro; nadie tiene la trazabilidad completa del caso.
2. **Referencias sin seguimiento.** Una referencia emitida en un centro de primer nivel no siempre tiene confirmación de que el paciente llegó al especialista, fue atendido y en qué resultó esa atención.
3. **Criterios de sospecha no homogéneos.** La valoración de los signos de alarma depende de la experiencia individual de quien atiende, sin una herramienta de cribado estandarizada.
4. **Familia desinformada.** El padre o tutor recibe indicaciones verbales que se olvidan o se malinterpretan, y no dispone de un canal formal para reportar el empeoramiento de los síntomas.
5. **Reportería manual.** La generación de las estadísticas institucionales y los reportes al Ministerio de Salud Pública (PENCI-RD) se hace de forma manual, con alto costo de tiempo y riesgo de error.

### 2.2 Justificación

FACCI Care aborda esos cinco puntos con una respuesta concreta:

| Problema | Respuesta del sistema |
|---|---|
| Dispersión de la información | Expediente único por paciente con línea de tiempo unificada (cribado, referencias, seguimientos, documentos, notas, síntomas reportados). |
| Referencias sin seguimiento | Máquina de estados de la referencia con **contrarreferencia** obligatoria del especialista, que devuelve diagnóstico, estadio, tratamiento y recomendaciones al médico de origen. |
| Criterios no homogéneos | **Cuestionario de cribado** de 13 signos, con cálculo automático y determinista del nivel de riesgo y del resultado. |
| Familia desinformada | **Portal de padres** con indicaciones médicas, seguimiento, recursos educativos, control de toma de medicamentos y reporte de síntomas. |
| Reportería manual | **Módulo de reportes** con exportación a PDF, Excel y CSV, reporte PENCI-RD con codificación ICD-O3 y matrices operativas exportables. |

### 2.3 Beneficiarios

- **Pacientes pediátricos y sus familias** — ruta de atención más corta y acompañamiento informado.
- **Personal clínico** — herramienta de decisión y trazabilidad del caso.
- **FACCI como institución** — visión operativa consolidada y reportería automatizada.
- **Sistema nacional de salud** — datos estructurados y consistentes para la vigilancia del cáncer infantil.

---

## 3. Objetivos del proyecto

### 3.1 Objetivo general

Desarrollar un sistema clínico web que permita gestionar el cribado, las referencias médicas, el seguimiento clínico, las alertas, la documentación y el acompañamiento a las familias, para apoyar el monitoreo y la atención temprana de pacientes pediátricos con sospecha de cáncer.

### 3.2 Objetivos específicos

1. Implementar un registro centralizado de pacientes pediátricos y sus tutores, con expediente clínico e historial trazable.
2. Estandarizar la detección mediante un cuestionario de cribado con clasificación automática del nivel de riesgo.
3. Automatizar el ciclo completo de la referencia médica, desde su emisión hasta la contrarreferencia del especialista, con generación de documentos imprimibles.
4. Registrar el seguimiento clínico por fases de protocolo y derivar de él las indicaciones médicas dirigidas a la familia.
5. Habilitar un portal diferenciado para padres y tutores, con acceso restringido a su propio paciente.
6. Incorporar la dimensión psicosocial y la gestión del alojamiento de familias en la Casa FACCI.
7. Generar reportes estadísticos y matrices operativas exportables en formatos estándar.
8. Garantizar la confidencialidad de los datos clínicos mediante control de acceso por rol, cifrado de campos sensibles y registro de auditoría.

---

## 4. Alcance y limitaciones

### 4.1 Alcance funcional

El sistema cubre:

- Registro y administración de pacientes pediátricos y sus tutores.
- Cuestionario de cribado con clasificación de nivel de riesgo.
- Gestión de referencias médicas con control de prioridad/urgencia y generación de PDF.
- Contrarreferencias del especialista al médico referente.
- Seguimiento clínico por fases de protocolo e indicaciones médicas.
- Registro y catálogo de laboratorio, con banderas de valores críticos.
- Gestión de documentos médicos por paciente, incluidas las solicitudes de documento a la familia.
- Evaluaciones psicosociales con cálculo de riesgo social.
- Administración de la Casa FACCI: habitaciones, estancias, entrega de habitación con inventario y reportes de estancia.
- Alertas clínicas y notificaciones internas.
- Reportes estadísticos, reporte PENCI-RD y matrices operativas.
- Gestión de centros de salud, incluida su geolocalización.
- Portal de padres/tutores con acceso por código de paciente + PIN.
- API REST protegida por autenticación JWT o de sesión.
- Panel de administración vía Django Admin y panel de auditoría propio.

### 4.2 Fuera de alcance

Los siguientes elementos **no** forman parte de esta versión del sistema:

- Facturación, tarifación o gestión de seguros de salud más allá del registro informativo del seguro del paciente.
- Interoperabilidad automática (HL7/FHIR) con sistemas hospitalarios de terceros.
- Aplicación móvil nativa; la interfaz es web responsiva, incluida una barra de navegación inferior para móvil en el portal de padres.
- Telemedicina, videoconsulta o mensajería instantánea entre médico y familia.
- Prescripción electrónica con validez legal ante entidades reguladoras.
- Envío automatizado de SMS. La configuración muestra el indicador, pero el canal implementado para el envío de reportes es el correo electrónico.

### 4.3 Limitaciones conocidas

- El motor de base de datos por defecto en desarrollo es SQLite; para producción se recomienda MySQL, configurable mediante la variable `DB_ENGINE`.
- El cifrado de campos sensibles depende de que la variable `FACCI_ENCRYPTION_KEY` esté configurada. Si está vacía (escenario típico de desarrollo), los campos se almacenan sin cifrar y el sistema continúa operando.
- La geocodificación de centros de salud depende de un servicio externo y se omite durante la ejecución de pruebas.
- El comando `seed_data`, que puebla datos de demostración, solo se ejecuta con `DEBUG=True`.

---

## 5. Metodología de desarrollo

### 5.1 Enfoque

El proyecto se desarrolló siguiendo un enfoque **iterativo e incremental**, organizado por módulos funcionales. Cada iteración produjo un módulo utilizable de extremo a extremo (modelo de datos → vistas → plantillas → control de acceso), lo que permitió validar tempranamente con los responsables de FACCI el comportamiento de cada flujo antes de avanzar al siguiente.

### 5.2 Ciclo por iteración

1. **Levantamiento** — definición del caso de uso con el responsable funcional.
2. **Modelado** — diseño de las entidades y sus relaciones; creación de la migración.
3. **Implementación** — vistas, formularios, plantillas y decoradores de acceso.
4. **Integración de permisos** — incorporación del módulo a la matriz de acceso por rol.
5. **Verificación** — pruebas manuales con los usuarios de demostración generados por `seed_data` y pruebas automatizadas donde aplica.
6. **Documentación** — actualización del README y de la documentación del proyecto.

### 5.3 Trazabilidad de casos de uso

Los casos de uso se identifican con la nomenclatura **CU-nn** y quedan referenciados directamente en el código fuente, en la docstring de la vista que los implementa. Ejemplos presentes en el repositorio:

| Caso de uso | Descripción | Implementación |
|---|---|---|
| CU-01 | Inicio de sesión, incluido el mensaje de cuenta deshabilitada | `apps/auth_app/views.py` |
| CU-03 | Registrar nuevo usuario del sistema | `apps/usuarios/views.py::nuevo_usuario_view` |
| CU-04 | Editar la ficha completa de un usuario | `apps/usuarios/views.py::editar_usuario_view` |
| CU-06 | Activar o desactivar un usuario | `apps/usuarios/views.py::toggle_usuario_view` |
| CU-34 | Listado y alta de habitaciones de la Casa FACCI | `apps/alojamiento/views.py::habitaciones_view` |
| CU-35 | Habilitar / deshabilitar una habitación | `apps/alojamiento/views.py::habitacion_toggle_view` |
| CU-36 | Eliminar una habitación sin estancias asociadas | `apps/alojamiento/views.py::habitacion_eliminar_view` |

Además, el repositorio incluye una prueba automatizada específica de alineación de casos de uso: `apps/core/tests_use_case_alignment.py`.

### 5.4 Control de versiones

El código se gestiona con **Git** y se aloja en **GitHub** (`alanaquino/faccicare`). El trabajo se realiza en ramas de funcionalidad que se integran a la rama principal mediante *pull requests*.

---

## 6. Arquitectura del sistema

### 6.1 Estilo arquitectónico

FACCI Care sigue el patrón **MTV (Model–Template–View)** propio de Django, que es la variante de MVC utilizada por el framework, con una organización **modular por aplicaciones**: cada dominio funcional del negocio es una *app* de Django independiente dentro del directorio `apps/`.

Sobre esa base se añaden dos capas transversales propias del proyecto:

- **Capa de control de acceso** — middleware y decoradores que aplican la matriz de permisos por rol.
- **Capa de servicios** — módulos como `apps/reportes/services.py` o `apps/core/geocoding.py`, que concentran la lógica de generación de reportes y de geocodificación fuera de las vistas.

### 6.2 Diagrama lógico

```
┌─────────────────────────────────────────────────────────────────────┐
│                            NAVEGADOR                                │
│   Portal clínico (escritorio)      Portal de padres (responsivo)    │
└───────────────┬─────────────────────────────────┬───────────────────┘
                │ HTTPS                           │ HTTPS
┌───────────────▼─────────────────────────────────▼───────────────────┐
│                       CAPA DE PRESENTACIÓN                          │
│   Plantillas Django + componentes (sidebar, navbar, cards)          │
│   CSS propio (facci.css / print.css) + JS ligero                    │
└───────────────┬─────────────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────────────┐
│                          MIDDLEWARE                                 │
│   SecurityMiddleware → Session → Common → CSRF → Authentication     │
│   → LoginRequiredMiddleware → ControlAccesoPorRolMiddleware         │
│   → Messages → XFrameOptions                                        │
└───────────────┬─────────────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────────────┐
│                        CAPA DE APLICACIÓN                           │
│   Vistas por módulo + decoradores de acceso + servicios             │
│   (reportes, matrices, geocodificación, auditoría, cifrado)         │
└───────────────┬─────────────────────────────┬───────────────────────┘
                │                             │
┌───────────────▼──────────────┐  ┌───────────▼───────────────────────┐
│      CAPA DE DOMINIO         │  │        API REST (DRF)             │
│   Modelos Django (ORM)       │  │  JWT / sesión + throttling        │
└───────────────┬──────────────┘  └───────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────────────┐
│                     PERSISTENCIA Y ARCHIVOS                         │
│   SQLite (dev) / MySQL (prod)     ·     MEDIA_ROOT (documentos)     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Cadena de middleware

El orden declarado en `config/settings.py` es determinante para la seguridad del sistema:

| Orden | Middleware | Función |
|---|---|---|
| 1 | `SecurityMiddleware` | Cabeceras de seguridad, HSTS y redirección SSL en producción. |
| 2 | `SessionMiddleware` | Gestión de sesión. |
| 3 | `CommonMiddleware` | Normalización de URLs. |
| 4 | `CsrfViewMiddleware` | Protección contra CSRF. |
| 5 | `AuthenticationMiddleware` | Resuelve `request.user`. |
| 6 | `apps.core.middleware.LoginRequiredMiddleware` | Exige autenticación en todas las rutas internas; deja públicas `/login/`, `/logout/`, `/acceso/`, `/admin/`, `/api/`, `/api-auth/`, `/static/` y `/media/`. También fija el contexto de la petición usado por la auditoría. |
| 7 | `apps.core.middleware.ControlAccesoPorRolMiddleware` | Separa físicamente los dos portales: un `PADRE_TUTOR` solo navega por su portal; el personal no puede entrar a `/padres/`. |
| 8 | `MessageMiddleware` | Mensajes de retroalimentación al usuario. |
| 9 | `XFrameOptionsMiddleware` | `SAMEORIGIN`, necesario para previsualizar documentos del propio sitio en un `<iframe>`. |

### 6.4 Control de acceso en tres niveles

El sistema aplica el mismo criterio de autorización en tres puntos, lo que evita que el menú y el acceso real se desincronicen:

1. **Matriz de acceso en el modelo de usuario** (`apps/auth_app/models.py`) — propiedades `puede_ver_*`, `puede_gestionar_*`, `puede_crear_*` y `puede_generar_*`. Es la **única fuente de verdad**.
2. **Menú lateral** (`templates/components/sidebar.html`) — cada entrada se muestra condicionada a la misma propiedad.
3. **Decoradores de vista** (`apps/core/decorators.py`) — `requiere_acceso('puede_ver_cribado')`, `roles_requeridos(...)`, `solo_personal`, `medico_requerido`, `staff_facci_requerido`, `enfermera_requerida`. Todo intento denegado se registra en el *logger* `facci.acceso` con usuario, rol, ruta e IP.

Adicionalmente, cada vista aplica un **filtrado por alcance de datos**: qué registros ve el usuario, no solo a qué pantalla entra (ver sección 11).

---

## 7. Tecnologías utilizadas

### 7.1 Plataforma

| Componente | Versión / detalle | Uso en el proyecto |
|---|---|---|
| Python | 3.x | Lenguaje base |
| Django | 6.0.5 | Framework web, ORM, plantillas, admin |
| Django REST Framework | 3.17.1 | API REST |
| djangorestframework-simplejwt | — | Autenticación por token JWT |
| django-filter | — | Filtrado de *querysets* en la API |
| drf-spectacular | — | Generación de esquema de la API |
| SQLite | integrado | Base de datos de desarrollo |
| MySQL (`mysqlclient` 2.2.8) | — | Base de datos de producción (opcional vía `DB_ENGINE`) |
| argon2-cffi | — | Hash de contraseñas |
| cryptography (Fernet) | ≥42.0.0 | Cifrado de campos sensibles en reposo |
| ReportLab | — | Generación de documentos PDF |
| openpyxl | — | Exportación a Excel `.xlsx` |
| Pillow | ≥10.0.0 | Procesamiento de imágenes y fotos de perfil |
| python-decouple | 3.8 | Lectura de configuración desde `.env` |
| requests | — | Llamadas HTTP salientes (geocodificación) |
| sqlparse / asgiref / tzdata | — | Dependencias de soporte de Django |

### 7.2 Frontend

- Plantillas Django con componentes reutilizables (`templates/components/`).
- Hojas de estilo propias: `static/css/facci.css` y `static/css/print.css` (esta última para las versiones imprimibles de formularios y reportes).
- JavaScript ligero sin framework: `static/js/live-filter.js` (filtrado en vivo de listados) y `static/js/searchable-select.js` (selectores con búsqueda).
- Iconografía Material Symbols, referenciada por nombre en los modelos (por ejemplo, la propiedad `icono` de `IndicacionMedica`).

### 7.3 Configuración regional

| Parámetro | Valor |
|---|---|
| `LANGUAGE_CODE` | `es` |
| `TIME_ZONE` | `America/Santo_Domingo` |
| `USE_I18N` / `USE_TZ` | Activados |

---

## 8. Estructura del proyecto

```
faccicare/
├── config/                 # Configuración Django (settings, urls, wsgi/asgi)
├── apps/
│   ├── core/               # Utilidades, middleware, decoradores, cifrado,
│   │                       # auditoría, geocodificación, centros de salud,
│   │                       # configuración del sistema y comando seed_data
│   ├── auth_app/           # CustomUser, roles, matriz de permisos y
│   │                       # autenticación de ambos portales
│   ├── dashboard/          # Dashboards por rol, alertas clínicas, matrices,
│   │                       # auditoría y ajustes
│   ├── pacientes/          # Pacientes, notas clínicas y expediente
│   ├── cribado/            # Cuestionario de cribado y nivel de riesgo
│   ├── referencias/        # Referencias médicas, contrarreferencias e
│   │                       # ingresos a Casa FACCI
│   ├── seguimiento/        # Seguimiento clínico e indicaciones médicas
│   ├── casos/              # Casos clínicos oncológicos y notas de evolución
│   ├── laboratorio/        # Catálogo de estudios, resultados y valores
│   ├── psicosocial/        # Evaluaciones psicosociales
│   ├── alojamiento/        # Casa FACCI: habitaciones, estancias y entregas
│   ├── documentos/         # Documentos médicos y solicitudes de documento
│   ├── reportes/           # Reportes estadísticos, PENCI-RD y exportación
│   ├── notificaciones/     # Notificaciones internas
│   ├── padres/             # Portal de padres, recursos educativos y síntomas
│   └── usuarios/           # Gestión de usuarios, roles y perfil
├── templates/              # Plantillas HTML organizadas por módulo
│   ├── layouts/            # base.html y base_padres.html
│   └── components/         # sidebar, navbar, bottom_nav, cards, paginación
├── static/                 # CSS, JS e imágenes
├── manage.py
└── requirements.txt
```

### 8.1 Convenciones internas

- **Identificadores.** Prácticamente todas las entidades de negocio usan `UUIDField` como clave primaria, lo que evita exponer identificadores secuenciales en las URLs.
- **Códigos legibles.** Las entidades que se imprimen o se comunican fuera del sistema exponen un código amigable calculado: `REF-AAAA-XXXX` (referencia), `CONTRA-AAAA-XXXX` (contrarreferencia), `CASA-FACCI-AAAA-XXXX` (ingreso a Casa FACCI) y `FACCI-AAAA0001` (paciente).
- **Marcas de tiempo.** Los modelos incluyen `created_at` / `updated_at` (`auto_now_add` / `auto_now`).
- **Propiedades de presentación.** Los modelos exponen propiedades derivadas (`estado_color`, `iniciales`, `edad`, `fecha`, `icono`) para que las plantillas no incluyan lógica.
- **Índices.** Los campos usados en filtros y listados están indexados explícitamente en `Meta.indexes`.

---

## 9. Modelo de datos

### 9.1 Entidades principales

#### `auth_app.CustomUser`
Modelo de usuario propio (extiende `AbstractUser`), declarado en `AUTH_USER_MODEL`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | Clave primaria |
| `rol` | Choice (8 valores) | Determina toda la autorización |
| `tipo_documento` / `cedula` | Choice / Char único | Cédula dominicana o pasaporte |
| `telefono` | **Cifrado** | `EncryptedCharField` |
| `foto_perfil` | Imagen | |
| `especialidad` | Char | Especialidad médica |
| `centro_medico` | FK → `core.CentroSalud` | Hospital o clínica donde labora |
| `is_active` | Bool | Activa/desactiva el acceso |

#### `pacientes.Paciente`

| Campo | Tipo | Notas |
|---|---|---|
| `codigo_paciente` | Char único | Formato `FACCI-AAAA0001`, generado automáticamente |
| `nombres`, `apellidos`, `fecha_nacimiento`, `sexo` | — | Datos de identificación |
| `tipo_sangre`, `peso`, `altura`, `escuela`, `seguro_medico`, `numero_seguro` | — | Datos complementarios |
| `direccion`, `alergias`, `antecedentes_medicos` | **Cifrados** | `EncryptedTextField` |
| `provincia`, `municipio` | Char | Base de la distribución geográfica de reportes |
| `estado_actual` | Choice (8) | Ver ciclo de vida en 12.1 |
| `diagnostico` | Choice (6) | Leucemia, Tumores del SNC, Retinoblastoma, Tumor de Wilms, Neuroblastoma, Otro |
| `padre_tutor` | FK → `padres.PadreTutor` (PROTECT) | Un paciente siempre tiene tutor |
| `medico_asignado`, `creado_por` | FK → `CustomUser` | Definen el alcance de datos |

#### `cribado.CuestionarioCribado`
13 campos booleanos de síntomas, de los cuales 4 son **alarmas mayores**; más `tipo_cancer_sospechado`, `observaciones`, y los tres campos calculados `nivel_riesgo`, `resultado` y `requiere_referencia`.

#### `referencias.ReferenciaMedica`
Vincula paciente, cribado de origen, médico referente, especialista destino y hospital destino; con `motivo_referencia`, `prioridad` (Baja/Media/Alta/Urgente), `estado` (5 valores), `fecha_cita` y `observaciones`.

#### `referencias.Contrarreferencia`
Relación **uno a uno** con la referencia. Registra `fecha_atencion`, `diagnostico`, `tipo_cancer`, `estadio` (I–IV/NE), `tratamiento_realizado`, `estudios_realizados`, `medicamentos_indicados`, `resultado_atencion` (6 valores), `recomendaciones`, `requiere_seguimiento_facci` y `proxima_cita`.

#### `seguimiento.SeguimientoPaciente`
`fase_protocolo` (Inducción/Consolidación/Mantenimiento/Vigilancia), `estado_clinico`, `sintomas_actuales`, `tratamiento_actual`, `medicamentos`, `observaciones`, `proxima_fecha_seguimiento`, `medico_seguimiento`, `lugar_seguimiento`, `peso_kg`, `talla_cm` (con IMC calculado) y `requiere_hospitalizacion`.

#### `seguimiento.IndicacionMedica`
`tipo_indicacion` (8 valores), `titulo`, `descripcion`, `prioridad` (Alta/Media/Baja), `activa` y `visible_padre` — este último controla si la familia la ve en su portal.

#### Otras entidades

| Entidad | Contenido esencial |
|---|---|
| `padres.PadreTutor` | Perfil del tutor: parentesco, nacionalidad, dirección y contacto de emergencia (**cifrados**), provincia, municipio, ocupación, estado civil, cantidad de hijos e ingresos aproximados. |
| `padres.ReporteSintoma` | Síntomas reportados por la familia: fecha de inicio, gravedad (Leve/Moderada/Severa), lista JSON de síntomas y descripción. |
| `padres.RecursoEducativo` | Contenido educativo con *slug*, categoría (11 valores), contenido, actividades, pasos para el tutor, cuándo contactar al equipo médico, imagen y video. |
| `padres.RegistroTomaMedicamento` | Marca de medicamento tomado por día, con restricción de unicidad por paciente + medicamento + índice + fecha. |
| `laboratorio.CatalogoEstudio` / `CatalogoParametro` | Catálogo de estudios y sus parámetros, con unidades, rangos de referencia, tipo de valor y marca de alerta crítica. |
| `laboratorio.ResultadoLaboratorio` / `ValorResultado` | Resultado por paciente (9 tipos de examen, 4 estados) y sus valores individuales con bandera Normal/Bajo/Alto/Crítico. |
| `documentos.DocumentoMedico` | Archivo asociado a paciente, con tipo (12 valores), estado (Pendiente/Revisado/Requiere corrección) y `visible_padre`. |
| `documentos.SolicitudDocumento` | Documento que el médico solicita a la familia; se enlaza al documento entregado. |
| `psicosocial.EvaluacionPsicosocial` | Contexto familiar, económico, habitacional, emocional y escolar; `puntaje_total` y `nivel_riesgo` calculados. |
| `alojamiento.HabitacionCasa` | Habitación de la Casa FACCI: nombre, capacidad, descripción y disponibilidad. |
| `alojamiento.EstanciaFamiliar` | Estancia de la familia: habitación, acompañante, motivo (6 valores), fechas y estado (Activa/Completada/Cancelada). |
| `alojamiento.EntregaHabitacion` / `ItemEntregaHabitacion` | Acta de entrega y recepción con inventario por ítem. |
| `referencias.ReferenciaIngresoCasaFACCI` | Solicitud de ingreso a la Casa FACCI con datos del responsable y estado (Pendiente/Aprobada/Ingresado/Cancelada). |
| `dashboard.AlertaClinica` | Alerta generada por el sistema: 7 tipos, prioridad, estado, fecha límite y comentario de cierre; con clave de deduplicación. |
| `notificaciones.Notificacion` | Notificación al usuario: 13 tipos, 4 prioridades, URL de acción, objeto relacionado genérico, lectura y archivado. |
| `reportes.ReporteGenerado` | Registro histórico de cada reporte producido: tipo, formato, código de documento, rango de fechas, total de registros y archivo. |
| `core.CentroSalud` | Centro de salud: tipo por nivel, capacidades (camas), especialidades, personal entrenado, estado de derivación y coordenadas. |
| `core.LogActividad` | Bitácora de auditoría: usuario, acción, tipo de acción, módulo, objeto, descripción, IP y fecha. |
| `core.SistemaConfiguracion` | Configuración institucional: nombre de la aplicación, nombre de la institución, logo de aplicación y logo oficial de reportes. |

### 9.2 Relaciones clave

```
CustomUser 1─────* Paciente          (medico_asignado / creado_por)
PadreTutor 1─────* Paciente          (PROTECT: no se borra un tutor con pacientes)
CustomUser 1─────1 PadreTutor        (perfil_padre)
Paciente   1─────* CuestionarioCribado
Paciente   1─────* ReferenciaMedica
CuestionarioCribado 1───* ReferenciaMedica     (cribado de origen)
ReferenciaMedica 1─────1 Contrarreferencia
Paciente   1─────* SeguimientoPaciente
Paciente   1─────* IndicacionMedica
Paciente   1─────* DocumentoMedico
Paciente   1─────* ResultadoLaboratorio 1───* ValorResultado
Paciente   1─────* EvaluacionPsicosocial
Paciente   1─────* EstanciaFamiliar 1───* EntregaHabitacion 1───* ItemEntregaHabitacion
HabitacionCasa 1─* EstanciaFamiliar
Paciente   1─────* ReporteSintoma
Paciente   1─────* AlertaClinica
CentroSalud 1────* CustomUser / ReferenciaMedica / SeguimientoPaciente
```

### 9.3 Integridad referencial

- **PROTECT** en las relaciones cuyo borrado destruiría trazabilidad clínica: `Paciente.padre_tutor`, `CuestionarioCribado.medico`, `ReferenciaMedica.medico_referente`, `SeguimientoPaciente.medico`, `IndicacionMedica.medico`, `NotaClinica.autor`.
- **CASCADE** en los registros que carecen de sentido sin su paciente: cribados, referencias, seguimientos, indicaciones, documentos, notas, alertas.
- **SET_NULL** en referencias opcionales de contexto: `especialista_destino`, `centro_medico`, `lugar_seguimiento`, `habitacion`.

---

## 10. Descripción funcional de los módulos

### 10.1 `core` — Base del sistema
Middleware de acceso y de auditoría, decoradores de rol, cifrado Fernet, geocodificación de centros, constantes (provincias de la República Dominicana), gestión de centros de salud, configuración del sistema y el comando `seed_data` que genera datos de demostración.

### 10.2 `auth_app` — Identidad y autenticación
Modelo `CustomUser` con los 8 roles y la matriz de permisos. Implementa **dos flujos de autenticación distintos**:

- **Portal clínico** (`/login/`): usuario o correo + contraseña. Detecta explícitamente la cuenta deshabilitada para mostrar el mensaje correspondiente en vez de un error genérico.
- **Portal de padres** (`/acceso/padres/`): código de paciente, correo o nombre de usuario + **PIN**. El sistema resuelve el tutor a partir del código de paciente y autentica contra la contraseña de esa cuenta.

El cierre de sesión devuelve al usuario al portal por el que entró.

### 10.3 `dashboard` — Indicadores, alertas y coordinación
Dashboard por rol con indicadores y accesos directos; distribución de pacientes por provincia; gestión de **alertas clínicas** (revisar, resolver, descartar); **matrices operativas** por período con vista previa, exportación CSV y descarga en PDF; panel de **auditoría**; y **ajustes del sistema** (nombre e imagen institucional).

### 10.4 `pacientes` — Registro y expediente
Registro del paciente junto con su tutor en un solo formulario: si el tutor no existe, el sistema crea su cuenta y genera un **PIN numérico de 6 dígitos**; si ya existe (localizado por cédula o correo), lo reutiliza y actualiza sus datos. El expediente reúne en una **línea de tiempo** los cribados, referencias, seguimientos, documentos, notas clínicas, síntomas reportados, indicaciones y solicitudes. Incluye ficha del paciente imprimible en PDF y reseteo del PIN del tutor.

### 10.5 `cribado` — Detección temprana
Cuestionario estructurado en secciones (síntomas generales, signos hematológicos, signos neurológicos y masas, signos oculares). Calcula el nivel de riesgo de forma automática al guardar y, cuando corresponde, habilita la creación directa de la referencia desde la pantalla de resultado. Permite exportar el listado a CSV.

### 10.6 `referencias` — Derivación y retorno
Ciclo completo de la referencia con máquina de estados, historial por paciente, impresión del formulario MSP, guardado del documento MSP, **contrarreferencia** del especialista y **solicitud de ingreso a la Casa FACCI** con su formulario imprimible.

### 10.7 `seguimiento` — Evolución e indicaciones
Registro de seguimientos por fase de protocolo, línea de tiempo del caso, administración de indicaciones médicas por paciente y generación del **descargo de tratamiento** en pantalla y en PDF.

### 10.8 `laboratorio` — Apoyo diagnóstico
Catálogo de estudios y parámetros con rangos de referencia; registro de resultados con valores individuales; cálculo de banderas (normal, bajo, alto, crítico) y marcado de revisión.

### 10.9 `psicosocial` — Acompañamiento social
Evaluación del contexto familiar con puntuación automática que deriva el nivel de riesgo psicosocial, las necesidades identificadas, las acciones recomendadas y la fecha de próxima evaluación.

### 10.10 `alojamiento` — Casa FACCI
Administración de habitaciones (alta, habilitación/deshabilitación, eliminación cuando no tienen estancias), estancias familiares con motivo y fechas, *check-out*, acta de **entrega de habitación** con inventario e impresión, y reporte de estancias en pantalla y PDF.

### 10.11 `documentos` — Gestión documental
Carga de documentos por paciente, previsualización en el navegador, descarga, cambio de estado, cambio de visibilidad para la familia, eliminación y bandeja de **solicitudes** de documentos dirigidas a los tutores.

### 10.12 `reportes` — Estadística institucional
Dashboard estadístico, generador de reportes con tipo, formato, período y filtros; vista previa imprimible; **envío por correo electrónico** con el archivo adjunto; y el reporte **PENCI-RD** con codificación ICD-O3 y agrupación por rangos etarios (0–4, 5–9, 10–14, ≥15 años). Cada reporte producido queda registrado en `ReporteGenerado`.

### 10.13 `notificaciones` — Comunicación interna
Bandeja de notificaciones con marcado de leído/no leído, marcado masivo, eliminación, apertura directa al objeto relacionado y API de consulta para el indicador del encabezado. Incluye deduplicación por clave para evitar avisos repetidos.

### 10.14 `padres` — Portal de la familia
Estado del paciente, evolución, reporte de síntomas, indicaciones médicas, marcado de medicamentos tomados, alertas, documentos (consulta y carga en respuesta a una solicitud), recursos educativos y perfil del tutor.

### 10.15 `usuarios` — Administración de cuentas
Listado con búsqueda y filtros por rol y estado, alta de usuario, edición completa de la ficha (incluido el perfil extendido si el rol es Padre/Tutor), activación/desactivación, catálogo descriptivo de roles, configuración y perfil propio con cambio de contraseña y actividad reciente.

### 10.16 `casos` — Casos clínicos oncológicos
Apertura y cierre del caso, tipo de cáncer, protocolo y notas de evolución. La aplicación se mantiene registrada en `INSTALLED_APPS` por su historial de migraciones.

---

## 11. Roles y matriz de permisos

### 11.1 Roles del sistema

| Código | Nombre | Ámbito |
|---|---|---|
| `ADMIN` | Administrador | Supervisión total del sistema |
| `MEDICO` | Médico General (primer nivel) | Detección y puerta de entrada |
| `PEDIATRA` | Pediatra (segundo nivel) | Detección y derivación al especialista |
| `ONCOLOGO` | Oncólogo Pediátrico (tercer nivel) | Confirmación y tratamiento |
| `PERSONAL_FACCI` | Coordinador FACCI | Coordinación operativa e institucional |
| `TRABAJADORA_SOCIAL` | Trabajo Social / Psicología | Acompañamiento psicosocial |
| `ENFERMERA` | Enfermera / Técnico de Salud | Apoyo asistencial |
| `PADRE_TUTOR` | Padre / Tutor | Portal de la familia |

### 11.2 Matriz de acceso

| Rol | Qué puede ver | Qué puede hacer (escritura) | Qué NO puede ver / hacer | Alcance de datos |
|---|---|---|---|---|
| **Administrador** | Todo: pacientes, alertas, cribado, referencias, seguimiento, indicaciones, laboratorio, psicosocial, Casa FACCI, reportes, matrices y usuarios | Gestionar referencias, indicaciones, psicosocial y alojamiento; subir documentos; generar/exportar reportes; administrar usuarios | **No puede crear cribados** (exclusivo de Médico General y Pediatra) | **Todos** los registros |
| **Pediatra** | Pacientes, alertas, cribado, referencias, seguimiento, indicaciones, laboratorio, Casa FACCI (lectura), reportes | **Crear cribados**, gestionar referencias e indicaciones, subir documentos | No ve psicosocial ni matrices; no gestiona Casa FACCI; no genera reportes | Los que **creó o tiene asignados** |
| **Médico General** | Igual que Pediatra | **Crear cribados**, gestionar referencias e indicaciones, subir documentos | Igual que Pediatra | Los que **creó o tiene asignados** |
| **Oncólogo** | Pacientes, alertas, cribado (lectura), referencias, seguimiento, indicaciones, laboratorio, Casa FACCI (lectura), reportes | Gestionar referencias e indicaciones, subir documentos | No crea cribados; no ve psicosocial ni matrices; no gestiona Casa FACCI; no genera reportes | Los que le han sido **referidos** |
| **Enfermera / Técnico** | Pacientes, alertas, cribado, referencias (lectura), seguimiento (lectura), indicaciones (lectura), laboratorio, reportes | Subir documentos, registrar en laboratorio | No crea cribados; no gestiona referencias ni indicaciones; no ve psicosocial, Casa FACCI ni matrices; no genera reportes | Los que **creó o tiene asignados** |
| **Trabajo Social / Psicología** | Pacientes (lectura), alertas, referencias y seguimiento (lectura), psicosocial, Casa FACCI, reportes | **Gestionar evaluaciones psicosociales**, gestionar Casa FACCI, subir documentos | No ve cribado, indicaciones ni laboratorio; no ve matrices; no crea cribados; no genera reportes | **Todos** los registros |
| **Coordinador FACCI** | Pacientes y referencias (lectura), psicosocial (lectura), Casa FACCI, reportes, **matrices operativas** | **Gestionar Casa FACCI**, **generar/exportar reportes** | No ve alertas, cribado, seguimiento, indicaciones ni laboratorio; no crea cribados; no edita psicosocial; no sube documentos | **Todos** los registros |
| **Padre / Tutor** | Su portal: estado del paciente, indicaciones y documentos compartidos, seguimiento, recursos educativos | **Reportar síntomas** y subir documentos de su hijo/a | No accede a ningún módulo del personal | **Solo su(s) propio(s) paciente(s)** |

### 11.3 Restricciones destacadas

- **Crear cribados:** exclusivo de Médico General y Pediatra. Ni siquiera el Administrador puede crearlos.
- **Generar/exportar reportes y matrices:** Administrador y Coordinador FACCI.
- **Módulo psicosocial:** equipo FACCI (Coordinador y Trabajo Social) más el Administrador; solo Trabajo Social y Administrador pueden **editar**.
- **Autoprotección del administrador:** un administrador no puede desactivar su propia cuenta ni quitarse su propio rol.
- **Separación de portales:** una cuenta con rol de personal no puede vincularse como padre o tutor de un paciente, y el middleware impide la navegación cruzada entre portales.

---

## 12. Flujos de negocio

### 12.1 Ciclo de vida del paciente

```
Sospechoso → Referido → En estudio → Confirmado / Descartado
          → En tratamiento → En remisión → Finalizado
```

### 12.2 Cadena de valor del sistema

```
1. Cribado (detección)
        ↓
2. Referencia (derivación)  →  Contrarreferencia (retorno del especialista)
        ↓
3. Seguimiento clínico (tratamiento por fases)
        ↓
4. Indicaciones médicas (pautas para la familia)
        ↓
5. Psicosocial + Casa FACCI (acompañamiento)
        ↓
6. Reportes (estadística / PENCI-RD)
```

En paralelo, el **portal de padres** mantiene informada a la familia y devuelve información clínica al equipo mediante el reporte de síntomas.

### 12.3 Flujo 1 — Detección (Médico General / Pediatra)

1. Registra al paciente y a su tutor. El paciente queda asociado al profesional (`medico_asignado` / `creado_por`) y se genera el código `FACCI-AAAA0001`. Si el tutor es nuevo, el sistema muestra una sola vez el PIN generado.
2. Aplica el cuestionario de cribado. El sistema calcula el nivel de riesgo y el resultado.
3. Si el cribado indica `requiere_referencia`, crea la referencia eligiendo especialista destino y prioridad. El paciente pasa a estado **Referido**.
4. Como médico referente, hace seguimiento y carga documentos. Puede **cancelar** su propia referencia mientras esté Pendiente o Aceptada.

### 12.4 Flujo 2 — Especialista receptor (Oncólogo)

Máquina de estados de la referencia:

```
PENDIENTE ──aceptar──▶ ACEPTADA ──iniciar atención──▶ EN_PROCESO ──completar──▶ COMPLETADA
    │                      │
    └──rechazar/cancelar───┴──────────────────────────▶ CANCELADA
```

Al completar la atención, el especialista emite la **contrarreferencia** con el diagnóstico establecido, el tipo de cáncer confirmado, el estadio, el tratamiento realizado, los estudios, los medicamentos indicados, el resultado de la atención y las recomendaciones para el médico de origen.

### 12.5 Flujo 3 — Seguimiento clínico

Confirmado el diagnóstico, el clínico responsable registra el seguimiento por fases del protocolo:

```
Inducción → Consolidación → Mantenimiento → Vigilancia
```

En cada seguimiento se anota el estado clínico, los síntomas actuales, el tratamiento, los medicamentos, peso y talla (con IMC calculado), la próxima cita y si requiere hospitalización. De ahí derivan las **indicaciones médicas** que la familia ve en su portal.

### 12.6 Flujo 4 — Acompañamiento psicosocial y alojamiento

1. Trabajo Social realiza la **evaluación psicosocial**: ingresos, tipo y condición de la vivienda, hacinamiento, apoyo familiar, estado emocional del cuidador, situación escolar del niño e impacto emocional. El sistema calcula el puntaje y el nivel de riesgo (Bajo → Crítico).
2. Se gestiona la **Casa FACCI**: creación de la estancia, asignación de habitación, registro del motivo (quimioterapia, cirugía, radioterapia, hospitalización prolongada, consulta) y **acta de entrega de habitación** con inventario.
3. Al egreso se registra el *check-out* y la estancia pasa a **Completada**.

### 12.7 Flujo 5 — Reportería institucional

El Administrador o el Coordinador FACCI selecciona tipo de reporte, período (último mes, 3 meses, 6 meses, último año o rango personalizado), formato (PDF, Excel o CSV) y filtros opcionales; puede previsualizarlo, descargarlo o enviarlo por correo con el archivo adjunto. Cada generación queda registrada con su código de documento y aparece en el panel de auditoría.

### 12.8 Flujo 6 — La familia

1. El tutor entra al portal con el código de paciente (o su correo) y su PIN.
2. Consulta el estado del paciente, sus indicaciones médicas, el seguimiento y los recursos educativos.
3. Marca los medicamentos tomados y **reporta síntomas** observados en casa, lo que retroalimenta al equipo clínico y puede originar una alerta.
4. Responde a las solicitudes de documentos subiendo los archivos requeridos.

---

## 13. Reglas de negocio implementadas

### 13.1 Cálculo del nivel de riesgo del cribado

El cuestionario evalúa **13 signos**, de los cuales **4 son alarmas mayores**: dolor de cabeza persistente, vómitos matutinos sin causa gastrointestinal, masa abdominal palpable y leucocoria (reflejo ocular blanquecino). El puntaje es el número de signos marcados y la clasificación se recalcula automáticamente **en cada guardado**:

| Condición | Nivel de riesgo | Resultado | ¿Requiere referencia? |
|---|---|---|---|
| Alguna alarma mayor **o** puntaje ≥ 6 | **Alto** (alerta roja) | Sospecha alta | **Sí** |
| Puntaje ≥ 3 (sin alarma mayor) | Moderado | Sospecha moderada | No |
| Puntaje < 3 | Bajo | Sin sospecha | No |

Esta lógica reside en el método `calcular_resultado()` del modelo y se invoca desde `save()`, de modo que **ninguna vía de creación puede saltarse el cálculo**, ni siquiera la API o el Django Admin.

### 13.2 Generación del código de paciente

Formato `FACCI-{año}{consecutivo de 4 dígitos}`. El consecutivo se obtiene del último código del año en curso y se verifica su unicidad antes de asignarlo.

### 13.3 Alta del tutor y PIN de acceso

- Si no existe una cuenta con esa cédula o correo, se crea con rol `PADRE_TUTOR` y un **PIN aleatorio de 6 dígitos** generado con `secrets`, que se muestra una sola vez tras el registro.
- Si ya existe, se reutiliza y se actualizan sus datos.
- Si la cédula o el correo pertenecen a una **cuenta del personal**, el formulario rechaza la operación.
- La cédula dominicana se valida (11 dígitos) y se normaliza al formato `000-0000000-0`.
- El reseteo del PIN está autorizado para el Administrador, el médico asignado y el creador del paciente.

### 13.4 Autorización de edición del paciente

| Rol | Puede editar si… |
|---|---|
| Administrador | Siempre |
| Médico General / Pediatra | Es el médico asignado o quien lo creó |
| Oncólogo | Existe una referencia dirigida a él |
| Resto de roles | No puede editar |

### 13.5 Evaluación psicosocial

El puntaje se calcula a partir de los factores registrados (ingresos, seguro, dificultad para medicamentos y transporte, condición de vivienda, hacinamiento, ausencia de servicios básicos, apoyo familiar, cuidador único, estado emocional, pérdida de trabajo, necesidad de apoyo psicológico, abandono escolar e impacto emocional) y determina el nivel de riesgo entre Bajo, Moderado, Alto y Crítico.

### 13.6 Laboratorio

Cada valor se compara con el rango de referencia del parámetro del catálogo y recibe una bandera: Normal, Bajo, Alto, Crítico bajo, Crítico alto o Sin rango. La presencia de valores críticos marca el resultado completo y alimenta el estado **Valores críticos**.

### 13.7 Alertas clínicas

El sistema genera alertas de siete tipos: síntomas de alarma, sospechoso sin referencia, referencia sin seguimiento, seguimiento pendiente o vencido, alta prioridad sin revisión, documento clínico pendiente y caso crítico. Cada alerta tiene prioridad, fecha límite y un flujo de cierre **Pendiente → Revisada → Resuelta / Descartada** con comentario. La **clave de deduplicación** evita que un mismo hecho genere alertas repetidas.

### 13.8 Visibilidad hacia la familia

Dos interruptores explícitos controlan qué llega al portal de padres: `IndicacionMedica.visible_padre` y `DocumentoMedico.visible_padre`. Nada del expediente clínico se publica a la familia sin esa marca.

### 13.9 Restricciones de eliminación

Una habitación de la Casa FACCI solo puede eliminarse si **no tiene estancias asociadas**; en caso contrario se deshabilita.

---

## 14. Interfaz de programación (API REST)

### 14.1 Autenticación

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/token/` | POST | Obtiene el par de tokens JWT (acceso y refresco) |
| `/api/token/refresh/` | POST | Renueva el token de acceso |
| `/api-auth/` | — | Autenticación de sesión del navegador (DRF) |

Clases de autenticación habilitadas: **JWT**, **sesión** y **básica**. El permiso por defecto es `IsAuthenticated`: **no hay endpoints públicos**.

### 14.2 Recursos disponibles

| Prefijo | Recursos |
|---|---|
| `/api/core/` | Punto de entrada del núcleo, mapa de centros de salud y geocodificación de un centro |
| `/api/pacientes/` | `pacientes` |
| `/api/cribado/` | `cribados` |
| `/api/seguimiento/` | `referencias`, `seguimientos`, `alertas` |
| `/api/documentos/` | `documentos`, `solicitudes` |

### 14.3 Límite de peticiones (*throttling*)

| Tipo de cliente | Límite |
|---|---|
| Anónimo | 30 peticiones por minuto |
| Autenticado | 200 peticiones por minuto |

---

## 15. Seguridad y protección de datos

### 15.1 Autenticación y contraseñas

- **Argon2** como algoritmo principal de hash, con salt. PBKDF2, PBKDF2-SHA1 y Scrypt se mantienen como respaldo para verificar hashes antiguos; Django los recifra a Argon2 en el siguiente inicio de sesión.
- Validadores activos: similitud con atributos del usuario, longitud mínima, contraseñas comunes y contraseñas solo numéricas.
- Longitud mínima de 8 caracteres exigida además en el alta y el cambio de contraseña.

### 15.2 Cifrado de datos sensibles en reposo

Los campos de mayor sensibilidad se almacenan cifrados con **Fernet** (AES-128-CBC + HMAC-SHA256) mediante los tipos propios `EncryptedCharField` y `EncryptedTextField`. Los valores cifrados llevan el prefijo `enc:` para distinguirlos de datos previos sin cifrar.

Campos cifrados:

| Modelo | Campos |
|---|---|
| `CustomUser` | `telefono` |
| `Paciente` | `direccion`, `alergias`, `antecedentes_medicos` |
| `PadreTutor` | `direccion`, `contacto_emergencia`, `telefono_emergencia` |

La clave se define en `FACCI_ENCRYPTION_KEY` y se genera con:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> **Advertencia operativa.** La pérdida de esta clave hace irrecuperables los datos cifrados. Debe respaldarse fuera del repositorio y fuera del servidor de aplicación.

### 15.3 Cabeceras y transporte

Con `DEBUG=False` se activan automáticamente:

| Medida | Valor |
|---|---|
| `SECURE_HSTS_SECONDS` | 31 536 000 (1 año), incluidos subdominios |
| `SECURE_SSL_REDIRECT` | Activo |
| `SECURE_PROXY_SSL_HEADER` | `HTTP_X_FORWARDED_PROTO` (evita el bucle de redirección tras un proxy TLS) |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | Activos |
| `SECURE_BROWSER_XSS_FILTER` / `SECURE_CONTENT_TYPE_NOSNIFF` | Activos |
| `X_FRAME_OPTIONS` | `SAMEORIGIN` — permite previsualizar documentos propios y bloquea el *framing* externo |
| `CSRF_TRUSTED_ORIGINS` | Derivados de `ALLOWED_HOSTS` con esquema `https://` |

### 15.4 Control de acceso

Ver sección 6.4. Todo acceso denegado se registra en el *logger* `facci.acceso` con nivel `WARNING`, incluyendo usuario, rol, ruta, IP y roles permitidos.

### 15.5 Buenas prácticas de configuración

- Ningún secreto en el repositorio: `DJANGO_SECRET_KEY`, credenciales de base de datos, credenciales SMTP y clave de cifrado se leen del entorno con `python-decouple`.
- `.gitignore` excluye `.env`, `db.sqlite3`, `media/`, `staticfiles/`, respaldos y `secrets.json`.
- `DEBUG` debe ser `False` en producción y `ALLOWED_HOSTS` debe listar únicamente los dominios reales.

---

## 16. Auditoría y trazabilidad

### 16.1 Bitácora de actividad

El modelo `core.LogActividad` registra usuario, acción, tipo de acción, modelo, módulo, identificador y representación del objeto, descripción, dirección IP y fecha. El tipo de acción y el módulo se infieren automáticamente cuando no se especifican, a partir del texto de la acción y del modelo afectado.

Tipos de acción: Creación, Edición, Eliminación, Consulta, Inicio de sesión, Cierre de sesión y Generación de reporte.

### 16.2 Panel de auditoría

Disponible únicamente para el Administrador en `/auditoria/`, muestra:

- Indicadores: total de usuarios, usuarios activos, acciones del día, reportes generados y accesos de los últimos 7 días.
- Listado de usuarios con su número de acciones y último acceso.
- Actividad reciente filtrable por usuario, rol, estado, último acceso, módulo, tipo de acción y rango de fechas.
- Historial de reportes generados con su autor.

### 16.3 Trazabilidad clínica

Más allá de la bitácora, la trazabilidad clínica está garantizada por el diseño mismo del modelo: cada cribado, referencia, seguimiento, indicación, documento y nota conserva su autor mediante relaciones **PROTECT**, de modo que **no es posible eliminar al profesional responsable** de un acto clínico registrado.

---

## 17. Instalación y puesta en marcha

### 17.1 Requisitos previos

- Python 3.x con `pip` y `venv`.
- Git.
- Para producción con MySQL: servidor MySQL y las librerías de desarrollo necesarias para `mysqlclient`.

### 17.2 Instalación en entorno de desarrollo

```bash
# 1. Clonar el repositorio
git clone https://github.com/alanaquino/faccicare.git
cd faccicare

# 2. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. Poblar datos de prueba (solo funciona con DEBUG=True)
python manage.py seed_data

# 6. Levantar el servidor de desarrollo
python manage.py runserver
```

### 17.3 Direcciones de acceso

| Destino | URL |
|---|---|
| Portal clínico | `http://127.0.0.1:8000/login/` |
| Portal de padres | `http://127.0.0.1:8000/acceso/padres/` |
| Django Admin | `http://127.0.0.1:8000/admin/` |

### 17.4 Variables de entorno

La configuración usa `python-decouple`. Se define un archivo `.env` en la raíz del proyecto:

| Variable | Descripción | Valor por defecto (desarrollo) |
|---|---|---|
| `DJANGO_DEBUG` | Modo depuración | `True` |
| `DJANGO_SECRET_KEY` | Clave secreta de Django | clave insegura de desarrollo |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos (lista separada por comas) | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes de confianza CSRF | derivados de `ALLOWED_HOSTS` |
| `DB_ENGINE` | Motor de base de datos | `django.db.backends.sqlite3` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Conexión a la base de datos | `db.sqlite3` / vacío / vacío / `localhost` / `3306` |
| `FACCI_ENCRYPTION_KEY` | Clave Fernet para cifrar datos sensibles | vacío |
| `EMAIL_BACKEND` | Backend de correo | consola |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | Servidor SMTP | `smtp.gmail.com` / `587` / `True` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Credenciales SMTP | vacío |
| `DEFAULT_FROM_EMAIL` | Remitente por defecto | `noreply@faccicare.org` |
| `SEED_ADMIN_PASSWORD` | Contraseña del admin en `seed_data` | `adminpassword123` |
| `SEED_DEFAULT_PASSWORD` | Contraseña del resto de usuarios de prueba | `password123` |

### 17.5 Usuarios de demostración

El comando `python manage.py seed_data` crea el siguiente conjunto de cuentas. **Son exclusivamente para desarrollo y pruebas**; el comando no se ejecuta con `DEBUG=False`.

| Rol | Usuario(s) | Contraseña | Portal |
|---|---|---|---|
| Administrador | `admin` (Ana Flores) | `adminpassword123` | Clínico |
| Pediatra | `jmartinez`, `elopez` | `password123` | Clínico |
| Oncólogo | `evargas` | `password123` | Clínico |
| Médico General | `rgomez` | `password123` | Clínico |
| Coordinador FACCI | `msantos` | `password123` | Clínico |
| Trabajo Social / Psicología | `lperez` | `password123` | Clínico |
| Enfermera / Técnico | `cgonzalez` | `password123` | Clínico |
| Padre / Tutor | `carlos_r`, `maria_v`, `ana_p`, `pedro_d`, `luis_m` | PIN `password123` | Padres |

---

## 18. Despliegue en producción

### 18.1 Lista de verificación previa

1. `DJANGO_DEBUG=False`.
2. `DJANGO_SECRET_KEY` con un valor aleatorio y exclusivo del entorno productivo.
3. `DJANGO_ALLOWED_HOSTS` con los dominios reales.
4. `FACCI_ENCRYPTION_KEY` generada y respaldada de forma segura fuera del servidor.
5. `DB_ENGINE=django.db.backends.mysql` con credenciales propias y usuario de base de datos con permisos mínimos.
6. Credenciales SMTP reales si se usará el envío de reportes por correo.
7. Certificado TLS activo y proxy configurado para enviar `X-Forwarded-Proto`.

### 18.2 Procedimiento

```bash
# Dependencias
pip install -r requirements.txt

# Migraciones
python manage.py migrate --noinput

# Archivos estáticos
python manage.py collectstatic --noinput

# Superusuario inicial
python manage.py createsuperuser
```

Servir la aplicación mediante WSGI (`config.wsgi:application`) detrás de un servidor web que termine TLS y sirva `/static/` y `/media/`.

### 18.3 Consideraciones de archivos

- `MEDIA_ROOT` almacena documentos médicos, fotografías, logos y reportes generados. Debe estar en un volumen persistente **respaldado** y **no accesible por listado de directorio**.
- `STATIC_ROOT` se genera con `collectstatic` y lo sirve el servidor web.
- En desarrollo, Django sirve `/media/` únicamente cuando `DEBUG=True`.

### 18.4 Respaldos recomendados

| Elemento | Frecuencia sugerida |
|---|---|
| Base de datos | Diaria, con retención mínima de 30 días |
| `MEDIA_ROOT` | Diaria o incremental |
| `FACCI_ENCRYPTION_KEY` y `.env` | Custodia segura fuera del servidor, con copia en sobre cerrado o gestor de secretos |

---

## 19. Pruebas y control de calidad

### 19.1 Pruebas automatizadas

```bash
python manage.py test
```

Suites presentes en el repositorio:

| Archivo | Cobertura |
|---|---|
| `apps/core/tests_use_case_alignment.py` | Verifica que la implementación se mantenga alineada con los casos de uso definidos |
| `apps/core/tests_centros_matching.py` | Emparejamiento y normalización de centros de salud |
| `apps/pacientes/tests_verificar_tutor.py` | Verificación de tutor por cédula en el registro de pacientes |
| `apps/usuarios/tests.py` | Gestión de usuarios |

Durante la ejecución de pruebas, la geocodificación externa se desactiva automáticamente para no depender de servicios de terceros.

### 19.2 Pruebas manuales por rol

El procedimiento de validación funcional consiste en recorrer, con los usuarios de demostración, los siguientes escenarios:

| Escenario | Rol | Resultado esperado |
|---|---|---|
| Cribado con alarma mayor | Pediatra | Nivel Alto, sospecha alta y referencia habilitada |
| Cribado con 3 síntomas menores | Médico General | Nivel Moderado, sin referencia |
| Aceptar y completar referencia | Oncólogo | Estado avanza y se habilita la contrarreferencia |
| Indicación con `visible_padre` desactivado | Pediatra / Padre | La indicación no aparece en el portal de padres |
| Acceso a `/psicosocial/` | Enfermera | Redirección al inicio con mensaje de permiso denegado |
| Acceso a `/padres/` | Cualquier rol de personal | Redirección al inicio |
| Acceso a `/pacientes/` | Padre / Tutor | Redirección a su portal |
| Desactivación de la cuenta propia | Administrador | Operación rechazada |
| Generación de reporte | Coordinador FACCI | Descarga correcta y registro en auditoría |

### 19.3 Criterios de aceptación

1. Ningún rol accede a un módulo fuera de su matriz de permisos.
2. Ningún usuario ve registros fuera de su alcance de datos.
3. El nivel de riesgo del cribado se recalcula siempre al guardar.
4. Toda acción de escritura relevante queda registrada en la bitácora de auditoría.
5. Los documentos PDF se generan con el logotipo institucional configurado.

---

## 20. Mantenimiento y evolución

### 20.1 Cómo añadir un nuevo módulo

1. Crear la *app* dentro de `apps/` y registrarla en `INSTALLED_APPS`.
2. Definir modelos con clave primaria UUID, marcas de tiempo e índices.
3. Añadir a `CustomUser` las propiedades de la matriz (`puede_ver_*`, `puede_gestionar_*`).
4. Proteger las vistas con `requiere_acceso('<propiedad>')` u otro decorador equivalente.
5. Añadir la entrada al menú lateral condicionada a **la misma propiedad**.
6. Registrar las acciones de escritura con `registrar_actividad(...)`.
7. Crear plantillas bajo `templates/<app>/` extendiendo `layouts/base.html`.
8. Documentar el caso de uso y actualizar esta documentación.

### 20.2 Tareas periódicas recomendadas

| Tarea | Frecuencia |
|---|---|
| Verificación de respaldos | Semanal |
| Revisión de la bitácora de accesos denegados | Semanal |
| Revisión de cuentas inactivas y bajas de personal | Mensual |
| Actualización de dependencias con parches de seguridad | Trimestral |
| Depuración de notificaciones archivadas | Semestral |

### 20.3 Líneas de evolución sugeridas

1. Envío automático programado de reportes periódicos al MSP.
2. Notificaciones por SMS o mensajería para recordatorios de cita a las familias.
3. Tablero de indicadores en tiempo real por centro de salud.
4. Interoperabilidad HL7/FHIR con sistemas hospitalarios.
5. Aplicación móvil dedicada al portal de padres.
6. Firma digital de referencias y contrarreferencias.

---

## 21. Riesgos identificados

| # | Riesgo | Impacto | Mitigación implementada / recomendada |
|---|---|---|---|
| 1 | Pérdida de `FACCI_ENCRYPTION_KEY` | Crítico: datos cifrados irrecuperables | Custodia fuera del servidor y respaldo documentado |
| 2 | Uso de credenciales de demostración en producción | Crítico | `seed_data` bloqueado con `DEBUG=False`; cambio obligatorio de contraseñas iniciales |
| 3 | Exposición de datos clínicos por rol mal asignado | Alto | Matriz única de permisos, filtrado por alcance de datos y bitácora de accesos denegados |
| 4 | Caída del servicio externo de geocodificación | Bajo | El sistema continúa operando sin coordenadas; se puede reintentar por API |
| 5 | Crecimiento de `MEDIA_ROOT` sin control | Medio | Política de respaldo y depuración periódica de reportes antiguos |
| 6 | Dependencia de un solo administrador | Medio | Designar al menos dos cuentas con rol `ADMIN` |
| 7 | Fallo del envío SMTP al remitir reportes | Bajo | El error se informa al usuario y el reporte queda guardado para descarga manual |

---

## 22. Entregables del proyecto

| # | Entregable | Descripción | Formato / medio de entrega |
|---|---|---|---|
| 1 | **Documentación** | El presente documento, en el que se detallan todos los pormenores del proyecto: justificación, objetivos, alcance, arquitectura, modelo de datos, módulos, reglas de negocio, seguridad, instalación, despliegue, pruebas y mantenimiento. | Documento digital (Markdown/PDF) en el repositorio |
| 2 | **Manual de usuario** | Documento con instrucciones sobre el uso de las herramientas de administración del sitio web, dirigido al personal que opera el sistema. | Documento digital enviado **por correo electrónico** a los responsables de FACCI |

Ambos documentos se versionan junto con el código fuente en el directorio `documentacion/` del repositorio, de modo que cualquier cambio funcional quede reflejado en la documentación correspondiente.

---

## 23. Glosario

| Término | Definición |
|---|---|
| **Alarma mayor** | Signo del cribado que, por sí solo, clasifica el caso como riesgo alto: dolor de cabeza persistente, vómitos matutinos, masa abdominal palpable o leucocoria. |
| **Alcance de datos** | Conjunto de registros que un usuario puede ver, independientemente de a qué pantalla tenga acceso. |
| **Casa FACCI** | Alojamiento que la fundación ofrece a las familias que deben trasladarse para el tratamiento del paciente. |
| **Contrarreferencia** | Documento con el que el especialista devuelve al médico referente el resultado de la atención. |
| **Cribado** | Cuestionario estructurado de detección temprana aplicado por el médico de primer nivel o el pediatra. |
| **Descargo de tratamiento** | Documento imprimible con las indicaciones médicas vigentes que se entrega a la familia. |
| **Estadio** | Grado de extensión de la enfermedad oncológica (I a IV, o No estadificado). |
| **Fase de protocolo** | Etapa del tratamiento oncológico: Inducción, Consolidación, Mantenimiento o Vigilancia. |
| **Fernet** | Esquema de cifrado simétrico autenticado (AES-128-CBC + HMAC-SHA256) usado para los campos sensibles. |
| **ICD-O3** | Clasificación Internacional de Enfermedades para Oncología, tercera edición; usada en el reporte PENCI-RD. |
| **JWT** | JSON Web Token; formato de token usado por la API. |
| **Leucocoria** | Reflejo pupilar blanquecino; signo principal de sospecha de retinoblastoma. |
| **Matriz operativa** | Tablero de coordinación con indicadores por centro de salud y provincia en un período dado. |
| **MSP** | Ministerio de Salud Pública de la República Dominicana. |
| **PENCI-RD** | Programa/registro nacional de cáncer infantil de la República Dominicana; formato de reporte estadístico. |
| **PIN** | Clave numérica de 6 dígitos con la que el padre o tutor accede a su portal. |
| **Referencia médica** | Derivación formal de un paciente hacia un especialista o centro de mayor nivel. |
| **Throttling** | Límite de peticiones por unidad de tiempo aplicado a la API. |

---

## 24. Anexos

### Anexo A — Mapa de rutas principales

| Ruta | Módulo | Acceso |
|---|---|---|
| `/` | Inicio (redirige según rol) | Autenticado |
| `/login/` | Acceso del personal | Público |
| `/acceso/padres/` | Acceso de padres/tutores | Público |
| `/dashboard/` | Dashboard por rol | Personal |
| `/pacientes/` | Pacientes y expediente | Personal |
| `/cribado/` | Cribado | Equipo asistencial |
| `/referencias/` | Referencias y contrarreferencias | Equipo clínico + Coordinación (lectura) |
| `/seguimiento/` · `/seguimientos/` | Seguimiento clínico | Equipo clínico ampliado |
| `/indicaciones/` | Indicaciones médicas | Equipo asistencial |
| `/laboratorio/` | Laboratorio | Equipo asistencial |
| `/psicosocial/` | Evaluaciones psicosociales | Equipo FACCI + Admin |
| `/alojamiento/` | Casa FACCI | Equipo FACCI + clínicos (lectura) |
| `/documentos/` | Documentos y solicitudes | Personal |
| `/reportes/` | Reportes y PENCI-RD | Personal (generación: Admin y Coordinador) |
| `/alertas/` | Alertas clínicas | Equipo clínico ampliado |
| `/matrices/` | Matrices operativas | Admin y Coordinador FACCI |
| `/centros-salud/` | Centros de salud | Personal (edición: Admin) |
| `/usuarios/` | Gestión de usuarios | Admin |
| `/auditoria/` | Auditoría | Admin |
| `/ajustes/` | Ajustes del sistema | Admin |
| `/notificaciones/` · `/mensajes/` | Notificaciones | Autenticado |
| `/padres/` | Portal de padres | Padre / Tutor |
| `/recursos/` | Recursos educativos | Autenticado |
| `/admin/` | Django Admin | Superusuario |
| `/api/…` | API REST | Autenticado (JWT o sesión) |

### Anexo B — Catálogos de valores

**Estado del paciente:** Sospechoso · Referido · En estudio · Confirmado · Descartado · En tratamiento · En remisión · Finalizado

**Diagnóstico:** Leucemia · Tumores del SNC · Retinoblastoma · Tumor de Wilms · Neuroblastoma · Otro

**Estado de la referencia:** Pendiente · Aceptada · En proceso · Completada · Cancelada

**Prioridad de la referencia:** Baja · Media · Alta · Urgente

**Resultado de la atención (contrarreferencia):** Diagnóstico confirmado — en seguimiento FACCI · Tratamiento iniciado · Derivado a otro nivel de atención · Alta médica — descartado · Paciente no se presentó · Paciente fallecido

**Fase de protocolo:** Inducción · Consolidación · Mantenimiento · Vigilancia

**Tipo de indicación:** Medicación · Protocolo activo · Pauta médica específica · Hidratación · Descanso · Alimentación · Higiene · Otra

**Tipo de documento:** Hemograma · Analítica · Radiografía · Sonografía · Resonancia · Tomografía · Biopsia · Receta médica · Informe médico · Referimiento · Laboratorio · Otro

**Estado del documento:** Pendiente · Revisado · Requiere corrección

**Tipo de examen de laboratorio:** Hemograma/BHC · Química sanguínea · Coagulación · Análisis de orina · Cultivo microbiológico · Imagenología · Anatomía patológica · Marcadores tumorales · Otro

**Motivo de estancia en Casa FACCI:** Ciclo de quimioterapia · Intervención quirúrgica · Radioterapia · Hospitalización prolongada · Consulta/exámenes · Otro

**Tipo de alerta clínica:** Síntomas de alarma · Sospechoso sin referencia · Referencia sin seguimiento · Seguimiento pendiente o vencido · Alta prioridad sin revisión · Documento clínico pendiente · Caso crítico

**Formato de reporte:** PDF · Excel (.xlsx) · CSV

**Período de reporte:** Último mes · Últimos 3 meses · Últimos 6 meses · Último año · Rango personalizado

### Anexo C — Comandos de administración frecuentes

```bash
python manage.py migrate                 # Aplicar migraciones
python manage.py makemigrations          # Generar migraciones tras cambiar modelos
python manage.py createsuperuser         # Crear superusuario del Django Admin
python manage.py seed_data               # Datos de demostración (solo con DEBUG=True)
python manage.py collectstatic           # Consolidar archivos estáticos
python manage.py test                    # Ejecutar la batería de pruebas
python manage.py changepassword <user>   # Cambiar la contraseña de un usuario
python manage.py shell                   # Consola interactiva de Django
```

---

*Fin del documento — Documentación del Proyecto FACCI Care, versión 1.0.*
