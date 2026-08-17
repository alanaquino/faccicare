# Diccionario Físico de la Base de Datos — FACCI Care

**Especificación detallada de tablas, columnas, tipos, claves e índices**
Fundación de Apoyo Contra el Cáncer Infantil (FACCI) — República Dominicana

| Campo | Detalle |
|---|---|
| **Tipo de entregable** | Diccionario físico de la base de datos |
| **Versión del documento** | 1.0 |
| **Fecha de emisión** | Agosto 2026 |
| **Tablas documentadas** | 32 tablas propias (463 columnas) |
| **Motores** | SQLite 3 (desarrollo) · MySQL 8 (producción) |
| **Origen** | Introspección de la base de datos generada por las migraciones del repositorio |
| **Documentos relacionados** | `03-Modelo-de-Datos.md` (conceptual) · `04-Diagrama-de-Base-de-Datos.md` (diagrama) |

---

## Cómo leer este diccionario

Cada tabla se documenta con una ficha que incluye la entidad que representa, el modelo que la implementa, el ordenamiento por defecto de sus consultas, el detalle de todas sus columnas y sus índices.

### Columnas de la ficha

| Encabezado | Significado |
|---|---|
| **#** | Posición de la columna dentro de la tabla |
| **Columna** | Nombre físico de la columna |
| **Tipo (SQLite)** | Tipo con el que se crea en el entorno de desarrollo |
| **Tipo (MySQL)** | Tipo equivalente en el entorno de producción |
| **Nulo** | «Sí» si admite valor nulo; «No» si es obligatoria a nivel de base de datos |
| **Clave** | `PK` primaria · `FK` foránea · `UQ` única · `IX` indexada |
| **Predet.** | Valor predeterminado aplicado al insertar |
| **Descripción** | Significado de la columna, valores admitidos, tabla referenciada y política de borrado |

### Convenciones

1. **Obligatoriedad.** «Nulo = No» significa que la base rechaza un valor nulo. Muchas columnas de texto se declaran no nulas pero admiten cadena vacía; en esos casos la obligatoriedad real se valida en los formularios de la aplicación.
2. **Claves foráneas.** Se indican como `→ tabla.columna (ON DELETE política)`. `RESTRICT` corresponde a `PROTECT` en el modelo: impide eliminar el registro padre.
3. **Valores de dominio.** Cuando la columna admite un conjunto cerrado de valores, se listan los códigos almacenados. Sus etiquetas legibles están en el documento del modelo de datos, sección 9.
4. **Columnas cifradas.** Marcadas como **Cifrado en reposo (Fernet)**. Almacenan texto cifrado con prefijo `enc:` y **no admiten filtrado ni ordenamiento en SQL**.
5. **Archivos.** Las columnas de tipo `varchar(100)` que corresponden a archivos o imágenes almacenan la **ruta relativa** dentro de `MEDIA_ROOT`, nunca el contenido binario.
6. **Marcas de tiempo.** `created_at` se fija en la inserción y `updated_at` se actualiza en cada modificación; ambas las gestiona el ORM.

### Advertencia sobre modificación directa

Este diccionario es una referencia de **consulta**. Las tablas no deben alterarse con sentencias DDL manuales: todo cambio de estructura debe realizarse mediante migraciones de Django, o el esquema quedará desincronizado del código y las siguientes migraciones fallarán.

---

## Índice de tablas por módulo

| Módulo | Tablas |
|---|---|
| `core` — Núcleo y configuración | `core_centrosalud` · `core_logactividad` · `core_sistemaconfiguracion` |
| `auth_app` — Seguridad y usuarios | `auth_app_customuser` |
| `padres` — Familia y portal de padres | `padres_padretutor` · `padres_recursoeducativo` · `padres_registrotomamedicamento` · `padres_reportesintoma` |
| `pacientes` — Pacientes | `pacientes_paciente` · `pacientes_notaclinica` |
| `cribado` — Cribado | `cribado_cuestionariocribado` |
| `referencias` — Referencias | `referencias_referenciamedica` · `referencias_contrarreferencia` · `referencias_referenciaingresocasafacci` |
| `seguimiento` — Seguimiento | `seguimiento_seguimientopaciente` · `seguimiento_indicacionmedica` |
| `casos` — Casos clínicos | `casos_casoclinico` · `casos_notacaso` |
| `laboratorio` — Laboratorio | `laboratorio_catalogoestudio` · `laboratorio_catalogoparametro` · `laboratorio_resultadolaboratorio` · `laboratorio_valorresultado` |
| `psicosocial` — Psicosocial | `psicosocial_evaluacionpsicosocial` |
| `alojamiento` — Casa FACCI | `alojamiento_habitacioncasa` · `alojamiento_estanciafamiliar` · `alojamiento_entregahabitacion` · `alojamiento_itementregahabitacion` |
| `documentos` — Documentos | `documentos_documentomedico` · `documentos_solicituddocumento` |
| `reportes` — Reportes | `reportes_reportegenerado` |
| `notificaciones` — Notificaciones | `notificaciones_notificacion` |
| `dashboard` — Alertas clínicas | `dashboard_alertaclinica` |

---

## Módulo `core` — Núcleo y configuración


### 1. Tabla `core_centrosalud`

**Entidad:** Centro de salud · **Modelo:** `core.CentroSalud` · **Columnas:** 23

**Ordenamiento por defecto:** `nombre`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | INTEGER | bigint AUTO_INCREMENT | No | **PK** | — | ID |
| 2 | `nombre` | varchar(150) | varchar(150) | No | — | — | Nombre del centro |
| 3 | `tipo` | varchar(30) | varchar(30) | No | — | `hospital` | Tipo. Valores: hospital, clinica, unidad_atencion, centro_diagnostico, otro |
| 4 | `provincia` | varchar(100) | varchar(100) | No | — | — | Provincia / Ciudad |
| 5 | `municipio` | varchar(100) | varchar(100) | No | — | — | Municipio |
| 6 | `direccion` | varchar(255) | varchar(255) | No | — | — | Dirección exacta |
| 7 | `telefono` | varchar(30) | varchar(30) | No | — | — | Telefono |
| 8 | `correo` | varchar(254) | varchar(254) | No | — | — | Correo |
| 9 | `camas_disponibles` | integer unsigned | integer UNSIGNED | No | — | `0` | Camas oncológicas disponibles |
| 10 | `camas_total` | integer unsigned | integer UNSIGNED | No | — | `0` | Camas oncológicas total |
| 11 | `estado_derivacion` | varchar(20) | varchar(20) | No | — | `disponible` | Estado de derivación. Valores: disponible, limitado, no_disponible, mantenimiento |
| 12 | `esp_oncologia_pediatrica` | bool | bool | No | — | False | Oncología Pediátrica |
| 13 | `esp_pediatria_general` | bool | bool | No | — | False | Pediatría General |
| 14 | `esp_imagenes_diagnosticas` | bool | bool | No | — | False | Imágenes Diagnósticas |
| 15 | `esp_laboratorio_avanzado` | bool | bool | No | — | False | Laboratorio Clínico Avanzado |
| 16 | `medicos_titulares` | integer unsigned | integer UNSIGNED | No | — | `0` | Médicos titulares en turno |
| 17 | `entrenados_facci` | integer unsigned | integer UNSIGNED | No | — | `0` | Entrenados FACCI |
| 18 | `latitud` | REAL | double precision | Sí | — | — | Latitud |
| 19 | `longitud` | REAL | double precision | Sí | — | — | Longitud |
| 20 | `direccion_normalizada` | varchar(255) | varchar(255) | Sí | — | — | Direccion normalizada |
| 21 | `coordenadas_actualizadas` | datetime | datetime(6) | Sí | — | — | Coordenadas actualizadas |
| 22 | `activo` | bool | bool | No | — | True | Activo |
| 23 | `fecha_creacion` | datetime | datetime(6) | No | — | — | Fecha creacion |


### 2. Tabla `core_logactividad`

**Entidad:** Log de actividad · **Modelo:** `core.LogActividad` · **Columnas:** 11

**Ordenamiento por defecto:** `-fecha`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | INTEGER | bigint AUTO_INCREMENT | No | **PK** | — | ID |
| 2 | `usuario_id` | char(32) | char(32) | Sí | FK IX | — | Usuario. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 3 | `accion` | varchar(80) | varchar(80) | No | — | — | Accion |
| 4 | `tipo_accion` | varchar(20) | varchar(20) | No | IX | `CONSULTA` | Tipo accion. Valores: CREACION, EDICION, ELIMINACION, CONSULTA, LOGIN, LOGOUT, REPORTE |
| 5 | `modelo` | varchar(100) | varchar(100) | No | — | — | Modelo |
| 6 | `modulo` | varchar(80) | varchar(80) | No | IX | — | Modulo |
| 7 | `objeto_id` | varchar(80) | varchar(80) | No | — | — | Objeto id |
| 8 | `objeto_repr` | varchar(220) | varchar(220) | No | — | — | Objeto repr |
| 9 | `descripcion` | TEXT | longtext | No | — | — | Descripcion |
| 10 | `direccion_ip` | char(39) | char(39) | Sí | — | — | Direccion ip |
| 11 | `fecha` | datetime | datetime(6) | No | — | — | Fecha |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `core_logactividad_modulo_be8c5cbf` | `modulo` | No |
| `core_logactividad_tipo_accion_8040e457` | `tipo_accion` | No |
| `core_logactividad_usuario_id_c04ce032` | `usuario_id` | No |
| `logactividad_fecha_idx` | `fecha` | No |
| `logactividad_modulo_idx` | `modulo` | No |
| `logactividad_tipo_idx` | `tipo_accion` | No |


### 3. Tabla `core_sistemaconfiguracion`

**Entidad:** Configuración del sistema · **Modelo:** `core.SistemaConfiguracion` · **Columnas:** 6


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | INTEGER | bigint AUTO_INCREMENT | No | **PK** | — | ID |
| 2 | `logo` | varchar(100) | varchar(100) | Sí | — | — | Logo del sistema (Legacy) |
| 3 | `nombre_institucion` | varchar(150) | varchar(150) | No | — | `Fundación de Apoyo Contra el Cáncer Infantil (FACCI)` | Nombre de la institución |
| 4 | `nombre_aplicacion` | varchar(150) | varchar(150) | No | — | `FACCI Care` | Nombre de la aplicación |
| 5 | `logo_aplicacion` | varchar(100) | varchar(100) | Sí | — | — | Logo de la aplicación |
| 6 | `logo_reportes` | varchar(100) | varchar(100) | Sí | — | — | Logo oficial para reportes |


## Módulo `auth_app` — Seguridad y usuarios


### 4. Tabla `auth_app_customuser`

**Entidad:** Usuario · **Modelo:** `auth_app.CustomUser` · **Columnas:** 20

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `password` | varchar(128) | varchar(128) | No | — | — | Contraseña |
| 2 | `last_login` | datetime | datetime(6) | Sí | — | — | Último inicio de sesión |
| 3 | `is_superuser` | bool | bool | No | — | False | Estado de superusuario. Indica que este usuario tiene todos los permisos sin asignárselos explícitamente. |
| 4 | `username` | varchar(150) | varchar(150) | No | UQ | — | Nombre de usuario. Requerido. 150 carácteres como máximo. Únicamente letras, dígitos y @/./+/-/_ |
| 5 | `first_name` | varchar(150) | varchar(150) | No | — | — | Nombre |
| 6 | `last_name` | varchar(150) | varchar(150) | No | — | — | Apellidos |
| 7 | `email` | varchar(254) | varchar(254) | No | — | — | Dirección de correo electrónico |
| 8 | `is_staff` | bool | bool | No | — | False | Es staff. Indica si el usuario puede entrar en este sitio de administración. |
| 9 | `is_active` | bool | bool | No | — | True | Activo. Indica si el usuario debe ser tratado como activo. Desmarque esta opción en lugar de borrar la cuenta. |
| 10 | `date_joined` | datetime | datetime(6) | No | — | `<function now at 0x7f9278493e20>` | Fecha de alta |
| 11 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 12 | `telefono` | varchar(512) | varchar(512) | No | — | — | Teléfono. **Cifrado en reposo (Fernet)**. Número de contacto principal |
| 13 | `tipo_documento` | varchar(20) | varchar(20) | No | — | `CEDULA` | Tipo de documento. Valores: CEDULA, PASAPORTE |
| 14 | `cedula` | varchar(20) | varchar(20) | Sí | UQ | `None` | Cédula. Cédula de identidad dominicana (ej. 001-0000000-0) |
| 15 | `foto_perfil` | varchar(100) | varchar(100) | No | — | — | Foto de perfil |
| 16 | `rol` | varchar(25) | varchar(25) | No | IX | `MEDICO` | Rol. Valores: ADMIN, MEDICO, PEDIATRA, ONCOLOGO, PERSONAL_FACCI, TRABAJADORA_SOCIAL, ENFERMERA, PADRE_TUTOR |
| 17 | `especialidad` | varchar(100) | varchar(100) | No | — | — | Especialidad médica |
| 18 | `centro_medico_id` | bigint | bigint | Sí | FK IX | — | Centro médico. → `core_centrosalud`.`id` (ON DELETE SET_NULL). Hospital o clínica donde labora |
| 19 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 20 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `auth_app_customuser_centro_medico_id_f58c344a` | `centro_medico_id` | No |
| `auth_app_customuser_rol_745a18e3` | `rol` | No |
| `customuser_cedula_idx` | `cedula` | No |
| `customuser_email_idx` | `email` | No |
| `customuser_rol_idx` | `rol` | No |


## Módulo `padres` — Familia y portal de padres


### 5. Tabla `padres_padretutor`

**Entidad:** Padre / tutor · **Modelo:** `padres.PadreTutor` · **Columnas:** 15

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `usuario_id` | char(32) | char(32) | No | FK UQ | — | Usuario. → `auth_app_customuser`.`id` (ON DELETE CASCADE) |
| 3 | `parentesco` | varchar(20) | varchar(20) | No | — | `PADRE` | Parentesco. Valores: PADRE, MADRE, ABUELO, TIO, TUTOR, OTRO |
| 4 | `nacionalidad` | varchar(80) | varchar(80) | Sí | — | `Dominicana` | Nacionalidad. Nacionalidad legal del padre, madre o tutor responsable |
| 5 | `direccion` | TEXT | longtext | No | — | — | Dirección. **Cifrado en reposo (Fernet)**. Dirección completa de residencia |
| 6 | `provincia` | varchar(100) | varchar(100) | No | — | — | Provincia |
| 7 | `municipio` | varchar(100) | varchar(100) | No | — | — | Municipio |
| 8 | `ocupacion` | varchar(100) | varchar(100) | No | — | — | Ocupación |
| 9 | `contacto_emergencia` | varchar(512) | varchar(512) | No | — | — | Contacto de emergencia. **Cifrado en reposo (Fernet)**. Nombre del contacto de emergencia |
| 10 | `telefono_emergencia` | varchar(512) | varchar(512) | No | — | — | Teléfono de emergencia. **Cifrado en reposo (Fernet)** |
| 11 | `estado_civil` | varchar(20) | varchar(20) | No | — | — | Estado civil. Valores: SOLTERO, CASADO, UNION_LIBRE, DIVORCIADO, VIUDO |
| 12 | `cantidad_hijos` | smallint unsigned | smallint UNSIGNED | No | — | `1` | Cantidad de hijos |
| 13 | `ingresos_aproximados` | varchar(50) | varchar(50) | No | — | — | Ingresos aproximados. Rango mensual en pesos dominicanos (ej. RD$10,000–20,000) |
| 14 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 15 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `padretutor_provincia_idx` | `provincia` | No |


### 6. Tabla `padres_recursoeducativo`

**Entidad:** Recurso educativo · **Modelo:** `padres.RecursoEducativo` · **Columnas:** 18

**Ordenamiento por defecto:** `orden, titulo`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `titulo` | varchar(255) | varchar(255) | No | — | — | Título del recurso |
| 3 | `slug` | varchar(255) | varchar(255) | No | UQ | — | Identificador URL |
| 4 | `descripcion` | TEXT | longtext | No | — | — | Descripción. Contenido educativo del recurso |
| 5 | `descripcion_corta` | TEXT | longtext | No | — | — | Descripción corta. Resumen que se muestra en la tarjeta del recurso |
| 6 | `contenido` | TEXT | longtext | No | — | — | Contenido completo |
| 7 | `actividades` | TEXT | json | No | — | `<class 'list'>` | Actividades recomendadas |
| 8 | `pasos_padres` | TEXT | json | No | — | `<class 'list'>` | Qué puede hacer el padre, madre o tutor |
| 9 | `cuando_contactar` | TEXT | json | No | — | `<class 'list'>` | Cuándo contactar al equipo médico |
| 10 | `icono` | varchar(50) | varchar(50) | No | — | `info` | Icono Material Design. Nombre del icono (ej. restaurant, favorite, help) |
| 11 | `categoria` | varchar(50) | varchar(50) | No | — | `OTRO` | Categoría. Valores: ALIMENTACION, APOYO_EMOCIONAL, PREGUNTAS_FRECUENTES, MEDICAMENTOS, ACTIVIDAD_FISICA, HIGIENE, JUEGOS_ACTIVIDADES, APOYO_ESCOLAR, SENALES_ALERTA, CUIDADO_CASA, OTRO |
| 12 | `url` | varchar(200) | varchar(200) | No | — | — | Enlace externo. URL opcional a recurso externo |
| 13 | `imagen` | varchar(500) | varchar(500) | No | — | — | Imagen. Ruta dentro de static (ej. img/recurso.jpg) o URL absoluta |
| 14 | `video_url` | varchar(200) | varchar(200) | No | — | — | Video relacionado. Enlace opcional de YouTube |
| 15 | `activo` | bool | bool | No | — | True | Activo |
| 16 | `orden` | smallint unsigned | smallint UNSIGNED | No | — | `0` | Orden |
| 17 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 18 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `recurso_activo_cat_idx` | `activo`, `categoria` | No |


### 7. Tabla `padres_registrotomamedicamento`

**Entidad:** Registro de toma de medicamento · **Modelo:** `padres.RegistroTomaMedicamento` · **Columnas:** 7

**Ordenamiento por defecto:** `-fecha, indice`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `tutor_id` | char(32) | char(32) | Sí | FK IX | — | Tutor que registró. → `padres_padretutor`.`id` (ON DELETE SET_NULL) |
| 4 | `nombre_medicamento` | varchar(200) | varchar(200) | No | — | — | Nombre del medicamento |
| 5 | `indice` | smallint unsigned | smallint UNSIGNED | No | — | — | Índice en la lista del día. Posición del medicamento en la lista del día (para identificación) |
| 6 | `fecha` | date | date | No | IX | — | Fecha |
| 7 | `tomado_a` | datetime | datetime(6) | No | — | — | Marcado como tomado a las |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `padres_registrotomamedicamento_fecha_4e85e908` | `fecha` | No |
| `padres_registrotomamedicamento_paciente_id_073de234` | `paciente_id` | No |
| `padres_registrotomamedicamento_paciente_id_nombre_medicamento_indice_fecha_0a689286_uniq` | `paciente_id`, `nombre_medicamento`, `indice`, `fecha` | Sí |
| `padres_registrotomamedicamento_tutor_id_e78035e5` | `tutor_id` | No |
| `regtoma_paciente_fecha_idx` | `paciente_id`, `fecha` | No |

**Restricciones de unicidad compuesta**

- (`paciente`, `nombre_medicamento`, `indice`, `fecha`)


### 8. Tabla `padres_reportesintoma`

**Entidad:** Reporte de síntomas · **Modelo:** `padres.ReporteSintoma` · **Columnas:** 8

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `tutor_id` | char(32) | char(32) | Sí | FK IX | — | Tutor reportante. → `padres_padretutor`.`id` (ON DELETE SET_NULL) |
| 4 | `fecha_inicio` | date | date | No | — | — | Fecha de inicio |
| 5 | `gravedad` | varchar(20) | varchar(20) | No | — | `Leve` | Gravedad. Valores: Leve, Moderada, Severa |
| 6 | `sintomas` | TEXT | json | No | — | `<class 'list'>` | Síntomas reportados |
| 7 | `descripcion` | TEXT | longtext | No | — | — | Descripción adicional |
| 8 | `created_at` | datetime | datetime(6) | No | — | — | Enviado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `padres_reportesintoma_paciente_id_75216f76` | `paciente_id` | No |
| `padres_reportesintoma_tutor_id_5d67b959` | `tutor_id` | No |


## Módulo `pacientes` — Pacientes


### 9. Tabla `pacientes_notaclinica`

**Entidad:** Nota clinica · **Modelo:** `pacientes.NotaClinica` · **Columnas:** 8

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `autor_id` | char(32) | char(32) | No | FK IX | — | Autor. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `tipo` | varchar(20) | varchar(20) | No | IX | `EVOLUCION` | Tipo de nota. Valores: EVOLUCION, DIAGNOSTICO, TRATAMIENTO, OBSERVACION, ALERTA |
| 5 | `texto` | TEXT | longtext | No | — | — | Nota clinica |
| 6 | `es_importante` | bool | bool | No | — | False | Marcar como importante |
| 7 | `created_at` | datetime | datetime(6) | No | — | — | Registrada el |
| 8 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizada el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `nota_fecha_idx` | `created_at` | No |
| `nota_paciente_idx` | `paciente_id` | No |
| `nota_tipo_idx` | `tipo` | No |
| `pacientes_notaclinica_autor_id_baf44daa` | `autor_id` | No |
| `pacientes_notaclinica_paciente_id_14a1707f` | `paciente_id` | No |
| `pacientes_notaclinica_tipo_a5ea9345` | `tipo` | No |


### 10. Tabla `pacientes_paciente`

**Entidad:** Paciente · **Modelo:** `pacientes.Paciente` · **Columnas:** 25

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `codigo_paciente` | varchar(20) | varchar(20) | No | UQ | — | Código de paciente. Código único generado automáticamente (ej. FACCI-20240001) |
| 3 | `nombres` | varchar(150) | varchar(150) | No | — | — | Nombres |
| 4 | `apellidos` | varchar(150) | varchar(150) | No | — | — | Apellidos |
| 5 | `fecha_nacimiento` | date | date | No | — | — | Fecha de nacimiento |
| 6 | `sexo` | varchar(1) | varchar(1) | No | — | — | Sexo. Valores: M, F |
| 7 | `tipo_sangre` | varchar(3) | varchar(3) | No | — | — | Tipo de sangre. Valores: A+, A-, B+, B-, AB+, AB-, O+, O- |
| 8 | `peso` | decimal | numeric(5, 2) | Sí | — | — | Peso (kg) |
| 9 | `altura` | decimal | numeric(5, 2) | Sí | — | — | Altura (cm) |
| 10 | `direccion` | TEXT | longtext | No | — | — | Dirección. **Cifrado en reposo (Fernet)** |
| 11 | `provincia` | varchar(100) | varchar(100) | No | — | — | Provincia |
| 12 | `municipio` | varchar(100) | varchar(100) | No | — | — | Municipio |
| 13 | `escuela` | varchar(200) | varchar(200) | No | — | — | Escuela |
| 14 | `seguro_medico` | varchar(100) | varchar(100) | No | — | — | Seguro médico |
| 15 | `numero_seguro` | varchar(50) | varchar(50) | No | — | — | Número de seguro |
| 16 | `alergias` | TEXT | longtext | No | — | — | Alergias conocidas. **Cifrado en reposo (Fernet)**. Listar alergias separadas por coma |
| 17 | `antecedentes_medicos` | TEXT | longtext | No | — | — | Antecedentes médicos. **Cifrado en reposo (Fernet)**. Historial de enfermedades, cirugías y condiciones previas |
| 18 | `estado_actual` | varchar(20) | varchar(20) | No | IX | `SOSPECHOSO` | Estado actual. Valores: SOSPECHOSO, REFERIDO, EN_ESTUDIO, CONFIRMADO, DESCARTADO, EN_TRATAMIENTO, EN_REMISION, FINALIZADO |
| 19 | `diagnostico` | varchar(20) | varchar(20) | No | IX | — | Diagnóstico. Valores: LEUCEMIA, TUMORES_SNC, RETINOBLASTOMA, TUMOR_WILMS, NEUROBLASTOMA, OTRO |
| 20 | `fotografia` | varchar(100) | varchar(100) | No | — | — | Fotografía |
| 21 | `padre_tutor_id` | char(32) | char(32) | No | FK IX | — | Padre / Tutor. → `padres_padretutor`.`id` (ON DELETE PROTECT) |
| 22 | `medico_asignado_id` | char(32) | char(32) | Sí | FK IX | — | Médico asignado. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 23 | `creado_por_id` | char(32) | char(32) | Sí | FK IX | — | Creado por. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 24 | `created_at` | datetime | datetime(6) | No | — | — | Registrado el |
| 25 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `paciente_codigo_idx` | `codigo_paciente` | No |
| `paciente_estado_idx` | `estado_actual` | No |
| `paciente_padre_idx` | `padre_tutor_id` | No |
| `paciente_provincia_idx` | `provincia` | No |
| `pacientes_paciente_creado_por_id_fdb1a62b` | `creado_por_id` | No |
| `pacientes_paciente_diagnostico_f8f806c0` | `diagnostico` | No |
| `pacientes_paciente_estado_actual_d999e659` | `estado_actual` | No |
| `pacientes_paciente_medico_asignado_id_ec7d763f` | `medico_asignado_id` | No |
| `pacientes_paciente_padre_tutor_id_7d06c513` | `padre_tutor_id` | No |


## Módulo `cribado` — Cribado


### 11. Tabla `cribado_cuestionariocribado`

**Entidad:** Cuestionario de cribado · **Modelo:** `cribado.CuestionarioCribado` · **Columnas:** 24

**Ordenamiento por defecto:** `-fecha_evaluacion`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `medico_id` | char(32) | char(32) | No | FK IX | — | Medico evaluador. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `fecha_evaluacion` | datetime | datetime(6) | No | — | — | Fecha de evaluacion |
| 5 | `fiebre_persistente` | bool | bool | No | — | False | Fiebre persistente (>2 semanas). Temperatura >38 C sin causa aparente por mas de 2 semanas |
| 6 | `perdida_peso` | bool | bool | No | — | False | Perdida de peso inexplicable |
| 7 | `dolor_huesos` | bool | bool | No | — | False | Dolor en huesos o articulaciones |
| 8 | `palidez` | bool | bool | No | — | False | Palidez marcada |
| 9 | `fatiga` | bool | bool | No | — | False | Fatiga o cansancio extremo |
| 10 | `moretones` | bool | bool | No | — | False | Moretones sin causa aparente |
| 11 | `sangrado` | bool | bool | No | — | False | Sangrado espontaneo. Encias, nariz u otras zonas sin traumatismo |
| 12 | `ganglios` | bool | bool | No | — | False | Ganglios inflamados. Linfadenopatia cervical, axilar o inguinal |
| 13 | `infecciones_recurrentes` | bool | bool | No | — | False | Infecciones recurrentes |
| 14 | `dolor_cabeza` | bool | bool | No | — | False | Dolor de cabeza persistente |
| 15 | `vomitos` | bool | bool | No | — | False | Vomitos matutinos sin causa gastrointestinal |
| 16 | `masa_abdominal` | bool | bool | No | — | False | Masa abdominal palpable |
| 17 | `leucocoria` | bool | bool | No | — | False | Leucocoria / reflejo ocular blanquecino. Pupila blanquecina o reflejo rojo ausente en fotografías — signo principal de retinoblastoma |
| 18 | `tipo_cancer_sospechado` | varchar(20) | varchar(20) | No | IX | — | Tipo de cáncer sospechado. Valores: LEUCEMIA, TUMORES_SNC, RETINOBLASTOMA, TUMOR_WILMS, NEUROBLASTOMA, LINFOMA, SARCOMA, SIN_DEFINIR. Tipo de cáncer que el médico sospecha según el cuadro clínico |
| 19 | `observaciones` | TEXT | longtext | No | — | — | Observaciones clinicas |
| 20 | `nivel_riesgo` | varchar(10) | varchar(10) | No | IX | `BAJO` | Nivel de riesgo. Valores: BAJO, MEDIO, ALTO |
| 21 | `resultado` | varchar(25) | varchar(25) | No | — | `SIN_SOSPECHA` | Resultado del cribado. Valores: SIN_SOSPECHA, SOSPECHA_MODERADA, SOSPECHA_ALTA |
| 22 | `requiere_referencia` | bool | bool | No | — | False | Requiere referencia a especialista |
| 23 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 24 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `cribado_cuestionariocribado_medico_id_48a49371` | `medico_id` | No |
| `cribado_cuestionariocribado_nivel_riesgo_27d53068` | `nivel_riesgo` | No |
| `cribado_cuestionariocribado_paciente_id_d5538e26` | `paciente_id` | No |
| `cribado_cuestionariocribado_tipo_cancer_sospechado_84271e12` | `tipo_cancer_sospechado` | No |
| `cribado_fecha_idx` | `fecha_evaluacion` | No |
| `cribado_nivel_idx` | `nivel_riesgo` | No |
| `cribado_paciente_idx` | `paciente_id` | No |
| `cribado_referencia_idx` | `requiere_referencia` | No |
| `cribado_tipo_cancer_idx` | `tipo_cancer_sospechado` | No |


## Módulo `referencias` — Referencias


### 12. Tabla `referencias_contrarreferencia`

**Entidad:** Contrarreferencia · **Modelo:** `referencias.Contrarreferencia` · **Columnas:** 16

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `referencia_id` | char(32) | char(32) | No | FK UQ | — | Referencia de origen. → `referencias_referenciamedica`.`id` (ON DELETE CASCADE) |
| 3 | `medico_contrarreferente_id` | char(32) | char(32) | No | FK IX | — | Médico que emite contrarreferencia. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `fecha_atencion` | date | date | No | — | — | Fecha de atención. Fecha en que el paciente fue atendido en el centro destino |
| 5 | `diagnostico` | TEXT | longtext | No | — | — | Diagnóstico establecido. Diagnóstico clínico o histopatológico confirmado |
| 6 | `tipo_cancer` | varchar(20) | varchar(20) | No | — | — | Tipo de cáncer confirmado. Valores: LEUCEMIA, TUMORES_SNC, RETINOBLASTOMA, TUMOR_WILMS, NEUROBLASTOMA, LINFOMA, SARCOMA, DESCARTADO, OTRO |
| 7 | `estadio` | varchar(3) | varchar(3) | No | — | `NE` | Estadio clínico. Valores: I, II, III, IV, NE |
| 8 | `tratamiento_realizado` | TEXT | longtext | No | — | — | Tratamiento realizado / indicado. Cirugía, quimioterapia, radioterapia, etc. |
| 9 | `estudios_realizados` | TEXT | longtext | No | — | — | Estudios y/o imágenes realizadas. Laboratorios, radiografías, TAC, RMN u otros estudios efectuados |
| 10 | `medicamentos_indicados` | TEXT | longtext | No | — | — | Medicamentos indicados. Fármacos prescritos con dosis y duración |
| 11 | `resultado_atencion` | varchar(30) | varchar(30) | No | IX | — | Resultado de la atención. Valores: CONFIRMADO_SEGUIMIENTO, TRATAMIENTO_INICIADO, DERIVADO_OTRO_NIVEL, ALTA_MEDICA, NO_PRESENTADO, FALLECIDO |
| 12 | `recomendaciones` | TEXT | longtext | No | — | — | Recomendaciones al médico referente. Indicaciones de seguimiento para el centro de origen |
| 13 | `requiere_seguimiento_facci` | bool | bool | No | — | True | Requiere seguimiento en FACCI |
| 14 | `proxima_cita` | date | date | Sí | — | — | Fecha próxima cita |
| 15 | `created_at` | datetime | datetime(6) | No | — | — | Created at |
| 16 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `referencias_contrarreferencia_medico_contrarreferente_id_352c83ec` | `medico_contrarreferente_id` | No |
| `referencias_contrarreferencia_resultado_atencion_b07c3eec` | `resultado_atencion` | No |


### 13. Tabla `referencias_referenciaingresocasafacci`

**Entidad:** Referencia ingreso casa facci · **Modelo:** `referencias.ReferenciaIngresoCasaFACCI` · **Columnas:** 22

**Ordenamiento por defecto:** `-fecha_creacion`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `referencia_medica_id` | char(32) | char(32) | Sí | FK IX | — | Referencia medica. → `referencias_referenciamedica`.`id` (ON DELETE SET_NULL) |
| 4 | `centro_origen_id` | bigint | bigint | Sí | FK IX | — | Centro de origen. → `core_centrosalud`.`id` (ON DELETE SET_NULL) |
| 5 | `hospital_destino_id` | bigint | bigint | Sí | FK IX | — | Hospital / destino. → `core_centrosalud`.`id` (ON DELETE SET_NULL) |
| 6 | `motivo_ingreso` | TEXT | longtext | No | — | — | Motivo de ingreso |
| 7 | `fecha_entrada` | date | date | No | — | — | Fecha de entrada |
| 8 | `fecha_salida` | date | date | Sí | — | — | Fecha de salida |
| 9 | `tiempo_estadia` | varchar(80) | varchar(80) | No | — | — | Tiempo estimado de estadia |
| 10 | `habitacion_id` | char(32) | char(32) | Sí | FK IX | — | Habitacion asignada. → `alojamiento_habitacioncasa`.`id` (ON DELETE SET_NULL) |
| 11 | `responsable_paciente` | varchar(150) | varchar(150) | No | — | — | Responsable del paciente |
| 12 | `parentesco_responsable` | varchar(60) | varchar(60) | No | — | — | Parentesco |
| 13 | `cedula_responsable` | varchar(20) | varchar(20) | No | — | — | Cedula |
| 14 | `telefono_responsable` | varchar(30) | varchar(30) | No | — | — | Telefono |
| 15 | `celular_responsable` | varchar(30) | varchar(30) | No | — | — | Celular |
| 16 | `direccion_responsable` | TEXT | longtext | No | — | — | Direccion |
| 17 | `ocupacion_responsable` | varchar(100) | varchar(100) | No | — | — | Ocupacion |
| 18 | `estado` | varchar(12) | varchar(12) | No | IX | `PENDIENTE` | Estado. Valores: PENDIENTE, APROBADA, INGRESADO, CANCELADA |
| 19 | `observaciones` | TEXT | longtext | No | — | — | Observaciones |
| 20 | `creado_por_id` | char(32) | char(32) | Sí | FK IX | — | Creado por. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 21 | `fecha_creacion` | datetime | datetime(6) | No | — | — | Fecha creacion |
| 22 | `fecha_actualizacion` | datetime | datetime(6) | No | — | — | Fecha actualizacion |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `ingreso_casa_entrada_idx` | `fecha_entrada` | No |
| `ingreso_casa_estado_idx` | `estado` | No |
| `ingreso_casa_paciente_idx` | `paciente_id` | No |
| `referencias_referenciaingresocasafacci_centro_origen_id_8e7f4e41` | `centro_origen_id` | No |
| `referencias_referenciaingresocasafacci_creado_por_id_50c9c96d` | `creado_por_id` | No |
| `referencias_referenciaingresocasafacci_estado_4d870e02` | `estado` | No |
| `referencias_referenciaingresocasafacci_habitacion_id_e7181063` | `habitacion_id` | No |
| `referencias_referenciaingresocasafacci_hospital_destino_id_3ab23c6f` | `hospital_destino_id` | No |
| `referencias_referenciaingresocasafacci_paciente_id_c6f2edd0` | `paciente_id` | No |
| `referencias_referenciaingresocasafacci_referencia_medica_id_1f657f08` | `referencia_medica_id` | No |


### 14. Tabla `referencias_referenciamedica`

**Entidad:** Referencia médica · **Modelo:** `referencias.ReferenciaMedica` · **Columnas:** 14

**Ordenamiento por defecto:** `-fecha_referencia`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `cuestionario_id` | char(32) | char(32) | Sí | FK IX | — | Cribado de origen. → `cribado_cuestionariocribado`.`id` (ON DELETE SET_NULL). Cuestionario que motivó esta referencia |
| 4 | `medico_referente_id` | char(32) | char(32) | No | FK IX | — | Médico referente. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 5 | `especialista_destino_id` | char(32) | char(32) | Sí | FK IX | — | Especialista destino. → `auth_app_customuser`.`id` (ON DELETE SET_NULL). Especialista dentro del sistema que recibirá al paciente |
| 6 | `hospital_destino_id` | bigint | bigint | Sí | FK IX | — | Hospital / Centro de destino. → `core_centrosalud`.`id` (ON DELETE PROTECT) |
| 7 | `motivo_referencia` | TEXT | longtext | No | — | — | Motivo de referencia. Descripción clínica que justifica la referencia |
| 8 | `prioridad` | varchar(10) | varchar(10) | No | IX | `MEDIA` | Prioridad. Valores: BAJA, MEDIA, ALTA, URGENTE |
| 9 | `estado` | varchar(15) | varchar(15) | No | IX | `PENDIENTE` | Estado. Valores: PENDIENTE, ACEPTADA, EN_PROCESO, COMPLETADA, CANCELADA |
| 10 | `fecha_referencia` | datetime | datetime(6) | No | IX | — | Fecha de referencia |
| 11 | `fecha_cita` | datetime | datetime(6) | Sí | — | — | Fecha de cita agendada |
| 12 | `observaciones` | TEXT | longtext | No | — | — | Observaciones adicionales |
| 13 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 14 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `referencia_estado_idx` | `estado` | No |
| `referencia_paciente_idx` | `paciente_id` | No |
| `referencia_prioridad_idx` | `prioridad` | No |
| `referencias_referenciamedica_cuestionario_id_c1a55283` | `cuestionario_id` | No |
| `referencias_referenciamedica_especialista_destino_id_633331b1` | `especialista_destino_id` | No |
| `referencias_referenciamedica_estado_f43b6e49` | `estado` | No |
| `referencias_referenciamedica_fecha_referencia_69dcb0f6` | `fecha_referencia` | No |
| `referencias_referenciamedica_hospital_destino_id_0c89f667` | `hospital_destino_id` | No |
| `referencias_referenciamedica_medico_referente_id_f2e2e37e` | `medico_referente_id` | No |
| `referencias_referenciamedica_paciente_id_c26c652f` | `paciente_id` | No |
| `referencias_referenciamedica_prioridad_411272c0` | `prioridad` | No |


## Módulo `seguimiento` — Seguimiento


### 15. Tabla `seguimiento_indicacionmedica`

**Entidad:** Indicación médica · **Modelo:** `seguimiento.IndicacionMedica` · **Columnas:** 11

**Ordenamiento por defecto:** `prioridad, -created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `medico_id` | char(32) | char(32) | No | FK IX | — | Médico tratante. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `tipo_indicacion` | varchar(50) | varchar(50) | No | — | `OTRA` | Tipo de indicación. Valores: MEDICACION, PROTOCOLO_ACTIVO, PAUTA_MEDICA, HIDRATACION, DESCANSO, ALIMENTACION, HIGIENE, OTRA |
| 5 | `titulo` | varchar(200) | varchar(200) | No | — | — | Título de la indicación |
| 6 | `descripcion` | TEXT | longtext | No | — | — | Descripción / Instrucciones |
| 7 | `prioridad` | varchar(10) | varchar(10) | No | — | `MEDIA` | Nivel de prioridad. Valores: ALTA, MEDIA, BAJA |
| 8 | `activa` | bool | bool | No | — | True | Activa |
| 9 | `visible_padre` | bool | bool | No | — | True | Visible para padre/tutor. Permite mostrar esta indicación en el Portal Padres. |
| 10 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 11 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `seguimiento_indicacionmedica_medico_id_1f5c4e9c` | `medico_id` | No |
| `seguimiento_indicacionmedica_paciente_id_0af43f6a` | `paciente_id` | No |


### 16. Tabla `seguimiento_seguimientopaciente`

**Entidad:** Seguimiento de paciente · **Modelo:** `seguimiento.SeguimientoPaciente` · **Columnas:** 18

**Ordenamiento por defecto:** `-fecha_seguimiento`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `medico_id` | char(32) | char(32) | No | FK IX | — | Médico tratante. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `fecha_seguimiento` | datetime | datetime(6) | No | — | — | Fecha del seguimiento |
| 5 | `fase_protocolo` | varchar(20) | varchar(20) | No | — | `VIGILANCIA` | Fase del protocolo. Valores: INDUCCION, CONSOLIDACION, MANTENIMIENTO, VIGILANCIA |
| 6 | `estado_clinico` | varchar(200) | varchar(200) | No | — | — | Estado clínico actual. Resumen breve del estado del paciente en esta consulta |
| 7 | `sintomas_actuales` | TEXT | longtext | No | — | — | Síntomas actuales |
| 8 | `tratamiento_actual` | TEXT | longtext | No | — | — | Tratamiento en curso. Descripción del protocolo de tratamiento activo |
| 9 | `medicamentos` | TEXT | longtext | No | — | — | Medicamentos indicados. Lista de medicamentos, dosis y frecuencia |
| 10 | `observaciones` | TEXT | longtext | No | — | — | Observaciones del médico |
| 11 | `proxima_fecha_seguimiento` | datetime | datetime(6) | Sí | — | — | Próximo seguimiento |
| 12 | `medico_seguimiento_id` | char(32) | char(32) | Sí | FK IX | — | Médico del seguimiento. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 13 | `lugar_seguimiento_id` | bigint | bigint | Sí | FK IX | — | Lugar / Centro del seguimiento. → `core_centrosalud`.`id` (ON DELETE SET_NULL) |
| 14 | `peso_kg` | decimal | numeric(5, 2) | Sí | — | — | Peso (kg) |
| 15 | `talla_cm` | decimal | numeric(5, 2) | Sí | — | — | Talla (cm) |
| 16 | `requiere_hospitalizacion` | bool | bool | No | — | False | Requiere hospitalización |
| 17 | `created_at` | datetime | datetime(6) | No | — | — | Creado el |
| 18 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `seguimiento_fecha_idx` | `fecha_seguimiento` | No |
| `seguimiento_hosp_idx` | `requiere_hospitalizacion` | No |
| `seguimiento_paciente_idx` | `paciente_id` | No |
| `seguimiento_seguimientopaciente_lugar_seguimiento_id_182872a4` | `lugar_seguimiento_id` | No |
| `seguimiento_seguimientopaciente_medico_id_afc4f45b` | `medico_id` | No |
| `seguimiento_seguimientopaciente_medico_seguimiento_id_5bcc9fc4` | `medico_seguimiento_id` | No |
| `seguimiento_seguimientopaciente_paciente_id_6af66a50` | `paciente_id` | No |


## Módulo `casos` — Casos clínicos


### 17. Tabla `casos_casoclinico`

**Entidad:** Caso clínico · **Modelo:** `casos.CasoClinico` · **Columnas:** 17

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `codigo_caso` | varchar(20) | varchar(20) | No | UQ | — | Código del caso. Generado automáticamente (ej. CASO-2026-0001) |
| 3 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 4 | `medico_responsable_id` | char(32) | char(32) | No | FK IX | — | Médico responsable. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 5 | `creado_por_id` | char(32) | char(32) | Sí | FK IX | — | Creado por. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 6 | `cribado_origen_id` | char(32) | char(32) | Sí | FK IX | — | Cribado de origen. → `cribado_cuestionariocribado`.`id` (ON DELETE SET_NULL) |
| 7 | `tipo_cancer` | varchar(20) | varchar(20) | No | IX | `OTRO` | Tipo de cáncer. Valores: LEUCEMIA, TUMORES_SNC, RETINOBLASTOMA, TUMOR_WILMS, NEUROBLASTOMA, LINFOMA, SARCOMA, OTRO |
| 8 | `estado` | varchar(20) | varchar(20) | No | IX | `ABIERTO` | Estado del caso. Valores: ABIERTO, EN_ESTUDIO, EN_TRATAMIENTO, EN_REMISION, CERRADO, ARCHIVADO |
| 9 | `prioridad` | varchar(10) | varchar(10) | No | IX | `MEDIA` | Prioridad. Valores: BAJA, MEDIA, ALTA, URGENTE |
| 10 | `titulo` | varchar(250) | varchar(250) | No | — | — | Título del caso. Descripción clínica breve que identifica el caso |
| 11 | `resumen_clinico` | TEXT | longtext | No | — | — | Resumen clínico. Descripción del cuadro clínico, síntomas principales y hallazgos relevantes |
| 12 | `protocolo_tratamiento` | TEXT | longtext | No | — | — | Protocolo de tratamiento. Protocolo oncológico asignado y descripción del plan terapéutico |
| 13 | `observaciones` | TEXT | longtext | No | — | — | Observaciones adicionales |
| 14 | `fecha_apertura` | date | date | No | — | — | Fecha de apertura |
| 15 | `fecha_cierre` | date | date | Sí | — | — | Fecha de cierre |
| 16 | `created_at` | datetime | datetime(6) | No | — | — | Registrado el |
| 17 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `caso_estado_idx` | `estado` | No |
| `caso_fecha_apertura_idx` | `fecha_apertura` | No |
| `caso_medico_idx` | `medico_responsable_id` | No |
| `caso_paciente_idx` | `paciente_id` | No |
| `caso_prioridad_idx` | `prioridad` | No |
| `caso_tipo_idx` | `tipo_cancer` | No |
| `casos_casoclinico_creado_por_id_781a69f7` | `creado_por_id` | No |
| `casos_casoclinico_cribado_origen_id_beb28b03` | `cribado_origen_id` | No |
| `casos_casoclinico_estado_8d460ccc` | `estado` | No |
| `casos_casoclinico_medico_responsable_id_6c98e32c` | `medico_responsable_id` | No |
| `casos_casoclinico_paciente_id_aaad2d37` | `paciente_id` | No |
| `casos_casoclinico_prioridad_95b21429` | `prioridad` | No |
| `casos_casoclinico_tipo_cancer_90655d8e` | `tipo_cancer` | No |


### 18. Tabla `casos_notacaso`

**Entidad:** Nota del caso · **Modelo:** `casos.NotaCaso` · **Columnas:** 9

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `caso_id` | char(32) | char(32) | No | FK IX | — | Caso clínico. → `casos_casoclinico`.`id` (ON DELETE CASCADE) |
| 3 | `autor_id` | char(32) | char(32) | No | FK IX | — | Autor. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `tipo` | varchar(20) | varchar(20) | No | IX | `EVOLUCION` | Tipo de nota. Valores: EVOLUCION, DIAGNOSTICO, TRATAMIENTO, INTERCONSULTA, LABORATORIO, IMAGEN, QUIRURGICO, ALTA, CIERRE, OBSERVACION |
| 5 | `titulo` | varchar(250) | varchar(250) | No | — | — | Título |
| 6 | `contenido` | TEXT | longtext | No | — | — | Contenido |
| 7 | `es_importante` | bool | bool | No | — | False | Marcar como importante |
| 8 | `created_at` | datetime | datetime(6) | No | — | — | Registrada el |
| 9 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizada el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `casos_notacaso_autor_id_e6901d78` | `autor_id` | No |
| `casos_notacaso_caso_id_393f6d73` | `caso_id` | No |
| `casos_notacaso_tipo_34d461fb` | `tipo` | No |
| `nota_caso_autor_idx` | `autor_id` | No |
| `nota_caso_idx` | `caso_id` | No |
| `nota_caso_tipo_idx` | `tipo` | No |


## Módulo `laboratorio` — Laboratorio


### 19. Tabla `laboratorio_catalogoestudio`

**Entidad:** Catálogo de estudio · **Modelo:** `laboratorio.CatalogoEstudio` · **Columnas:** 7

**Ordenamiento por defecto:** `categoria, nombre`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `nombre` | varchar(180) | varchar(180) | No | UQ | — | Nombre |
| 3 | `categoria` | varchar(120) | varchar(120) | No | IX | — | Categoria |
| 4 | `descripcion` | TEXT | longtext | No | — | — | Descripcion |
| 5 | `activo` | bool | bool | No | IX | True | Activo |
| 6 | `created_at` | datetime | datetime(6) | No | — | — | Created at |
| 7 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `laboratorio_catalogoestudio_activo_80522250` | `activo` | No |
| `laboratorio_catalogoestudio_categoria_31f16a0d` | `categoria` | No |


### 20. Tabla `laboratorio_catalogoparametro`

**Entidad:** Catálogo de parámetro · **Modelo:** `laboratorio.CatalogoParametro` · **Columnas:** 16

**Ordenamiento por defecto:** `estudio__nombre, orden, nombre`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `estudio_id` | char(32) | char(32) | No | FK IX | — | Estudio. → `laboratorio_catalogoestudio`.`id` (ON DELETE CASCADE) |
| 3 | `nombre` | varchar(180) | varchar(180) | No | — | — | Nombre |
| 4 | `unidad` | varchar(60) | varchar(60) | No | — | — | Unidad |
| 5 | `referencia_minima` | decimal | numeric(12, 4) | Sí | — | — | Referencia minima |
| 6 | `referencia_maxima` | decimal | numeric(12, 4) | Sí | — | — | Referencia maxima |
| 7 | `referencia_texto` | varchar(180) | varchar(180) | No | — | — | Referencia texto |
| 8 | `requiere_comentario` | bool | bool | No | — | False | Requiere comentario |
| 9 | `comentario_sugerido` | TEXT | longtext | No | — | — | Comentario sugerido |
| 10 | `alerta_sistema` | TEXT | longtext | No | — | — | Alerta sistema |
| 11 | `alerta_critica` | bool | bool | No | IX | False | Alerta critica |
| 12 | `tipo_valor` | varchar(20) | varchar(20) | No | IX | `numerico` | Tipo valor. Valores: numerico, texto, resultado, positivo_negativo |
| 13 | `activo` | bool | bool | No | IX | True | Activo |
| 14 | `orden` | smallint unsigned | smallint UNSIGNED | No | — | `0` | Orden |
| 15 | `created_at` | datetime | datetime(6) | No | — | — | Created at |
| 16 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `lab_cat_param_est_act_idx` | `estudio_id`, `activo` | No |
| `lab_cat_param_tipo_idx` | `tipo_valor` | No |
| `laboratorio_catalogoparametro_activo_1b53243b` | `activo` | No |
| `laboratorio_catalogoparametro_alerta_critica_f4b54285` | `alerta_critica` | No |
| `laboratorio_catalogoparametro_estudio_id_d75f9eab` | `estudio_id` | No |
| `laboratorio_catalogoparametro_tipo_valor_0bdd9711` | `tipo_valor` | No |


### 21. Tabla `laboratorio_resultadolaboratorio`

**Entidad:** Resultado de laboratorio · **Modelo:** `laboratorio.ResultadoLaboratorio` · **Columnas:** 15

**Ordenamiento por defecto:** `-fecha_muestra, -created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `solicitado_por_id` | char(32) | char(32) | Sí | FK IX | — | Solicitado por. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 4 | `revisado_por_id` | char(32) | char(32) | Sí | FK IX | — | Revisado por. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 5 | `tipo` | varchar(20) | varchar(20) | No | IX | — | Tipo. Valores: HEMOGRAMA, QUIMICA, COAGULACION, ORINA, CULTIVO, IMAGENOLOGIA, PATOLOGIA, MARCADORES, OTRO |
| 6 | `nombre_examen` | varchar(200) | varchar(200) | No | — | — | Nombre examen |
| 7 | `fecha_muestra` | date | date | No | IX | — | Fecha muestra |
| 8 | `fecha_resultado` | date | date | Sí | — | — | Fecha resultado |
| 9 | `estado` | varchar(20) | varchar(20) | No | IX | `RECIBIDO` | Estado. Valores: PENDIENTE, RECIBIDO, REVISADO, CRITICO |
| 10 | `resultado_narrativo` | TEXT | longtext | No | — | — | Resultado narrativo |
| 11 | `archivo` | varchar(100) | varchar(100) | Sí | — | — | Archivo |
| 12 | `observaciones` | TEXT | longtext | No | — | — | Observaciones |
| 13 | `hay_valores_criticos` | bool | bool | No | IX | False | Hay valores criticos |
| 14 | `created_at` | datetime | datetime(6) | No | — | — | Created at |
| 15 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `lab_pcte_fecha_idx` | `paciente_id`, `fecha_muestra` | No |
| `lab_pcte_tipo_idx` | `paciente_id`, `tipo` | No |
| `laboratorio_resultadolaboratorio_estado_7d4bf53c` | `estado` | No |
| `laboratorio_resultadolaboratorio_fecha_muestra_e473623c` | `fecha_muestra` | No |
| `laboratorio_resultadolaboratorio_hay_valores_criticos_c8bbd9a0` | `hay_valores_criticos` | No |
| `laboratorio_resultadolaboratorio_paciente_id_ed18588c` | `paciente_id` | No |
| `laboratorio_resultadolaboratorio_revisado_por_id_74b79858` | `revisado_por_id` | No |
| `laboratorio_resultadolaboratorio_solicitado_por_id_2f51803d` | `solicitado_por_id` | No |
| `laboratorio_resultadolaboratorio_tipo_a2e48a36` | `tipo` | No |


### 22. Tabla `laboratorio_valorresultado`

**Entidad:** Valor de resultado · **Modelo:** `laboratorio.ValorResultado` · **Columnas:** 13

**Ordenamiento por defecto:** `orden, parametro`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `resultado_id` | char(32) | char(32) | No | FK IX | — | Resultado. → `laboratorio_resultadolaboratorio`.`id` (ON DELETE CASCADE) |
| 3 | `parametro_catalogo_id` | char(32) | char(32) | Sí | FK IX | — | Parametro catalogo. → `laboratorio_catalogoparametro`.`id` (ON DELETE SET_NULL) |
| 4 | `parametro` | varchar(120) | varchar(120) | No | — | — | Parametro |
| 5 | `valor` | varchar(100) | varchar(100) | No | — | — | Valor |
| 6 | `valor_numerico` | decimal | numeric(12, 4) | Sí | — | — | Valor numerico |
| 7 | `unidad` | varchar(50) | varchar(50) | No | — | — | Unidad |
| 8 | `referencia_min` | decimal | numeric(12, 4) | Sí | — | — | Referencia min |
| 9 | `referencia_max` | decimal | numeric(12, 4) | Sí | — | — | Referencia max |
| 10 | `referencia_texto` | varchar(180) | varchar(180) | No | — | — | Referencia texto |
| 11 | `comentario` | TEXT | longtext | No | — | — | Comentario |
| 12 | `bandera` | varchar(15) | varchar(15) | No | IX | `SIN_RANGO` | Bandera. Valores: NORMAL, BAJO, ALTO, CRITICO_BAJO, CRITICO_ALTO, SIN_RANGO |
| 13 | `orden` | smallint unsigned | smallint UNSIGNED | No | — | `0` | Orden |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `laboratorio_valorresultado_bandera_266040f4` | `bandera` | No |
| `laboratorio_valorresultado_parametro_catalogo_id_bd3c513c` | `parametro_catalogo_id` | No |
| `laboratorio_valorresultado_resultado_id_6b2d8e04` | `resultado_id` | No |


## Módulo `psicosocial` — Psicosocial


### 23. Tabla `psicosocial_evaluacionpsicosocial`

**Entidad:** Evaluación psicosocial · **Modelo:** `psicosocial.EvaluacionPsicosocial` · **Columnas:** 32

**Ordenamiento por defecto:** `-fecha_evaluacion`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `evaluador_id` | char(32) | char(32) | Sí | FK IX | — | Evaluador. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 4 | `fecha_evaluacion` | datetime | datetime(6) | No | IX | `<function now at 0x7f9278493e20>` | Fecha evaluacion |
| 5 | `cuidador_principal_nombre` | varchar(150) | varchar(150) | No | — | — | Cuidador principal nombre |
| 6 | `parentesco_cuidador` | varchar(20) | varchar(20) | No | — | — | Parentesco cuidador. Valores: MADRE, PADRE, ABUELO_A, TIO_A, HERMANO_A, OTRO |
| 7 | `personas_en_hogar` | smallint unsigned | smallint UNSIGNED | No | — | `1` | Personas en hogar. Número total de personas que viven en el hogar |
| 8 | `tipo_vivienda` | varchar(20) | varchar(20) | No | — | — | Tipo vivienda. Valores: PROPIA, ALQUILADA, PRESTADA, OTRO |
| 9 | `ingreso_mensual` | varchar(20) | varchar(20) | No | — | `MEDIO` | Ingreso familiar mensual. Valores: NINGUNO, BAJO, MEDIO, SUFICIENTE |
| 10 | `tiene_seguro_medico` | bool | bool | No | — | True | Tiene seguro médico (SFS, ARS o SENASA) |
| 11 | `dificultad_medicamentos` | varchar(20) | varchar(20) | No | — | `NINGUNA` | Dificultad para costear medicamentos. Valores: NINGUNA, MODERADA, SEVERA |
| 12 | `dificultad_transporte` | varchar(20) | varchar(20) | No | — | `NINGUNA` | Dificultad para trasladarse al hospital. Valores: NINGUNA, MODERADA, SEVERA |
| 13 | `condicion_vivienda` | varchar(20) | varchar(20) | No | — | `ADECUADA` | Condición general de la vivienda. Valores: ADECUADA, REGULAR, PRECARIA |
| 14 | `hacinamiento` | bool | bool | No | — | False | Existe hacinamiento (más de 3 personas por habitación) |
| 15 | `servicios_basicos_ausentes` | bool | bool | No | — | False | Faltan servicios básicos (agua potable, luz, saneamiento) |
| 16 | `apoyo_familiar` | varchar(20) | varchar(20) | No | — | `BUENO` | Red de apoyo familiar. Valores: BUENO, REGULAR, LIMITADO, NINGUNO |
| 17 | `cuidador_es_unico` | bool | bool | No | — | False | El cuidador es el único responsable (sin red de relevo) |
| 18 | `estado_emocional_cuidador` | varchar(20) | varchar(20) | No | — | `ESTABLE` | Estado emocional del cuidador principal. Valores: ESTABLE, VULNERABLE, EN_CRISIS |
| 19 | `cuidador_perdio_trabajo` | bool | bool | No | — | False | El cuidador perdió o abandonó su empleo por el cuidado |
| 20 | `cuidador_requiere_apoyo_psicologico` | bool | bool | No | — | False | El cuidador requiere apoyo psicológico |
| 21 | `nino_en_edad_escolar` | bool | bool | No | — | True | El paciente está en edad escolar (3–18 años) |
| 22 | `abandono_escolar` | bool | bool | No | — | False | Ha abandonado o interrumpido la escuela por la enfermedad |
| 23 | `impacto_emocional_paciente` | varchar(20) | varchar(20) | No | — | `LEVE` | Impacto emocional observable en el paciente. Valores: LEVE, MODERADO, SEVERO |
| 24 | `puntaje_total` | smallint unsigned | smallint UNSIGNED | No | IX | `0` | Puntaje total |
| 25 | `nivel_riesgo` | varchar(10) | varchar(10) | No | IX | `BAJO` | Nivel riesgo. Valores: BAJO, MEDIO, ALTO, CRITICO |
| 26 | `necesidades_identificadas` | TEXT | longtext | No | — | — | Necesidades identificadas |
| 27 | `acciones_recomendadas` | TEXT | longtext | No | — | — | Acciones recomendadas |
| 28 | `observaciones` | TEXT | longtext | No | — | — | Observaciones |
| 29 | `requiere_seguimiento_social` | bool | bool | No | — | False | Requiere seguimiento social |
| 30 | `proxima_evaluacion` | date | date | Sí | — | — | Proxima evaluacion |
| 31 | `created_at` | datetime | datetime(6) | No | — | — | Created at |
| 32 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `psico_pcte_fecha_idx` | `paciente_id`, `fecha_evaluacion` | No |
| `psicosocial_evaluacionpsicosocial_evaluador_id_e9bf1a11` | `evaluador_id` | No |
| `psicosocial_evaluacionpsicosocial_fecha_evaluacion_b87f7f73` | `fecha_evaluacion` | No |
| `psicosocial_evaluacionpsicosocial_nivel_riesgo_bb8731b4` | `nivel_riesgo` | No |
| `psicosocial_evaluacionpsicosocial_paciente_id_16db8e1d` | `paciente_id` | No |
| `psicosocial_evaluacionpsicosocial_puntaje_total_b2ad325f` | `puntaje_total` | No |


## Módulo `alojamiento` — Casa FACCI


### 24. Tabla `alojamiento_entregahabitacion`

**Entidad:** Entrega de habitacion · **Modelo:** `alojamiento.EntregaHabitacion` · **Columnas:** 13

**Ordenamiento por defecto:** `-fecha_entrega, -fecha_creacion`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `estancia_id` | char(32) | char(32) | No | FK IX | — | Estancia. → `alojamiento_estanciafamiliar`.`id` (ON DELETE CASCADE) |
| 3 | `fecha_entrega` | date | date | No | — | Fecha/hora actual | Fecha de entrega |
| 4 | `hora_ingreso` | time | time(6) | Sí | — | — | Hora de ingreso |
| 5 | `hora_salida` | time | time(6) | Sí | — | — | Hora de salida |
| 6 | `entregado_por_facci` | varchar(150) | varchar(150) | No | — | `Encargado Administrativo FACCI` | Entregado por FACCI |
| 7 | `recibido_por_familiar` | varchar(150) | varchar(150) | No | — | — | Recibido por familiar responsable |
| 8 | `entregado_por_familiar` | varchar(150) | varchar(150) | No | — | — | Entregado por familiar responsable |
| 9 | `recibido_por_facci` | varchar(150) | varchar(150) | No | — | `Encargado Administrativo FACCI` | Recibido por FACCI |
| 10 | `observaciones` | TEXT | longtext | No | — | — | Observaciones generales |
| 11 | `creado_por_id` | char(32) | char(32) | Sí | FK IX | — | Creado por. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 12 | `fecha_creacion` | datetime | datetime(6) | No | — | — | Fecha creacion |
| 13 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `alojamiento_entregahabitacion_creado_por_id_eb941cd7` | `creado_por_id` | No |
| `alojamiento_entregahabitacion_estancia_id_3f61d01e` | `estancia_id` | No |


### 25. Tabla `alojamiento_estanciafamiliar`

**Entidad:** Estancia familiar · **Modelo:** `alojamiento.EstanciaFamiliar` · **Columnas:** 15

**Ordenamiento por defecto:** `-fecha_ingreso`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `habitacion_id` | char(32) | char(32) | No | FK IX | — | Habitación. → `alojamiento_habitacioncasa`.`id` (ON DELETE PROTECT) |
| 4 | `acompanante_nombre` | varchar(150) | varchar(150) | No | — | — | Nombre del acompañante |
| 5 | `acompanante_parentesco` | varchar(60) | varchar(60) | No | — | — | Parentesco |
| 6 | `acompanante_telefono` | varchar(20) | varchar(20) | No | — | — | Teléfono del acompañante |
| 7 | `motivo` | varchar(20) | varchar(20) | No | — | `CONSULTA` | Motivo de la estancia. Valores: QUIMIOTERAPIA, CIRUGIA, RADIOTERAPIA, HOSPITALIZACION, CONSULTA, OTRO |
| 8 | `fecha_ingreso` | date | date | No | — | — | Fecha de ingreso |
| 9 | `fecha_egreso_prevista` | date | date | Sí | — | — | Fecha de egreso prevista |
| 10 | `fecha_egreso_real` | date | date | Sí | — | — | Fecha de egreso real |
| 11 | `estado` | varchar(12) | varchar(12) | No | IX | `ACTIVA` | Estado. Valores: ACTIVA, COMPLETADA, CANCELADA |
| 12 | `observaciones` | TEXT | longtext | No | — | — | Observaciones |
| 13 | `registrado_por_id` | char(32) | char(32) | No | FK IX | — | Registrado por. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 14 | `created_at` | datetime | datetime(6) | No | — | — | Created at |
| 15 | `updated_at` | datetime | datetime(6) | No | — | — | Updated at |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `alojamiento_estanciafamiliar_estado_60bc124d` | `estado` | No |
| `alojamiento_estanciafamiliar_habitacion_id_7492c352` | `habitacion_id` | No |
| `alojamiento_estanciafamiliar_paciente_id_a2c87e92` | `paciente_id` | No |
| `alojamiento_estanciafamiliar_registrado_por_id_b124bcc2` | `registrado_por_id` | No |
| `estancia_estado_idx` | `estado` | No |
| `estancia_ingreso_idx` | `fecha_ingreso` | No |
| `estancia_pcte_idx` | `paciente_id` | No |


### 26. Tabla `alojamiento_habitacioncasa`

**Entidad:** Habitación · **Modelo:** `alojamiento.HabitacionCasa` · **Columnas:** 5

**Ordenamiento por defecto:** `nombre`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `nombre` | varchar(80) | varchar(80) | No | — | — | Nombre / Número |
| 3 | `capacidad` | smallint unsigned | smallint UNSIGNED | No | — | `2` | Capacidad (personas) |
| 4 | `descripcion` | varchar(200) | varchar(200) | No | — | — | Descripción. Planta baja, con baño privado, etc. |
| 5 | `activa` | bool | bool | No | — | True | Habilitada |


### 27. Tabla `alojamiento_itementregahabitacion`

**Entidad:** Item de entrega de habitacion · **Modelo:** `alojamiento.ItemEntregaHabitacion` · **Columnas:** 7

**Ordenamiento por defecto:** `orden, nombre_item`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `entrega_id` | char(32) | char(32) | No | FK IX | — | Entrega. → `alojamiento_entregahabitacion`.`id` (ON DELETE CASCADE) |
| 3 | `nombre_item` | varchar(80) | varchar(80) | No | — | — | Item |
| 4 | `entregado_por_facci` | bool | bool | No | — | False | Entregado por FACCI |
| 5 | `recibido_por_familiar` | bool | bool | No | — | False | Recibido del familiar |
| 6 | `observacion` | varchar(255) | varchar(255) | No | — | — | Observacion |
| 7 | `orden` | smallint unsigned | smallint UNSIGNED | No | — | `0` | Orden |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `alojamiento_itementregahabitacion_entrega_id_040a6a04` | `entrega_id` | No |


## Módulo `documentos` — Documentos


### 28. Tabla `documentos_documentomedico`

**Entidad:** Documento médico · **Modelo:** `documentos.DocumentoMedico` · **Columnas:** 11

**Ordenamiento por defecto:** `-fecha_documento`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `subido_por_id` | char(32) | char(32) | No | FK IX | — | Subido por. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `tipo_documento` | varchar(20) | varchar(20) | No | IX | — | Tipo de documento. Valores: HEMOGRAMA, ANALITICA, RADIOGRAFIA, SONOGRAFIA, RESONANCIA, TOMOGRAFIA, BIOPSIA, RECETA, INFORME_MEDICO, REFERIMIENTO, OTRO, LABORATORIO |
| 5 | `archivo` | varchar(100) | varchar(100) | No | — | — | Archivo. PDF, imagen o documento médico |
| 6 | `descripcion` | TEXT | longtext | No | — | — | Descripción. Descripción breve del contenido del documento |
| 7 | `fecha_documento` | date | date | No | — | — | Fecha del documento. Fecha en que fue emitido el documento |
| 8 | `estado` | varchar(20) | varchar(20) | No | IX | `PENDIENTE` | Estado. Valores: PENDIENTE, REVISADO, CORRECCION |
| 9 | `visible_padre` | bool | bool | No | IX | False | Visible para padre/tutor. Permite consultar este documento desde el Portal Padres. |
| 10 | `created_at` | datetime | datetime(6) | No | — | — | Subido el |
| 11 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `documento_fecha_idx` | `fecha_documento` | No |
| `documento_paciente_idx` | `paciente_id` | No |
| `documento_tipo_idx` | `tipo_documento` | No |
| `documentos_documentomedico_estado_ecc32d50` | `estado` | No |
| `documentos_documentomedico_paciente_id_384ae9b1` | `paciente_id` | No |
| `documentos_documentomedico_subido_por_id_efacd240` | `subido_por_id` | No |
| `documentos_documentomedico_tipo_documento_1a22dc18` | `tipo_documento` | No |
| `documentos_documentomedico_visible_padre_9147e22b` | `visible_padre` | No |


### 29. Tabla `documentos_solicituddocumento`

**Entidad:** Solicitud de documento · **Modelo:** `documentos.SolicitudDocumento` · **Columnas:** 9

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `medico_solicitante_id` | char(32) | char(32) | No | FK IX | — | Médico Solicitante. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 4 | `titulo` | varchar(150) | varchar(150) | No | — | — | Estudio Solicitado. Ej: Hemograma completo y plaquetas |
| 5 | `descripcion` | TEXT | longtext | No | — | — | Detalles / Indicaciones |
| 6 | `estado` | varchar(20) | varchar(20) | No | IX | `PENDIENTE` | Estado. Valores: PENDIENTE, SUBIDO, REVISADO, CORRECCION |
| 7 | `documento_asociado_id` | char(32) | char(32) | Sí | FK UQ | — | Documento Asociado. → `documentos_documentomedico`.`id` (ON DELETE SET_NULL) |
| 8 | `created_at` | datetime | datetime(6) | No | — | — | Solicitado el |
| 9 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `documentos_solicituddocumento_estado_55b539e6` | `estado` | No |
| `documentos_solicituddocumento_medico_solicitante_id_a4800f7e` | `medico_solicitante_id` | No |
| `documentos_solicituddocumento_paciente_id_28a53d13` | `paciente_id` | No |


## Módulo `reportes` — Reportes


### 30. Tabla `reportes_reportegenerado`

**Entidad:** Reporte generado · **Modelo:** `reportes.ReporteGenerado` · **Columnas:** 11

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `generado_por_id` | char(32) | char(32) | No | FK IX | — | Generado por. → `auth_app_customuser`.`id` (ON DELETE PROTECT) |
| 3 | `tipo_reporte` | varchar(30) | varchar(30) | No | IX | — | Tipo de reporte. Valores: RESUMEN_MENSUAL, POR_PROVINCIA, POR_DIAGNOSTICO, SEGUIMIENTO_CASOS, REFERENCIAS_MEDICAS, PACIENTES, REFERENCIAS, CRIBADO, SEGUIMIENTO, ESTADISTICAS |
| 4 | `nombre_reporte` | varchar(150) | varchar(150) | No | — | — | Nombre del reporte |
| 5 | `formato` | varchar(10) | varchar(10) | No | IX | `pdf` | Formato. Valores: pdf, xlsx, csv |
| 6 | `codigo_documento` | varchar(40) | varchar(40) | No | — | — | Codigo del documento |
| 7 | `total_registros` | integer unsigned | integer UNSIGNED | No | — | `0` | Total de registros |
| 8 | `fecha_inicio` | date | date | Sí | — | — | Período desde |
| 9 | `fecha_fin` | date | date | Sí | — | — | Período hasta |
| 10 | `archivo` | varchar(100) | varchar(100) | No | — | — | Archivo generado. PDF o Excel con los datos del reporte |
| 11 | `created_at` | datetime | datetime(6) | No | — | — | Generado el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `reporte_formato_idx` | `formato` | No |
| `reporte_tipo_idx` | `tipo_reporte` | No |
| `reporte_usuario_idx` | `generado_por_id` | No |
| `reportes_reportegenerado_formato_fa4977ca` | `formato` | No |
| `reportes_reportegenerado_generado_por_id_da6a05f0` | `generado_por_id` | No |
| `reportes_reportegenerado_tipo_reporte_352e18b2` | `tipo_reporte` | No |


## Módulo `notificaciones` — Notificaciones


### 31. Tabla `notificaciones_notificacion`

**Entidad:** Notificacion · **Modelo:** `notificaciones.Notificacion` · **Columnas:** 18

**Ordenamiento por defecto:** `-created_at`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `usuario_id` | char(32) | char(32) | No | FK IX | — | Usuario destinatario. → `auth_app_customuser`.`id` (ON DELETE CASCADE) |
| 3 | `tipo` | varchar(30) | varchar(30) | No | IX | `sistema` | Tipo. Valores: sistema, referencia, cita, seguimiento, alerta, alerta_clinica, mensaje, reporte, documento, paciente, cribado, medicamento, … |
| 4 | `modulo` | varchar(80) | varchar(80) | No | IX | — | Modulo relacionado |
| 5 | `prioridad` | varchar(10) | varchar(10) | No | IX | `media` | Prioridad. Valores: baja, media, alta, critica |
| 6 | `titulo` | varchar(180) | varchar(180) | No | — | — | Titulo |
| 7 | `mensaje` | TEXT | longtext | No | — | — | Mensaje |
| 8 | `leida` | bool | bool | No | IX | False | Leida |
| 9 | `fecha_lectura` | datetime | datetime(6) | Sí | — | — | Fecha de lectura |
| 10 | `accion_url` | varchar(255) | varchar(255) | Sí | — | — | URL de accion |
| 11 | `accion_texto` | varchar(100) | varchar(100) | Sí | — | — | Texto de accion |
| 12 | `content_type_id` | INTEGER | integer | Sí | FK IX | — | Tipo de objeto relacionado. → `django_content_type`.`id` (ON DELETE SET_NULL) |
| 13 | `objeto_id` | varchar(80) | varchar(80) | No | — | — | ID de objeto relacionado |
| 14 | `icono_nombre` | varchar(50) | varchar(50) | No | — | — | Icono visual |
| 15 | `clave_dedupe` | varchar(180) | varchar(180) | Sí | UQ | — | Clave de deduplicacion |
| 16 | `archivada` | bool | bool | No | IX | False | Archivada |
| 17 | `created_at` | datetime | datetime(6) | No | — | — | Creada el |
| 18 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizada el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `noti_prioridad_idx` | `prioridad` | No |
| `noti_tipo_idx` | `tipo` | No |
| `noti_user_arch_idx` | `usuario_id`, `archivada` | No |
| `noti_user_leida_idx` | `usuario_id`, `leida` | No |
| `notif_created_at_idx` | `created_at` | No |
| `notif_prioridad_idx` | `prioridad` | No |
| `notif_tipo_idx` | `tipo` | No |
| `notif_user_arch_idx` | `usuario_id`, `archivada` | No |
| `notif_user_leida_idx` | `usuario_id`, `leida` | No |
| `notif_usuario_idx` | `usuario_id` | No |
| `notificaciones_notificacion_archivada_4f634d20` | `archivada` | No |
| `notificaciones_notificacion_content_type_id_e45f05af` | `content_type_id` | No |
| `notificaciones_notificacion_leida_445591c8` | `leida` | No |
| `notificaciones_notificacion_modulo_52dcf562` | `modulo` | No |
| `notificaciones_notificacion_prioridad_26417c76` | `prioridad` | No |
| `notificaciones_notificacion_tipo_48e88b04` | `tipo` | No |
| `notificaciones_notificacion_usuario_id_4bc090a3` | `usuario_id` | No |


## Módulo `dashboard` — Alertas clínicas


### 32. Tabla `dashboard_alertaclinica`

**Entidad:** Alerta clinica · **Modelo:** `dashboard.AlertaClinica` · **Columnas:** 19

**Ordenamiento por defecto:** `estado, -prioridad, -fecha_creacion`


| # | Columna | Tipo (SQLite) | Tipo (MySQL) | Nulo | Clave | Predet. | Descripción |
|---|---|---|---|---|---|---|---|
| 1 | `id` | char(32) | char(32) | No | **PK** | UUID v4 | Id |
| 2 | `paciente_id` | char(32) | char(32) | No | FK IX | — | Paciente. → `pacientes_paciente`.`id` (ON DELETE CASCADE) |
| 3 | `cribado_id` | char(32) | char(32) | Sí | FK IX | — | Cribado relacionado. → `cribado_cuestionariocribado`.`id` (ON DELETE SET_NULL) |
| 4 | `referencia_id` | char(32) | char(32) | Sí | FK IX | — | Referencia relacionada. → `referencias_referenciamedica`.`id` (ON DELETE SET_NULL) |
| 5 | `seguimiento_id` | char(32) | char(32) | Sí | FK IX | — | Seguimiento relacionado. → `seguimiento_seguimientopaciente`.`id` (ON DELETE SET_NULL) |
| 6 | `documento_id` | char(32) | char(32) | Sí | FK IX | — | Documento relacionado. → `documentos_documentomedico`.`id` (ON DELETE SET_NULL) |
| 7 | `solicitud_documento_id` | char(32) | char(32) | Sí | FK IX | — | Solicitud de documento relacionada. → `documentos_solicituddocumento`.`id` (ON DELETE SET_NULL) |
| 8 | `tipo_alerta` | varchar(40) | varchar(40) | No | IX | — | Tipo de alerta. Valores: SINTOMAS_ALARMA, SOSPECHOSO_SIN_REFERENCIA, REFERENCIA_SIN_SEGUIMIENTO, SEGUIMIENTO_PENDIENTE, ALTA_PRIORIDAD_SIN_REVISION, DOCUMENTO_PENDIENTE, CASO_CRITICO |
| 9 | `prioridad` | varchar(10) | varchar(10) | No | IX | `MEDIA` | Nivel de prioridad. Valores: BAJA, MEDIA, ALTA, CRITICA |
| 10 | `titulo` | varchar(180) | varchar(180) | No | — | — | Titulo |
| 11 | `descripcion` | TEXT | longtext | No | — | — | Descripcion |
| 12 | `estado` | varchar(12) | varchar(12) | No | IX | `PENDIENTE` | Estado. Valores: PENDIENTE, REVISADA, RESUELTA, DESCARTADA |
| 13 | `fecha_creacion` | datetime | datetime(6) | No | IX | — | Fecha de creacion |
| 14 | `fecha_limite` | datetime | datetime(6) | Sí | IX | — | Fecha limite |
| 15 | `fecha_revision` | datetime | datetime(6) | Sí | — | — | Fecha de revision o cierre |
| 16 | `revisado_por_id` | char(32) | char(32) | Sí | FK IX | — | Usuario que reviso o resolvio. → `auth_app_customuser`.`id` (ON DELETE SET_NULL) |
| 17 | `comentario_cierre` | TEXT | longtext | No | — | — | Comentario u observacion de cierre |
| 18 | `clave_dedupe` | varchar(140) | varchar(140) | No | UQ | — | Clave de deduplicacion |
| 19 | `updated_at` | datetime | datetime(6) | No | — | — | Actualizada el |

**Índices**

| Nombre | Columnas | Único |
|---|---|---|
| `alerta_fecha_idx` | `fecha_creacion` | No |
| `alerta_limite_idx` | `fecha_limite` | No |
| `alerta_paciente_estado_idx` | `paciente_id`, `estado` | No |
| `alerta_prioridad_estado_idx` | `prioridad`, `estado` | No |
| `alerta_tipo_idx` | `tipo_alerta` | No |
| `dashboard_alertaclinica_cribado_id_ea2cf0a1` | `cribado_id` | No |
| `dashboard_alertaclinica_documento_id_85e51f69` | `documento_id` | No |
| `dashboard_alertaclinica_estado_9848aeb9` | `estado` | No |
| `dashboard_alertaclinica_fecha_creacion_70f65249` | `fecha_creacion` | No |
| `dashboard_alertaclinica_fecha_limite_ec7e7c41` | `fecha_limite` | No |
| `dashboard_alertaclinica_paciente_id_8a717be5` | `paciente_id` | No |
| `dashboard_alertaclinica_prioridad_47fe397a` | `prioridad` | No |
| `dashboard_alertaclinica_referencia_id_0e744f09` | `referencia_id` | No |
| `dashboard_alertaclinica_revisado_por_id_bfb4a076` | `revisado_por_id` | No |
| `dashboard_alertaclinica_seguimiento_id_df4afc4e` | `seguimiento_id` | No |
| `dashboard_alertaclinica_solicitud_documento_id_81717dc2` | `solicitud_documento_id` | No |
| `dashboard_alertaclinica_tipo_alerta_44e2f932` | `tipo_alerta` | No |



---

## Anexo A — Tablas del framework Django

Estas nueve tablas las gestiona el framework y **no deben modificarse manualmente**.

| Tabla | Función | Columnas |
|---|---|---|
| `django_migrations` | Registro de migraciones aplicadas | `id`, `app`, `name`, `applied` |
| `django_content_type` | Catálogo de tipos de modelo | `id`, `app_label`, `model` |
| `django_session` | Sesiones activas | `session_key`, `session_data`, `expire_date` |
| `django_admin_log` | Bitácora del panel Django Admin | `id`, `action_time`, `object_id`, `object_repr`, `action_flag`, `change_message`, `content_type_id`, `user_id` |
| `auth_permission` | Permisos del framework | `id`, `name`, `content_type_id`, `codename` |
| `auth_group` | Grupos de permisos | `id`, `name` |
| `auth_group_permissions` | Relación grupo ↔ permiso | `id`, `group_id`, `permission_id` |
| `auth_app_customuser_groups` | Relación usuario ↔ grupo | `id`, `customuser_id`, `group_id` |
| `auth_app_customuser_user_permissions` | Relación usuario ↔ permiso | `id`, `customuser_id`, `permission_id` |

> FACCI Care no basa su autorización en estos permisos y grupos: el control de acceso depende exclusivamente de la columna `rol` de `auth_app_customuser`.

---

## Anexo B — Columnas cifradas en reposo

| Tabla | Columna | Contenido protegido |
|---|---|---|
| `auth_app_customuser` | `telefono` | Teléfono de contacto del usuario |
| `pacientes_paciente` | `direccion` | Domicilio del menor |
| `pacientes_paciente` | `alergias` | Alergias conocidas |
| `pacientes_paciente` | `antecedentes_medicos` | Historial de enfermedades y condiciones previas |
| `padres_padretutor` | `direccion` | Domicilio de la familia |
| `padres_padretutor` | `contacto_emergencia` | Nombre del contacto de emergencia |
| `padres_padretutor` | `telefono_emergencia` | Teléfono de emergencia |

**Implicaciones operativas:**

1. Una consulta SQL directa devuelve el texto cifrado con prefijo `enc:`, no el valor legible.
2. Estas columnas no pueden usarse en cláusulas `WHERE`, `ORDER BY` ni en búsquedas parciales.
3. El descifrado requiere la clave `FACCI_ENCRYPTION_KEY`. **Sin esa clave, un respaldo de la base de datos no permite recuperar estos datos.**
4. Si la clave está vacía (configuración típica de desarrollo), los valores se almacenan en claro y el sistema opera igual.

---

## Anexo C — Columnas calculadas por el sistema

Estas columnas se almacenan pero **no las captura el usuario**: las calcula la aplicación al guardar el registro.

| Tabla | Columna | Regla |
|---|---|---|
| `cribado_cuestionariocribado` | `nivel_riesgo` | Alto si hay alarma mayor o puntaje ≥ 6; Moderado si ≥ 3; Bajo en otro caso |
| `cribado_cuestionariocribado` | `resultado` | Sospecha alta / moderada / sin sospecha, según el nivel |
| `cribado_cuestionariocribado` | `requiere_referencia` | Verdadero solo en nivel Alto |
| `psicosocial_evaluacionpsicosocial` | `puntaje_total` | Suma de los factores de vulnerabilidad |
| `psicosocial_evaluacionpsicosocial` | `nivel_riesgo` | Bajo / Moderado / Alto / Crítico según el puntaje |
| `laboratorio_valorresultado` | `bandera` | Comparación del valor contra el rango de referencia |
| `laboratorio_resultadolaboratorio` | `hay_valores_criticos` | Verdadero si algún valor tiene bandera crítica |
| `pacientes_paciente` | `codigo_paciente` | Serie `FACCI-{año}{consecutivo de 4 dígitos}` |
| `dashboard_alertaclinica` | `clave_dedupe` | Huella del hecho que origina la alerta |
| `notificaciones_notificacion` | `clave_dedupe` | Huella del hecho que origina la notificación |
| `core_logactividad` | `tipo_accion`, `modulo` | Inferidos del texto de la acción y del modelo afectado |
| `padres_recursoeducativo` | `slug` | Derivado del título, con sufijo si colisiona |

> Estas columnas **no deben editarse directamente en la base de datos**: al guardar el registro desde la aplicación, el valor se recalcula y sobrescribe cualquier modificación manual.

---

## Anexo D — Columnas de archivo

Las siguientes columnas almacenan rutas relativas dentro de `MEDIA_ROOT`, nunca el contenido del archivo.

| Tabla | Columna | Carpeta de destino |
|---|---|---|
| `auth_app_customuser` | `foto_perfil` | `perfiles/` |
| `pacientes_paciente` | `fotografia` | `pacientes/` |
| `documentos_documentomedico` | `archivo` | Documentos médicos |
| `laboratorio_resultadolaboratorio` | `archivo` | `laboratorio/AAAA/MM/` |
| `reportes_reportegenerado` | `archivo` | Reportes generados |
| `core_sistemaconfiguracion` | `logo` | `logo/` |
| `core_sistemaconfiguracion` | `logo_aplicacion` | `logo_app/` |
| `core_sistemaconfiguracion` | `logo_reportes` | `logo_reportes/` |

**Consecuencia para el respaldo:** una copia de la base de datos sin el directorio `MEDIA_ROOT` deja el expediente incompleto — las rutas existirán pero apuntarán a archivos ausentes. Ambos elementos deben respaldarse y restaurarse en conjunto.

---

## Anexo E — Consultas de verificación

```bash
# SQLite — listar tablas y ver la estructura de una tabla
sqlite3 db.sqlite3 ".tables"
sqlite3 db.sqlite3 ".schema pacientes_paciente"
sqlite3 db.sqlite3 "PRAGMA table_info(pacientes_paciente);"
sqlite3 db.sqlite3 "PRAGMA index_list(pacientes_paciente);"
sqlite3 db.sqlite3 "PRAGMA foreign_key_list(pacientes_paciente);"

# MySQL — equivalentes
mysql -u <usuario> -p -e "SHOW TABLES;" <base>
mysql -u <usuario> -p -e "SHOW CREATE TABLE pacientes_paciente\G" <base>
mysql -u <usuario> -p -e "SHOW INDEX FROM pacientes_paciente;" <base>

# Django — verificar que el esquema corresponde a los modelos
python manage.py makemigrations --check --dry-run   # debe responder "No changes detected"
python manage.py sqlmigrate pacientes 0001_initial  # SQL de una migración, sin ejecutarla
```

---

*Fin del documento — Diccionario Físico de la Base de Datos FACCI Care, versión 1.0.*
