# CineGrafo — Dgraph Lab 2 (pydgraph)

Aplicación de consola que convierte el modelo de grafos del Lab 1 (plataforma de streaming) en un cliente funcional con **pydgraph**.

## Estructura

| Archivo | Qué hace |
|---------|----------|
| `main.py` | Conexión a Dgraph, crea el schema al iniciar y muestra el menú |
| `model.py` | Schema, carga de CSVs, queries y deletes |
| `data/*.csv` | Un CSV por tipo de nodo + `relaciones.csv` (origen, relacion, destino) |

## Cómo ejecutar

1. Levantar Dgraph y Ratel:
   ```bash
   docker run --name dgraph -d -p 8080:8080 -p 9080:9080 dgraph/standalone:latest
   docker run --name ratel -d -p 8000:8000 dgraph/ratel:latest
   ```
2. Instalar dependencias: `pip install -r requirements.txt`
3. Ejecutar: `python main.py` (opcional: `DGRAPH_URI=host:9080`)
4. Elegir **1** para cargar los CSVs y luego cualquier query o delete.

> Si cargas dos veces sin borrar, se duplican nodos: usa la opción 12 (Drop All) antes de recargar.

## Schema

- **6 tipos:** Usuario, Plataforma, Contenido, Genero, Persona, Resena.
- **Índice de texto:** `titulo` y `nombre` con `@index(exact, term)`.
- **Índice numérico:** `calificacion_prom @index(float)`, `anio_estreno` y `estrellas @index(int)`.
- **Geo:** `Plataforma.location: geo @index(geo)` (sede, `[lon, lat]`).
- **Reverse:** todas las relaciones (`ve`, `tiene`, `pertenece`, ...) tienen `@reverse`.

## Opciones del menú

| # | Requisito | Implementación |
|---|-----------|----------------|
| 2 | Texto indexado | `anyofterms(titulo, ...)` |
| 3 | Numérico indexado | `ge(calificacion_prom, X)` |
| 4 | 2+ tipos de nodo | Contenido → `tiene` (Genero), `esta_en` (Plataforma), `~pertenece` (Persona) |
| 5 | Reversa | `~ve` (usuarios que vieron un contenido) |
| 6 | Orden | `orderdesc: calificacion_prom` |
| 7 | Count | `count(~tiene)` por género |
| 8 | Paginación | `first: 5, offset: (pagina-1)*5` |
| 9 | Geo (extra) | `near(location, [lon, lat], metros)` |
| 10–11 | Delete con condición | por `eq(email, ...)` / `lt(estrellas, N)` |
| 12 | Delete all | `Operation(drop_all=True)` |

Ejemplos para probar: título `Dark`, calificación `8.5`, contenido `Dune`, punto `-103.35, 20.67` con radio `50` km, email `ana@mail.com`, estrellas `3`.
