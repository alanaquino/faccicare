# Arquitectura de FACCI Care

Dos entregables generados a partir del análisis del repositorio.

| Archivo | Para qué sirve |
|---|---|
| `faccicare-arquitectura.html` | Diagrama interactivo autocontenido. Se abre con doble clic en cualquier navegador: no necesita servidor, dependencias ni conexión. |
| `faccicare-arquitectura.json` | El mismo grafo en datos, pensado para agentes de IA y herramientas. El HTML lleva una copia embebida, por lo que ambos archivos describen exactamente lo mismo. |

## El diagrama

- **Mapa por capas** de izquierda a derecha: actores → borde HTTP → autorización → dominio clínico → operación y portales → servicios → salida.
- **Panel de flujos** a la derecha con 18 recorridos reales del sistema. Al elegir uno se resalta su ruta completa sobre el diagrama, numerada en el orden de los pasos, y se atenúa lo demás.
- **Tooltips** en cada componente y en cada relación; el clic abre la ficha del componente (modelos, rutas, control de acceso, con quién habla y qué flujos lo atraviesan).
- **Capas conmutables**: control de acceso, auditoría, cifrado y persistencia están ocultas por defecto para no saturar la vista, pero cualquier flujo que las recorra las muestra igualmente.
- Búsqueda (`/`), navegación por pasos con las flechas, `Esc` para limpiar, zoom con rueda o pellizco, y descarga del JSON desde la propia página.
- Funciona en tema claro y oscuro, y se adapta a móvil, tableta y escritorio.

## Esquema del JSON

```jsonc
{
  "meta":   { /* proyecto, stack, entrypoints, estadísticas, observaciones */ },
  "layers": [ { "id", "label", "color", "descripcion" } ],
  "edgeKinds": [ { "id", "label", "default", "dash", "descripcion" } ],

  "nodes": [ {
    "id", "label", "sublabel", "layer", "type", "path",
    "summary",                 // qué hace, en una frase
    "detalles":  ["…"],        // reglas y matices relevantes
    "modelos":   ["…"],        // modelos Django que expone (opcional)
    "rutas":     ["…"],        // URLs que atiende (opcional)
    "acceso":    "…",          // propiedad de la matriz que lo protege (opcional)
    "x", "y", "w", "h"         // posición en el lienzo
  } ],

  "edges": [ {
    "id",                      // siempre "<source>__<target>"
    "source", "target",
    "kind",                    // peticion | flujo | evento | salida | acceso | auditoria | cifrado | datos
    "label", "detail"
  } ],

  "flows": [ {
    "id", "name", "category", "actor", "outcome", "description",
    "steps": [ {
      "n",                     // orden del paso
      "node",                  // id de nodo por el que pasa
      "edge",                  // id de arista que recorre (null en el primer paso)
      "title", "detail",
      "ref"                    // archivo:línea del código, cuando aplica (opcional)
    } ]
  } ]
}
```

Invariantes que puedes asumir: todo `edges[].source` y `edges[].target` existe en `nodes`; todo `flows[].steps[].node` existe en `nodes` y todo `steps[].edge` no nulo existe en `edges`; los `id` de arista siguen el patrón `source__target`.

## Regenerar el HTML tras editar el JSON

El HTML embebe el JSON en `<script type="application/json" id="graph-data">`. Para propagar un cambio basta con sustituir ese bloque; el resto de la página se dibuja sola a partir de los datos (posiciones, aristas, leyenda, panel y estadísticas).
