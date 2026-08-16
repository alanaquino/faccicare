# Manual de Usuario — FACCI Care

**Instrucciones sobre el uso de las herramientas de administración del sitio web**
Fundación de Apoyo Contra el Cáncer Infantil (FACCI) — República Dominicana

| Campo | Detalle |
|---|---|
| **Sistema** | FACCI Care — Sistema de Detección Temprana de Cáncer Pediátrico |
| **Tipo de entregable** | Manual de usuario |
| **Versión del documento** | 1.0 |
| **Fecha de emisión** | Agosto 2026 |
| **Dirigido a** | Responsables de FACCI y personal usuario del sistema |
| **Medio de entrega** | Documento digital enviado por **correo electrónico** a los responsables de FACCI |
| **Documento complementario** | *Documentación del Proyecto — FACCI Care* |

> **Aviso de confidencialidad.** Este manual describe el acceso a un sistema que contiene datos clínicos de menores de edad. Su contenido es de uso interno de FACCI y del personal autorizado. No debe reenviarse a terceros ni publicarse en medios abiertos.

---

## Tabla de contenido

1. [Antes de empezar](#1-antes-de-empezar)
2. [Cómo entrar al sistema](#2-cómo-entrar-al-sistema)
3. [Cómo moverse por la pantalla](#3-cómo-moverse-por-la-pantalla)
4. [Qué puede hacer cada rol](#4-qué-puede-hacer-cada-rol)
5. [Administración de usuarios](#5-administración-de-usuarios)
6. [Administración de roles y permisos](#6-administración-de-roles-y-permisos)
7. [Ajustes del sistema (identidad institucional)](#7-ajustes-del-sistema-identidad-institucional)
8. [Administración de centros de salud](#8-administración-de-centros-de-salud)
9. [Panel de auditoría](#9-panel-de-auditoría)
10. [Administración de pacientes y tutores](#10-administración-de-pacientes-y-tutores)
11. [Administración de alertas clínicas](#11-administración-de-alertas-clínicas)
12. [Administración de documentos](#12-administración-de-documentos)
13. [Reportes y estadísticas](#13-reportes-y-estadísticas)
14. [Matrices operativas](#14-matrices-operativas)
15. [Administración de la Casa FACCI](#15-administración-de-la-casa-facci)
16. [Módulo psicosocial](#16-módulo-psicosocial)
17. [Módulos clínicos: cribado, referencias, seguimiento y laboratorio](#17-módulos-clínicos-cribado-referencias-seguimiento-y-laboratorio)
18. [Notificaciones](#18-notificaciones)
19. [Mi perfil y mi contraseña](#19-mi-perfil-y-mi-contraseña)
20. [Portal de padres y tutores](#20-portal-de-padres-y-tutores)
21. [Panel avanzado (Django Admin)](#21-panel-avanzado-django-admin)
22. [Solución de problemas frecuentes](#22-solución-de-problemas-frecuentes)
23. [Preguntas frecuentes](#23-preguntas-frecuentes)
24. [Buenas prácticas y recomendaciones de seguridad](#24-buenas-prácticas-y-recomendaciones-de-seguridad)
25. [Soporte y contacto](#25-soporte-y-contacto)
26. [Anexos](#26-anexos)

---

## 1. Antes de empezar

### 1.1 Qué es FACCI Care

FACCI Care es el sistema web de la fundación para acompañar el caso de un paciente pediátrico desde la primera sospecha hasta el cierre del seguimiento. Reúne en un solo lugar:

- El **expediente del paciente** y su historial completo.
- El **cribado** de detección temprana.
- Las **referencias médicas** y su retorno (contrarreferencias).
- El **seguimiento clínico** y las **indicaciones** para la familia.
- El módulo **psicosocial** y la **Casa FACCI**.
- Los **reportes estadísticos** y las **matrices operativas**.
- El **portal de padres**, donde la familia consulta y reporta.

### 1.2 Qué necesita para usarlo

| Requisito | Detalle |
|---|---|
| Equipo | Computadora, tableta o teléfono con conexión a internet |
| Navegador | Google Chrome, Microsoft Edge o Mozilla Firefox actualizados |
| Credenciales | Usuario y contraseña entregados por el administrador del sistema |
| Dirección del sitio | La que le indique el administrador (por ejemplo, `https://faccicare.org`) |

> El sistema es **responsivo**: se adapta a pantallas de computadora y de teléfono. El portal de padres, en particular, está pensado para usarse desde el celular.

### 1.3 Dos portales separados

FACCI Care tiene **dos puertas de entrada distintas** y no se cruzan:

| Portal | Quién entra | Dirección |
|---|---|---|
| **Portal clínico** | Todo el personal: administrador, médicos, pediatra, oncólogo, enfermería, trabajo social y coordinación | `/login/` |
| **Portal de padres** | Únicamente padres, madres y tutores | `/acceso/padres/` |

Si un usuario del personal intenta abrir una dirección del portal de padres, el sistema lo devuelve automáticamente a su inicio, y viceversa. Esto es intencional y protege la confidencialidad de los datos.

---

## 2. Cómo entrar al sistema

### 2.1 Ingreso del personal

1. Abra el navegador y escriba la dirección del sitio seguida de `/login/`.
2. En **Usuario**, escriba su nombre de usuario **o** su correo electrónico. Ambos funcionan.
3. En **Contraseña**, escriba su clave.
4. Pulse **Iniciar sesión**.
5. El sistema lo lleva directamente al tablero (*dashboard*) que corresponde a su rol.

**Mensajes que puede recibir:**

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| «Credenciales incorrectas. Verifica el usuario o correo y la contraseña.» | El usuario o la contraseña no coinciden | Revise mayúsculas, espacios en blanco y el bloqueo de mayúsculas |
| «La cuenta está deshabilitada. Contacte al administrador.» | Su usuario y contraseña son correctos, pero la cuenta fue desactivada | Solicite al administrador que reactive su cuenta |

### 2.2 Ingreso de padres y tutores

1. Abra la dirección del sitio seguida de `/acceso/padres/`.
2. En el primer campo escriba **el código del paciente** (por ejemplo, `FACCI-20260001`) **o** el correo electrónico registrado del tutor.
3. En **PIN**, escriba la clave numérica de 6 dígitos entregada por el personal de salud.
4. Pulse **Entrar**.

> Si el tutor tiene más de un hijo registrado, puede entrar con el código de cualquiera de ellos: accede a la misma cuenta.

### 2.3 Cerrar sesión

Pulse **Cerrar sesión** al final del menú lateral (personal) o en el menú del avatar (padres). El sistema lo devuelve a la pantalla de acceso correspondiente al portal por el que entró.

> **Importante.** Cierre sesión siempre que use un equipo compartido, especialmente en consultorios y estaciones de enfermería.

---

## 3. Cómo moverse por la pantalla

### 3.1 El menú lateral (personal)

El menú de la izquierda muestra **solamente los módulos a los que su rol tiene acceso**. Si no ve una sección, no es un error: su rol no la tiene habilitada.

El menú está agrupado así:

| Grupo | Opciones |
|---|---|
| **Principal** | Dashboard Clínico · Pacientes · Cribado FACCI |
| **Atención clínica** | Indicaciones Médicas · Referencias Médicas · Seguimiento Clínico · Laboratorio · Alertas Clínicas |
| **Apoyo FACCI** | Psicosocial · Casa FACCI |
| **Información** | Documentos · Reportes · Matrices Operativas |
| **Comunicación** | Notificaciones |
| **Configuración** | Centros de Salud · Usuarios · Auditoría · Ajustes · Admin Django |
| **Pie de menú** | Soporte · Cerrar Sesión |

Los perfiles con permiso de cribado ven además un botón destacado **+ Nuevo Cribado** en la parte superior del menú.

### 3.2 Elementos comunes de las pantallas

| Elemento | Para qué sirve |
|---|---|
| **Buscador (`q`)** | Filtra el listado por nombre, código, correo u otros campos relevantes |
| **Filtros desplegables** | Acotan por estado, tipo, rol, período o fecha |
| **Tarjetas de indicadores** | Muestran totales y conteos rápidos en la parte superior |
| **Paginación** | Aparece al pie de los listados largos |
| **Mensajes de confirmación** | Franja de color en la parte superior tras guardar, con el resultado de la acción |
| **Botones de exportación** | Descargan el contenido en PDF, Excel o CSV según el módulo |

### 3.3 En teléfono móvil

En pantallas pequeñas el menú lateral se contrae; se abre con el ícono de menú de la esquina. En el portal de padres, la navegación se hace desde la **barra inferior**: Inicio · Evolución · Recursos · Docs · Perfil.

---

## 4. Qué puede hacer cada rol

Esta tabla resume qué ve y qué puede modificar cada perfil. Es la referencia para responder «¿por qué a mí no me aparece esa opción?».

| Rol | Ve | Puede crear / modificar | No tiene acceso | Qué registros ve |
|---|---|---|---|---|
| **Administrador** | Todos los módulos | Todo, incluida la gestión de usuarios y la generación de reportes | **No puede crear cribados** | Todos |
| **Pediatra** | Pacientes, alertas, cribado, referencias, seguimiento, indicaciones, laboratorio, Casa FACCI (lectura), reportes | Cribados, referencias, indicaciones, documentos | Psicosocial, matrices, generación de reportes | Los que creó o tiene asignados |
| **Médico General** | Igual que Pediatra | Cribados, referencias, indicaciones, documentos | Igual que Pediatra | Los que creó o tiene asignados |
| **Oncólogo** | Pacientes, alertas, cribado (lectura), referencias, seguimiento, indicaciones, laboratorio, Casa FACCI (lectura), reportes | Referencias, indicaciones, documentos | Crear cribados, psicosocial, matrices, generación de reportes | Los que le fueron referidos |
| **Enfermera / Técnico** | Pacientes, alertas, cribado, referencias, seguimiento, indicaciones (lectura), laboratorio, reportes | Registros de laboratorio y documentos | Crear cribados, gestionar referencias/indicaciones, psicosocial, Casa FACCI, matrices | Los que creó o tiene asignados |
| **Trabajo Social / Psicología** | Pacientes (lectura), alertas, referencias y seguimiento (lectura), psicosocial, Casa FACCI, reportes | Evaluaciones psicosociales, Casa FACCI, documentos | Cribado, indicaciones, laboratorio, matrices, generación de reportes | Todos |
| **Coordinador FACCI** | Pacientes y referencias (lectura), psicosocial (lectura), Casa FACCI, reportes, matrices | Casa FACCI y **generación/exportación de reportes** | Alertas, cribado, seguimiento, indicaciones, laboratorio, subir documentos | Todos |
| **Padre / Tutor** | Su portal: estado, indicaciones, seguimiento, documentos compartidos, recursos | Reporte de síntomas y carga de documentos de su hijo/a | Cualquier módulo del personal | Solo su propio paciente |

> **Reglas que conviene recordar:**
> - **Solo el Médico General y el Pediatra crean cribados.** Ni siquiera el Administrador puede hacerlo.
> - **Solo el Administrador y el Coordinador FACCI generan y exportan reportes** y ven las matrices operativas.
> - **Solo el Administrador** gestiona usuarios, auditoría y ajustes del sistema.

---

## 5. Administración de usuarios

> **Rol requerido: Administrador.** Ruta del menú: **Configuración → Usuarios** (`/usuarios/`).

Esta pantalla administra **las cuentas del personal**. Las cuentas de padres y tutores **no** se gestionan aquí: se crean automáticamente al registrar un paciente y se administran desde el expediente del paciente (ver sección 10).

### 5.1 Consultar y buscar usuarios

1. Entre a **Usuarios**. Verá el total de cuentas, cuántas están activas y el conteo por rol.
2. Use el **buscador** para localizar por nombre, usuario, correo, teléfono, cédula, especialidad o centro médico.
3. Use el filtro **Rol** para ver únicamente un perfil.
4. Use el filtro **Estado** para ver solo cuentas activas o solo inactivas.

### 5.2 Crear un usuario nuevo

1. Pulse **Nuevo usuario**.
2. Complete el formulario:

| Campo | Obligatorio | Notas |
|---|---|---|
| Nombre de usuario | Sí | Debe ser único; es el que se escribe al iniciar sesión |
| Nombre | Sí | |
| Apellido | No | Recomendado para la identificación en listados y reportes |
| Correo electrónico | No | Si se indica, debe ser único; permite iniciar sesión con el correo |
| Rol | Sí | Determina todo lo que la persona podrá ver y hacer |
| Contraseña | Sí | **Mínimo 8 caracteres** |
| Cédula | No | Si se indica, debe ser única |
| Especialidad | No | Aparece en referencias y documentos |
| Centro médico | No | Se elige entre los centros de salud activos |

3. Pulse **Guardar**.
4. El sistema confirma con «Usuario … creado correctamente» y vuelve al listado.

**Errores que puede recibir y su causa:**

| Mensaje | Causa |
|---|---|
| «El usuario "…" ya existe.» | Ese nombre de usuario está tomado |
| «El correo electrónico ya está registrado.» | Otra cuenta usa ese correo |
| «La cédula … ya está registrada.» | Otra cuenta usa esa cédula |
| «La contraseña debe tener al menos 8 caracteres.» | Contraseña demasiado corta |
| «El nombre es requerido.» | Falta el nombre |

> **Recomendación.** Entregue la contraseña inicial por un canal privado y pida a la persona que la cambie desde **Mi perfil** en su primer ingreso.

### 5.3 Editar un usuario

1. En el listado, pulse **Editar** en la fila del usuario.
2. Puede modificar: nombre, apellido, nombre de usuario, correo, tipo de documento, cédula, teléfono, foto de perfil, rol, especialidad, centro médico y estado activo.
3. Para **cambiar la contraseña**, complete los campos de contraseña nueva y su confirmación. Déjelos vacíos si no desea cambiarla.
4. Para **quitar la foto**, marque la casilla correspondiente (no puede cargar y eliminar la foto en la misma operación).
5. Si el rol del usuario es **Padre / Tutor**, se muestra además el bloque de perfil familiar: parentesco, nacionalidad, dirección, provincia, municipio, ocupación, contacto y teléfono de emergencia, estado civil, cantidad de hijos e ingresos aproximados.
6. Pulse **Guardar cambios**.

**Protecciones automáticas del sistema:**

- Un administrador **no puede quitarse a sí mismo el rol de administrador**.
- Un administrador **no puede desactivar su propia cuenta**.
- Los cambios quedan registrados en la auditoría con el detalle de los campos modificados.

### 5.4 Activar o desactivar un usuario

1. En el listado, pulse **Activar** o **Desactivar** en la fila correspondiente.
2. El sistema confirma la operación.

> Desactivar es la forma correcta de dar de baja a una persona que deja la institución. **No elimine cuentas**: la eliminación rompería la trazabilidad de los actos clínicos que esa persona registró. Una cuenta desactivada conserva el historial y no puede iniciar sesión.

### 5.5 Reglas de negocio a tener presentes

- Una cuenta del personal **no puede vincularse como padre o tutor** de un paciente. Si al registrar un paciente se introduce la cédula o el correo de un miembro del personal, el sistema rechaza la operación.
- El rol es el único elemento que determina los permisos: cambiar el rol cambia inmediatamente el menú y el acceso de esa persona.

---

## 6. Administración de roles y permisos

> **Rol requerido: Administrador.** Ruta: **Usuarios → Roles** (`/usuarios/roles/`).

Esta pantalla es un **catálogo de consulta**: describe cada uno de los ocho roles del sistema, su propósito y la lista de permisos que otorga. Sirve para decidir qué rol asignar a una persona nueva.

| Rol | Descripción funcional |
|---|---|
| **Administrador** | Acceso total. Gestión de usuarios, configuración y todos los reportes |
| **Médico General (primer nivel)** | Médico de UNAP o clínica. Registra pacientes, realiza cribado y crea referimientos |
| **Pediatra (segundo nivel)** | Recibe referencias del primer nivel, evalúa y refiere al oncólogo si la sospecha se confirma |
| **Oncólogo Pediátrico (tercer nivel)** | Recibe referencias del pediatra. Diagnostica, confirma y gestiona el tratamiento |
| **Coordinador FACCI** | Coordinación administrativa y logística. Recursos, reportes al MSP y Casa FACCI |
| **Trabajo Social / Psicología** | Evaluaciones psicosociales, alojamiento en Casa FACCI y apoyo familiar |
| **Enfermera / Técnico de Salud** | Signos vitales, peso/talla y toma de muestras. Apoyo al seguimiento clínico |
| **Padre / Tutor** | Acceso exclusivo al portal de padres para seguir el estado de su hijo |

> **Los permisos no se editan desde la interfaz.** Están definidos en el sistema para garantizar la coherencia entre el menú, las pantallas y los datos que cada rol puede ver. Para cambiar lo que puede hacer una persona, **cambie su rol**. Si la institución necesita una combinación de permisos que no existe, debe solicitarse como cambio al equipo técnico.

---

## 7. Ajustes del sistema (identidad institucional)

> **Rol requerido: Administrador.** Ruta: **Configuración → Ajustes** (`/ajustes/`).

Desde aquí se controla cómo se identifica el sistema en pantalla y en los documentos que genera.

### 7.1 Cambiar los nombres

1. Entre a **Ajustes**.
2. Edite **Nombre de la aplicación** (el que se muestra en la interfaz; por defecto «FACCI Care»).
3. Edite **Nombre de la institución** (el que aparece en documentos y reportes; por defecto «Fundación de Apoyo Contra el Cáncer Infantil (FACCI)»).
4. Pulse **Guardar**. Recibirá el mensaje «Configuración del sistema guardada correctamente».

### 7.2 Cambiar los logotipos

El sistema maneja **dos logotipos distintos**:

| Logotipo | Dónde aparece |
|---|---|
| **Logo de la aplicación** | Encabezado y menú de la interfaz web |
| **Logo oficial para reportes** | Documentos PDF: referencias, fichas, actas y reportes |

Para cambiarlos:

1. Pulse el selector de archivo del logotipo que desea reemplazar.
2. Elija la imagen (formato PNG recomendado, con fondo transparente).
3. Pulse **Guardar**.

Para volver al logotipo por defecto, pulse **Eliminar** en el logotipo correspondiente. El sistema confirma con «… eliminado. Se restauró el logo por defecto».

> **Recomendación.** Use una imagen de buena resolución para el logo de reportes: es el que se imprime y se entrega a instituciones externas.

### 7.3 Información del sistema

La pantalla **Usuarios → Configuración** (`/usuarios/config/`) muestra los datos informativos de la instalación: nombre y versión del sistema, país, idioma, zona horaria (`America/Santo_Domingo`, UTC-4) y el estado de las notificaciones y de los respaldos. Es una pantalla **de consulta**; los respaldos se administran a nivel de servidor, no desde la interfaz.

---

## 8. Administración de centros de salud

> **Consulta: todo el personal. Creación y edición: solo Administrador.** Ruta: **Configuración → Centros de Salud** (`/centros-salud/`).

Los centros de salud alimentan varias partes del sistema: el centro donde labora cada usuario, el hospital destino de las referencias, el lugar del seguimiento y la distribución geográfica de los reportes y las matrices.

### 8.1 Consultar centros

1. Entre a **Centros de Salud**. Verá el listado y el mapa con los centros que tienen coordenadas registradas.
2. Use el buscador para filtrar por nombre, provincia, municipio, dirección, teléfono o correo.
3. El contador **sin coordenadas** indica cuántos centros faltan por ubicar en el mapa.
4. Pulse sobre un centro para ver su ficha: tipo, ubicación, contacto, camas disponibles frente al total, porcentaje de disponibilidad, especialidades y personal entrenado por FACCI.

### 8.2 Registrar un centro

1. En la pantalla de centros, abra el formulario **Nuevo centro**.
2. Complete al menos el **Nombre** (es el único campo obligatorio para guardar).
3. Indique **Tipo**, **Provincia**, **Municipio**, **Dirección**, **Teléfono**, **Correo** y si está **Activo**.
4. Si dispone de ellas, escriba **Latitud** y **Longitud** para ubicarlo en el mapa. Se acepta coma o punto decimal.
5. Pulse **Guardar**.

**Tipos de centro disponibles:**

| Tipo | Significado |
|---|---|
| Nivel 3 (Especializado) | Hospital de alta complejidad |
| Nivel 2 (General) | Clínica u hospital general |
| Unidad de Atención Primaria | UNAP |
| Centro Diagnóstico | Laboratorio o imágenes |
| Otro | Cualquier otra modalidad |

### 8.3 Editar la ficha completa de un centro

1. Entre a la ficha del centro y pulse **Editar**.
2. Además de los datos generales, aquí se administran:

| Bloque | Campos |
|---|---|
| **Capacidad** | Camas oncológicas disponibles, camas totales y **Estado de derivación** (Disponible / Capacidad limitada / No disponible / En mantenimiento) |
| **Especialidades** | Oncología pediátrica · Pediatría general · Imágenes diagnósticas · Laboratorio clínico avanzado |
| **Personal** | Médicos titulares en turno · Entrenados FACCI |
| **Ubicación** | Latitud y longitud |

3. Pulse **Guardar**. El sistema confirma con «Centro "…" actualizado correctamente».

> El sistema intenta **geolocalizar automáticamente** el centro cuando cambia su dirección y no tiene coordenadas. Si el servicio externo no responde, el centro se guarda igual y puede ubicarse manualmente más adelante.

---

## 9. Panel de auditoría

> **Rol requerido: Administrador.** Ruta: **Configuración → Auditoría** (`/auditoria/`).

La auditoría responde a la pregunta **«quién hizo qué, cuándo y desde dónde»**. Es la herramienta principal de control interno del sistema.

### 9.1 Indicadores

En la parte superior verá: total de usuarios, usuarios activos, acciones registradas hoy, reportes generados y accesos de los últimos 7 días.

### 9.2 Bloques de información

| Bloque | Contenido |
|---|---|
| **Usuarios** | Listado con número de acciones registradas y fecha del último acceso |
| **Actividad reciente** | Últimas acciones del sistema con usuario, tipo, módulo, objeto afectado, descripción, IP y fecha |
| **Reportes generados** | Historial de reportes con su autor y fecha |

### 9.3 Filtrar la actividad

Combine los filtros disponibles:

| Filtro | Uso |
|---|---|
| **Usuario** | Nombre, usuario o correo (búsqueda parcial) |
| **Rol** | Perfil del usuario |
| **Estado** | Cuentas activas o inactivas |
| **Último acceso** | Con acceso · Sin acceso · Últimos 7 días |
| **Módulo** | Pacientes, Cribado, Referencias, Seguimiento, Alertas, Documentos, Reportes, Usuarios… |
| **Tipo de acción** | Creación · Edición · Eliminación · Consulta · Inicio de sesión · Cierre de sesión · Generación de reporte |
| **Fecha desde / hasta** | Rango de fechas |

### 9.4 Usos habituales

| Necesidad | Cómo resolverla |
|---|---|
| Saber quién modificó un expediente | Filtre por módulo **Pacientes** y por el rango de fechas |
| Verificar quién generó un reporte enviado al MSP | Revise el bloque **Reportes generados** |
| Detectar cuentas sin uso | Filtre **Último acceso → Sin acceso** |
| Confirmar el cambio de rol de un usuario | Filtre por módulo **Usuarios** y tipo **Edición**; la descripción indica los campos modificados |

---

## 10. Administración de pacientes y tutores

> Ruta: **Principal → Pacientes** (`/pacientes/`). El listado muestra únicamente los pacientes dentro de su alcance de datos.

### 10.1 Buscar un paciente

Use el buscador (nombre, apellido, código, provincia, municipio, tutor o médico asignado) y el filtro por **Estado**.

### 10.2 Registrar un paciente nuevo

> Pueden registrar: Administrador, Médico General, Pediatra, Enfermería, Trabajo Social y Coordinación. **No pueden**: Oncólogo ni Padre/Tutor.

1. Pulse **Nuevo paciente**.
2. **Datos del paciente:** nombre, apellido, fecha de nacimiento (no puede ser futura), sexo, provincia, municipio, dirección, tipo de sangre, alergias, antecedentes médicos, peso, altura, escuela, seguro médico y número de seguro.
3. **Datos del tutor:** nombre completo, tipo y número de documento, teléfono, correo, dirección y parentesco.
4. **Médico asignado** (opcional): se elige entre médicos, pediatras, oncólogos y coordinación.
5. Pulse **Registrar**.

**Qué hace el sistema automáticamente:**

- Genera el **código del paciente** con el formato `FACCI-AAAA0001`.
- Si el tutor **no existe**, crea su cuenta de acceso y genera un **PIN de 6 dígitos** que se muestra **una sola vez** en pantalla.
- Si el tutor **ya existe** (por cédula o correo), lo reutiliza y actualiza sus datos, conservando su PIN actual.
- Valida la cédula dominicana (11 dígitos) y la normaliza al formato `000-0000000-0`.

> **Anote el PIN antes de cerrar el mensaje.** Es el único momento en que se muestra. Si se pierde, puede regenerarse (sección 10.5).

### 10.3 El expediente del paciente

Al abrir un paciente accede a su expediente, que reúne en una **línea de tiempo** todo lo ocurrido: cribados, referencias, seguimientos, documentos, notas clínicas, síntomas reportados por la familia, indicaciones y solicitudes de documentos.

Desde el expediente puede, según su rol: registrar notas clínicas, iniciar un cribado, crear una referencia, registrar un seguimiento, subir documentos y consultar los datos del tutor.

### 10.4 Editar un paciente

| Rol | Puede editar |
|---|---|
| Administrador | Cualquier paciente |
| Médico General / Pediatra | Los que creó o tiene asignados |
| Oncólogo | Los que le fueron referidos |
| Otros roles | No pueden editar |

### 10.5 Regenerar el PIN del tutor

> Autorizado para el Administrador, el médico asignado y quien registró al paciente.

1. Abra el paciente y entre a **Editar**.
2. Pulse **Resetear PIN de acceso**.
3. El sistema genera un PIN nuevo de 6 dígitos y lo muestra en pantalla **una sola vez**.
4. Entréguelo al tutor por un canal privado.

La acción queda registrada en la auditoría con el nombre del tutor y del paciente afectados.

### 10.6 Ficha imprimible

Desde el expediente puede generar la **ficha del paciente en PDF** para adjuntarla al expediente físico o entregarla en otro centro.

---

## 11. Administración de alertas clínicas

> Ruta: **Atención clínica → Alertas Clínicas** (`/alertas/`). Accesible para todo el personal **excepto** el Coordinador FACCI.

Las alertas las genera el sistema cuando detecta situaciones que requieren atención.

### 11.1 Tipos de alerta

| Tipo | Se genera cuando… |
|---|---|
| Síntomas de alarma | La familia reporta síntomas relevantes desde su portal |
| Sospechoso sin referencia | Un caso con sospecha no ha sido referido |
| Referencia sin seguimiento | Una referencia no registra avance |
| Seguimiento pendiente o vencido | La próxima cita de seguimiento venció |
| Alta prioridad sin revisión | Un caso prioritario no ha sido atendido |
| Documento clínico pendiente | Falta un documento solicitado |
| Caso crítico | Situación clínica que requiere intervención inmediata |

Cada alerta tiene **prioridad** (Baja, Media, Alta, Crítica) y **fecha límite**.

### 11.2 Gestionar una alerta

Estados posibles: **Pendiente → Revisada → Resuelta**, o bien **Descartada**.

1. Entre a **Alertas Clínicas** y localice la alerta.
2. Pulse la acción correspondiente:
   - **Revisar** — deja constancia de que fue vista y está en tratamiento.
   - **Resolver** — la situación fue atendida. Escriba el comentario de cierre.
   - **Descartar** — la alerta no procede. Escriba el motivo.
3. El sistema registra quién la cerró, cuándo y con qué comentario.

> El sistema **deduplica** las alertas: un mismo hecho no genera avisos repetidos.

---

## 12. Administración de documentos

> Ruta: **Información → Documentos** (`/documentos/`). Consulta para todo el personal; la carga está reservada a los roles con permiso de subir documentos (todos excepto el Coordinador FACCI).

### 12.1 Consultar y filtrar

Filtre por tipo de documento, estado, texto libre (paciente o descripción) y rango de fechas.

### 12.2 Subir un documento

1. Pulse **Subir documento**.
2. Seleccione el **paciente** (la lista se limita a los de su alcance).
3. Elija el **tipo**: Hemograma, Analítica, Radiografía, Sonografía, Resonancia, Tomografía, Biopsia, Receta médica, Informe médico, Referimiento, Laboratorio u Otro.
4. Indique la **fecha del documento** y una **descripción**.
5. Adjunte el archivo y pulse **Guardar**.

### 12.3 Acciones sobre un documento

| Acción | Efecto |
|---|---|
| **Ver / Previsualizar** | Abre el documento dentro del sitio, sin descargarlo |
| **Descargar** | Guarda el archivo en su equipo |
| **Cambiar estado** | Pendiente · Revisado · Requiere corrección |
| **Cambiar visibilidad** | Activa o desactiva que la familia lo vea en su portal |
| **Eliminar** | Retira el documento del expediente |

> **La visibilidad hacia la familia es una decisión explícita.** Ningún documento aparece en el portal de padres si no se marca como visible.

### 12.4 Solicitudes de documentos

En **Documentos → Solicitudes** (`/documentos/solicitudes/`) se administran los documentos que el equipo pide a la familia. La solicitud aparece en el portal de padres; cuando el tutor carga el archivo, este queda enlazado a la solicitud y su estado se actualiza.

---

## 13. Reportes y estadísticas

> **Consulta: todo el personal. Generación, exportación y envío: solo Administrador y Coordinador FACCI.** Ruta: **Información → Reportes** (`/reportes/`).

### 13.1 Dashboard de reportes

Muestra los indicadores consolidados: pacientes por estado, distribución por provincia, tipos de cáncer y tendencia mensual.

### 13.2 Generar un reporte

1. Entre a **Reportes → Generar** (`/reportes/generar/`).
2. Elija el **tipo de reporte**:

| Tipo | Contenido |
|---|---|
| Resumen mensual | Estadísticas generales del período seleccionado |
| Por provincia | Distribución geográfica de pacientes, centros y referencias |
| Por diagnóstico | Frecuencia y porcentaje por diagnóstico |
| Seguimiento de casos | Estado actual, fase, responsable y alertas pendientes |
| Referencias médicas | Historial de referencias emitidas y recibidas |

3. Elija el **período**: Último mes · Últimos 3 meses · Últimos 6 meses · Último año · Rango personalizado (con fechas de inicio y fin).
4. Aplique **filtros opcionales** por provincia y por médico.
5. Elija el **formato**: **PDF**, **Excel (.xlsx)** o **CSV**.
6. Elija la acción:
   - **Vista previa** — muestra el reporte en pantalla en versión imprimible.
   - **Generar y descargar** — descarga el archivo.
   - **Enviar por correo** — ver 13.3.

Cada reporte generado queda guardado con su **código de documento**, el total de registros, el rango de fechas y el usuario que lo produjo, y aparece en **Reportes recientes** y en el panel de auditoría.

### 13.3 Enviar un reporte por correo electrónico

1. Complete los parámetros del reporte como en el punto anterior.
2. Escriba el **correo destino** (obligatorio), el **asunto** y, si desea, un **mensaje**.
3. Pulse **Enviar por correo**.
4. El sistema genera el archivo, lo adjunta y lo envía. Confirmará con «Reporte enviado correctamente a …».

> Si el servidor de correo no está configurado o falla, verá el mensaje «No se pudo enviar el correo: …». El reporte **igualmente queda generado y guardado**, de modo que puede descargarlo y enviarlo manualmente.

### 13.4 Reporte PENCI-RD

En **Reportes → PENCI** (`/reportes/penci/`) se consulta el reporte institucional con:

- Codificación **ICD-O3** por tipo de cáncer (por ejemplo, Leucemia C91–C95, Tumores del SNC C70–C72, Retinoblastoma C69.2, Tumor de Wilms C64, Neuroblastoma C74).
- Agrupación por rangos etarios: 0–4, 5–9, 10–14 y ≥15 años.
- Filtro por rango de fechas.

Todo el personal puede consultarlo; la exportación queda reservada al Administrador y al Coordinador FACCI.

---

## 14. Matrices operativas

> **Rol requerido: Administrador o Coordinador FACCI.** Ruta: **Información → Matrices Operativas** (`/matrices/`).

Las matrices son el tablero de coordinación institucional. Presentan cuatro vistas: **riesgo clínico**, **referencias médicas**, **seguimiento clínico** y **alertas clínicas**.

### 14.1 Uso

1. Seleccione el **período** de análisis (7, 30, 90 o 365 días).
2. Consulte los indicadores del período: total de cribados, total de referencias, tiempo medio de respuesta y tasa de éxito.
3. Revise la tabla por **centro de salud** (cribados y referencias de cada uno) y la distribución por **provincia**.
4. Revise las **alertas operativas** y el total de alertas abiertas.

### 14.2 Exportar

| Acción | Resultado |
|---|---|
| **Vista previa** (`/matrices/vista-previa/`) | Versión imprimible en pantalla |
| **Descargar PDF** (`/matrices/descargar-pdf/`) | Documento PDF con el logo institucional |
| **Exportar CSV** | Archivo con centro, provincia, tipo, estado, cribados y referencias del período |

---

## 15. Administración de la Casa FACCI

> **Gestión: Trabajo Social, Coordinador FACCI y Administrador. Consulta: también médicos, pediatras y oncólogos.** Ruta: **Apoyo FACCI → Casa FACCI** (`/alojamiento/`).

### 15.1 Administrar habitaciones

Ruta: `/alojamiento/habitaciones/`.

1. **Crear una habitación:** indique nombre o número, capacidad y descripción; pulse **Guardar**.
2. **Habilitar o deshabilitar:** pulse el interruptor de la habitación. Una habitación deshabilitada no puede asignarse a nuevas estancias, pero conserva su historial.
3. **Eliminar:** solo es posible si la habitación **no tiene estancias asociadas**. En caso contrario, deshabilítela.

### 15.2 Registrar una estancia familiar

1. Pulse **Nueva estancia** (o entre desde el paciente, con `/alojamiento/nuevo/<paciente>/`).
2. Seleccione el **paciente** y la **habitación**.
3. Registre al **acompañante**: nombre, parentesco y teléfono.
4. Indique el **motivo**: ciclo de quimioterapia, intervención quirúrgica, radioterapia, hospitalización prolongada, consulta/exámenes u otro.
5. Registre la **fecha de ingreso** y la **fecha de egreso prevista**.
6. Añada observaciones si corresponde y pulse **Guardar**.

La estancia queda en estado **Activa**.

### 15.3 Acta de entrega de habitación

1. Abra la estancia y pulse **Entrega de habitación**.
2. Complete fecha de entrega, hora de ingreso y hora de salida.
3. Registre quién **entrega por FACCI** y quién **recibe por la familia** (y, al egreso, quién entrega por la familia y quién recibe por FACCI).
4. Marque el **inventario** ítem por ítem, indicando lo entregado, lo recibido y las observaciones.
5. Guarde y, si lo necesita, use **Imprimir** o **Descargar PDF** para la copia firmada.

### 15.4 Cierre de la estancia (*check-out*)

1. Abra la estancia y pulse **Check-out**.
2. Registre la **fecha de egreso real**.
3. La estancia pasa a estado **Completada** y la habitación queda liberada.

### 15.5 Reporte de estancias

En `/alojamiento/reportes/estancias/` puede consultar el reporte de ocupación y descargarlo en PDF para la memoria institucional.

---

## 16. Módulo psicosocial

> **Consulta: Coordinador FACCI, Trabajo Social y Administrador. Edición: Trabajo Social y Administrador.** Ruta: **Apoyo FACCI → Psicosocial** (`/psicosocial/`).

### 16.1 Registrar una evaluación

1. Pulse **Nueva evaluación** (o entre desde el paciente).
2. Complete los bloques del formulario:

| Bloque | Información |
|---|---|
| **Cuidador y hogar** | Nombre del cuidador principal, parentesco y número de personas en el hogar |
| **Situación económica** | Tipo de vivienda, ingreso mensual, seguro médico, dificultad para medicamentos y para transporte |
| **Condiciones habitacionales** | Condición de la vivienda, hacinamiento y ausencia de servicios básicos |
| **Red de apoyo** | Apoyo familiar y si el cuidador es único |
| **Estado emocional del cuidador** | Estable / Vulnerable / En crisis, pérdida de trabajo y necesidad de apoyo psicológico |
| **Situación del niño** | Edad escolar, abandono escolar e impacto emocional |
| **Conclusión** | Necesidades identificadas, acciones recomendadas, observaciones, si requiere seguimiento social y fecha de la próxima evaluación |

3. Pulse **Guardar**.

El sistema calcula automáticamente el **puntaje** y el **nivel de riesgo psicosocial**: Bajo, Moderado, Alto o Crítico.

---

## 17. Módulos clínicos: cribado, referencias, seguimiento y laboratorio

Esta sección resume las herramientas clínicas. El detalle de los criterios médicos corresponde al personal de salud; aquí se describe la operación en el sistema.

### 17.1 Cribado

> **Crear: solo Médico General y Pediatra.** Consulta: Oncólogo, Enfermería y Administrador. Ruta: `/cribado/`.

1. Pulse **+ Nuevo Cribado**.
2. Seleccione el paciente.
3. Responda el cuestionario, organizado en secciones: síntomas generales, signos hematológicos, signos neurológicos y masas, y signos oculares.
4. Indique el tipo de cáncer sospechado y las observaciones clínicas.
5. Pulse **Guardar**.

El sistema clasifica el caso automáticamente:

| Situación | Nivel de riesgo | Resultado | ¿Habilita referencia? |
|---|---|---|---|
| Alguna **alarma mayor** (dolor de cabeza persistente, vómitos matutinos, masa abdominal palpable o leucocoria) **o** 6 o más síntomas | **Alerta roja — riesgo alto** | Sospecha alta | **Sí** |
| 3 a 5 síntomas, sin alarma mayor | Riesgo moderado | Sospecha moderada | No |
| Menos de 3 síntomas | Riesgo bajo | Sin sospecha | No |

Desde la pantalla de resultado, si el caso requiere referencia, puede crearla directamente. El listado de cribados puede exportarse a CSV.

### 17.2 Referencias médicas

> **Gestión: médicos clínicos y Administrador.** Consulta: Enfermería, Trabajo Social y Coordinación. Ruta: `/referencias/`.

**Crear una referencia:** seleccione paciente, especialista destino, hospital destino, motivo, prioridad (Baja, Media, Alta, Urgente) y fecha de cita si ya está agendada. El paciente pasa a estado **Referido** y la referencia recibe un código `REF-AAAA-XXXX`.

**Ciclo de la referencia (lo ejecuta el especialista destino):**

```
Pendiente → Aceptada → En proceso → Completada
    ↘ Rechazada / Cancelada
```

El médico referente puede **cancelar** su propia referencia mientras esté Pendiente o Aceptada.

**Otras acciones disponibles:**

| Acción | Descripción |
|---|---|
| **Imprimir** | Genera el formulario de referencia para su entrega física |
| **Guardar documento MSP** | Adjunta el formulario oficial a la referencia |
| **Historial del paciente** | Muestra todas las referencias de ese paciente |
| **Contrarreferir** | El especialista devuelve el resultado de la atención |
| **Ingreso a Casa FACCI** | Genera la solicitud de alojamiento vinculada a la referencia, con formulario imprimible |

**Contrarreferencia:** el especialista registra fecha de atención, diagnóstico establecido, tipo de cáncer confirmado, estadio (I–IV o No estadificado), tratamiento realizado, estudios, medicamentos indicados, resultado de la atención, recomendaciones al médico referente, si requiere seguimiento en FACCI y la fecha de la próxima cita.

### 17.3 Seguimiento clínico e indicaciones

> Ruta: `/seguimiento/` e `/indicaciones/`.

**Registrar un seguimiento:** seleccione el paciente, la fase del protocolo (Inducción, Consolidación, Mantenimiento o Vigilancia), el estado clínico, los síntomas actuales, el tratamiento en curso, los medicamentos, peso y talla (el sistema calcula el IMC), el lugar y el médico del seguimiento, la próxima fecha y si requiere hospitalización.

**Administrar indicaciones:** desde **Indicaciones Médicas** se registran las pautas para la familia. Cada indicación tiene:

| Campo | Opciones |
|---|---|
| Tipo | Medicación · Protocolo activo · Pauta médica específica · Hidratación · Descanso · Alimentación · Higiene · Otra |
| Prioridad | Alta · Media · Baja |
| Activa | Si está desactivada, deja de mostrarse |
| **Visible para padre/tutor** | Controla si aparece en el portal de la familia |

Desde el paciente puede generarse el **descargo de tratamiento**, en pantalla y en PDF, para entregar a la familia.

### 17.4 Laboratorio

> **Consulta y registro: equipo asistencial (clínicos, enfermería y Administrador).** Ruta: `/laboratorio/`.

1. **Registrar un resultado:** seleccione paciente, tipo de examen (hemograma, química sanguínea, coagulación, orina, cultivo, imagenología, patología, marcadores tumorales u otro), nombre del examen, fecha de muestra, fecha de resultado, resultado narrativo, archivo adjunto y observaciones.
2. **Valores:** cada parámetro se compara con su rango de referencia y recibe una bandera: Normal, Bajo, Alto, Crítico bajo, Crítico alto o Sin rango. La presencia de valores críticos marca todo el resultado.
3. **Marcar como revisado:** pulse la acción correspondiente cuando el resultado haya sido evaluado.
4. **Catálogo de parámetros** (`/laboratorio/catalogo/parametros/`): consulta de estudios y parámetros con sus unidades, rangos y alertas configuradas.

---

## 18. Notificaciones

> Ruta: **Comunicación → Notificaciones** (`/notificaciones/`). El encabezado muestra un contador de no leídas.

| Acción | Cómo |
|---|---|
| Abrir una notificación | Pulse sobre ella; el sistema lo lleva al registro relacionado |
| Marcar como leída / no leída | Botón de la propia notificación |
| Marcar todas como leídas | Botón en la parte superior del listado |
| Eliminar | Botón de la notificación |

Las notificaciones se clasifican por tipo (sistema, referencia, cita, seguimiento, alerta, alerta clínica, mensaje, reporte, documento, paciente, cribado, medicamento, síntomas) y por prioridad (Baja, Media, Alta, Crítica).

---

## 19. Mi perfil y mi contraseña

> Ruta: `/usuarios/perfil/`, accesible desde el avatar del encabezado. Disponible para todo el personal.

### 19.1 Actualizar mis datos

1. Entre a **Mi perfil**.
2. Modifique nombre, apellido, correo, especialidad, centro médico y foto de perfil.
3. Si desea recibir avisos por teléfono, active la opción correspondiente y registre su número.
4. Pulse **Guardar**.

### 19.2 Cambiar mi contraseña

1. En **Mi perfil**, abra el bloque de cambio de contraseña.
2. Escriba su **contraseña actual**.
3. Escriba la **nueva contraseña** y repítela. Debe tener **al menos 8 caracteres**.
4. Pulse **Cambiar contraseña**.

| Mensaje | Causa |
|---|---|
| «La contraseña actual es incorrecta.» | El primer campo no coincide con su clave vigente |
| «Las contraseñas nuevas no coinciden.» | Los dos campos nuevos son distintos |
| «La contraseña debe tener al menos 8 caracteres.» | Clave demasiado corta |

### 19.3 Mi actividad reciente

La pantalla muestra sus últimas acciones registradas (excluyendo entradas y salidas del sistema), útil para verificar su propio trabajo del día.

---

## 20. Portal de padres y tutores

Esta sección puede reproducirse y entregarse a las familias como instructivo breve.

### 20.1 Entrar

1. Abra la dirección del sitio seguida de `/acceso/padres/`.
2. Escriba el **código del paciente** (por ejemplo, `FACCI-20260001`) o su **correo electrónico**.
3. Escriba su **PIN** de 6 dígitos.
4. Pulse **Entrar**.

### 20.2 Qué encontrará

| Sección | Contenido |
|---|---|
| **Inicio** | Estado actual del paciente, próxima cita y datos del equipo médico |
| **Evolución** | Historial del seguimiento y botón para **reportar síntomas** |
| **Indicaciones** | Pautas médicas vigentes, con marcado de **medicamentos tomados** por día |
| **Recursos** | Material educativo: alimentación, apoyo emocional, medicamentos, higiene, actividad física, señales de alerta, cuidado en casa, apoyo escolar y preguntas frecuentes |
| **Docs** | Documentos compartidos por el equipo y carga de los documentos solicitados |
| **Alertas** | Avisos dirigidos a la familia |
| **Perfil** | Datos del tutor, editables |

### 20.3 Reportar síntomas

1. Entre a **Evolución** y pulse **Reportar síntomas**.
2. Indique la **fecha de inicio** y la **gravedad** (Leve, Moderada, Severa).
3. Marque los síntomas observados y añada una descripción.
4. Pulse **Enviar**.

El reporte llega al equipo clínico y puede generar una alerta.

> **Advertencia importante para las familias:** el portal **no sustituye la atención de urgencia**. Ante fiebre alta, sangrado, dificultad respiratoria o cualquier signo de gravedad, acuda de inmediato al centro de salud.

### 20.4 Responder a una solicitud de documento

1. Entre a **Docs**.
2. Localice la solicitud pendiente y pulse **Subir**.
3. Adjunte el archivo o la fotografía del documento y confirme.

### 20.5 Si olvidó su PIN

El PIN no puede recuperarse: se regenera. Comuníquese con el personal de FACCI o con el médico tratante, que puede generar uno nuevo (sección 10.5).

---

## 21. Panel avanzado (Django Admin)

> **Solo para el Administrador con cuenta de superusuario.** Ruta: `/admin/`.

Django Admin es la herramienta técnica de mantenimiento de datos. Permite consultar y editar directamente cualquier registro del sistema, incluidos catálogos que no tienen pantalla propia (por ejemplo, los **recursos educativos** del portal de padres o el **catálogo de estudios de laboratorio**).

**Reglas de uso:**

1. Use siempre las pantallas normales del sistema para el trabajo cotidiano. El panel avanzado **no aplica las mismas validaciones de negocio** que los formularios de la aplicación.
2. **No elimine** pacientes, referencias, cribados ni usuarios desde este panel: destruye la trazabilidad clínica.
3. Realice cualquier cambio masivo únicamente con respaldo previo de la base de datos.
4. Reserve el acceso a un número mínimo de personas.

---

## 22. Solución de problemas frecuentes

| Situación | Causa probable | Solución |
|---|---|---|
| «Credenciales incorrectas» al iniciar sesión | Usuario o contraseña mal escritos | Verifique el bloqueo de mayúsculas y los espacios; pruebe con su correo en lugar del usuario |
| «La cuenta está deshabilitada» | La cuenta fue desactivada | Solicite al administrador que la reactive |
| «No tienes permiso para acceder a esta sección» | Su rol no tiene ese módulo | Verifique la tabla de la sección 4; si necesita ese acceso, solicite el cambio de rol al administrador |
| No veo una opción del menú que otro compañero sí ve | Roles distintos | Es el comportamiento esperado |
| No encuentro un paciente que sé que existe | Está fuera de su alcance de datos | Los roles clínicos solo ven los pacientes que crearon o tienen asignados; el oncólogo, los referidos a él |
| No puedo crear un cribado | Su rol no lo permite | Solo Médico General y Pediatra crean cribados |
| El botón de generar reporte no aparece | Falta el permiso de generación | Solo Administrador y Coordinador FACCI generan y exportan reportes |
| «No se pudo enviar el correo» al remitir un reporte | Servidor de correo no configurado o sin conexión | El reporte quedó guardado: descárguelo y envíelo manualmente; informe al administrador |
| El tutor no puede entrar con el código del paciente | Código mal escrito o PIN incorrecto | Verifique el código en el expediente; si el PIN se perdió, regenérelo |
| El paciente no ve una indicación | La indicación no está marcada como visible o está inactiva | Revise las casillas **Activa** y **Visible para padre/tutor** |
| El paciente no ve un documento | El documento no está marcado como visible | Use **Cambiar visibilidad** en el documento |
| No puedo eliminar una habitación de la Casa FACCI | Tiene estancias asociadas | Deshabilítela en lugar de eliminarla |
| El centro de salud no aparece en el mapa | No tiene coordenadas | Edite el centro y registre latitud y longitud |
| La página no carga o queda en blanco | Sesión expirada o problema de conexión | Recargue la página; si persiste, cierre sesión y vuelva a entrar |

---

## 23. Preguntas frecuentes

**¿Puedo eliminar un usuario que ya no trabaja en la institución?**
No es recomendable. **Desactívelo**: la cuenta deja de poder entrar y se conserva el historial de todo lo que registró.

**¿Por qué el Administrador no puede hacer cribados?**
Porque el cribado es un acto clínico de detección que corresponde al médico que atiende al paciente. La restricción es intencional y garantiza que cada cribado tenga un responsable clínico identificable.

**¿Cómo cambio los permisos de una persona?**
Cambiando su **rol** desde **Usuarios → Editar**. Los permisos individuales no se editan: están definidos por rol para mantener la coherencia del sistema.

**¿Dónde veo quién modificó un registro?**
En **Auditoría**, filtrando por módulo, tipo de acción y rango de fechas.

**¿El sistema envía SMS?**
No. El canal implementado para el envío de documentos es el **correo electrónico**, desde el módulo de reportes.

**¿Se puede recuperar el PIN de un tutor?**
No se recupera: se **regenera** uno nuevo desde el expediente del paciente. El anterior deja de funcionar.

**¿Qué pasa si dos personas registran al mismo tutor?**
El sistema lo detecta por cédula o correo y **reutiliza la cuenta existente** en lugar de duplicarla.

**¿Puedo asignarle a un miembro del personal el rol de padre/tutor para hacer pruebas?**
No. El sistema rechaza vincular una cuenta del personal como tutor de un paciente.

**¿Los datos del paciente están protegidos?**
Sí. Las contraseñas se almacenan con Argon2, los datos más sensibles (dirección, alergias, antecedentes y teléfonos de contacto) se guardan cifrados, el acceso está restringido por rol y toda acción relevante queda registrada.

**¿Puedo usar el sistema desde el celular?**
Sí. La interfaz es responsiva y el portal de padres está diseñado especialmente para uso móvil.

---

## 24. Buenas prácticas y recomendaciones de seguridad

### 24.1 Para todo el personal

1. **No comparta su usuario ni su contraseña.** Cada acción queda registrada a nombre de quien inició sesión.
2. **Cierre sesión** al terminar, especialmente en equipos compartidos.
3. **Cambie la contraseña inicial** en su primer ingreso.
4. Use contraseñas de **al menos 8 caracteres**, sin datos personales fáciles de adivinar.
5. Verifique el paciente antes de registrar cualquier dato clínico.
6. Antes de marcar algo como visible para la familia, **confirme que es apropiado** compartirlo.
7. No descargue expedientes ni reportes a equipos personales sin autorización.

### 24.2 Para el administrador

1. Mantenga **al menos dos cuentas con rol de Administrador**, para evitar quedar sin acceso.
2. Revise mensualmente el listado de usuarios y desactive las cuentas del personal que ya no labora.
3. Revise semanalmente la auditoría en busca de accesos o cambios inesperados.
4. Verifique periódicamente que los **respaldos** de la base de datos y de los archivos se están realizando.
5. Custodie fuera del servidor la **clave de cifrado** del sistema: su pérdida hace irrecuperables los datos cifrados.
6. Entregue las credenciales iniciales por un canal privado, nunca en grupos de mensajería compartidos.
7. Cuando se publique una nueva versión del sistema, comunique al personal los cambios relevantes.

---

## 25. Soporte y contacto

Para incidencias, solicitudes de acceso, cambios de rol o dudas sobre el uso del sistema:

| Vía | Detalle |
|---|---|
| **Administrador del sistema FACCI Care** | Primer punto de contacto para altas, bajas, cambios de rol y restablecimiento de contraseñas |
| **Coordinación FACCI** | Consultas sobre reportes institucionales, matrices operativas y Casa FACCI |
| **Correo institucional** | El configurado en **Ajustes** para las comunicaciones del sistema |

Al reportar un problema, incluya:

1. Su nombre de usuario y su rol.
2. La pantalla o dirección donde ocurrió (por ejemplo, `/reportes/generar/`).
3. Los pasos exactos que realizó.
4. El mensaje de error, preferiblemente con una captura de pantalla.
5. La fecha y la hora aproximadas.

---

## 26. Anexos

### Anexo A — Rutas de acceso rápido

| Módulo | Dirección |
|---|---|
| Acceso del personal | `/login/` |
| Acceso de padres y tutores | `/acceso/padres/` |
| Inicio / Dashboard | `/` o `/dashboard/` |
| Pacientes | `/pacientes/` |
| Nuevo paciente | `/pacientes/nuevo/` |
| Cribado | `/cribado/` |
| Nuevo cribado | `/cribado/nuevo/` |
| Referencias | `/referencias/` |
| Nueva referencia | `/referencias/nueva/` |
| Seguimiento | `/seguimiento/` |
| Indicaciones | `/indicaciones/` |
| Laboratorio | `/laboratorio/` |
| Alertas clínicas | `/alertas/` |
| Psicosocial | `/psicosocial/` |
| Casa FACCI | `/alojamiento/` |
| Habitaciones | `/alojamiento/habitaciones/` |
| Documentos | `/documentos/` |
| Solicitudes de documentos | `/documentos/solicitudes/` |
| Reportes | `/reportes/` |
| Generar reporte | `/reportes/generar/` |
| PENCI-RD | `/reportes/penci/` |
| Matrices operativas | `/matrices/` |
| Centros de salud | `/centros-salud/` |
| Usuarios | `/usuarios/` |
| Roles | `/usuarios/roles/` |
| Auditoría | `/auditoria/` |
| Ajustes del sistema | `/ajustes/` |
| Mi perfil | `/usuarios/perfil/` |
| Notificaciones | `/notificaciones/` |
| Panel avanzado | `/admin/` |

### Anexo B — Tareas administrativas por frecuencia

| Frecuencia | Tarea | Responsable |
|---|---|---|
| Diaria | Revisar alertas clínicas pendientes | Equipo clínico |
| Diaria | Revisar notificaciones y solicitudes de documentos | Equipo clínico |
| Semanal | Revisar el panel de auditoría | Administrador |
| Semanal | Verificar la ocupación de la Casa FACCI | Trabajo Social / Coordinación |
| Mensual | Generar el reporte institucional del período | Administrador / Coordinación |
| Mensual | Revisar usuarios inactivos y bajas de personal | Administrador |
| Trimestral | Actualizar la información de los centros de salud | Administrador |
| Trimestral | Verificar respaldos y actualizar contraseñas administrativas | Administrador |

### Anexo C — Glosario para el usuario

| Término | Significado |
|---|---|
| **Alarma mayor** | Signo del cribado que por sí solo clasifica el caso como riesgo alto |
| **Alcance de datos** | Conjunto de pacientes y registros que usted puede ver según su rol |
| **Casa FACCI** | Alojamiento que la fundación ofrece a las familias durante el tratamiento |
| **Código de paciente** | Identificador único con formato `FACCI-AAAA0001` |
| **Contrarreferencia** | Respuesta del especialista al médico que refirió al paciente |
| **Cribado** | Cuestionario de detección temprana |
| **Descargo de tratamiento** | Documento con las indicaciones vigentes que se entrega a la familia |
| **Estancia** | Período de alojamiento de una familia en la Casa FACCI |
| **Fase de protocolo** | Etapa del tratamiento: Inducción, Consolidación, Mantenimiento o Vigilancia |
| **Indicación médica** | Pauta que el médico registra para que la familia la siga en casa |
| **Leucocoria** | Reflejo blanquecino en la pupila; signo de sospecha de retinoblastoma |
| **Matriz operativa** | Tablero de indicadores de coordinación por centro y provincia |
| **MSP** | Ministerio de Salud Pública |
| **PENCI-RD** | Formato de reporte estadístico nacional de cáncer infantil |
| **PIN** | Clave numérica de 6 dígitos del padre o tutor |
| **Referencia** | Derivación formal del paciente a un especialista o centro de mayor nivel |

### Anexo D — Constancia de entrega

Este manual se entrega en formato digital, por correo electrónico, a los responsables de FACCI. Se recomienda registrar la entrega con los siguientes datos:

| Campo | Registro |
|---|---|
| Documento entregado | Manual de Usuario — FACCI Care, versión 1.0 |
| Formato | Documento digital (PDF / Markdown) |
| Medio de entrega | Correo electrónico |
| Fecha de envío | _________________________ |
| Remitente | _________________________ |
| Destinatarios | _________________________ |
| Acuse de recibo | _________________________ |

---

*Fin del documento — Manual de Usuario FACCI Care, versión 1.0.*
