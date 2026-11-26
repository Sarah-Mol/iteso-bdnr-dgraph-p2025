#!/usr/bin/env python3
"""CineGrafo - modelo: schema, carga de CSVs, queries y deletes con pydgraph."""
import csv
import json
import os

import pydgraph

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# ---------------------------------------------------------------------------
# SCHEMA
# ---------------------------------------------------------------------------
def set_schema(client):
    """Crea el schema: 6 tipos, indices de texto/numericos, geo y @reverse."""
    schema = """
    type Usuario {
        nombre
        email
        pais
        ve
        suscrito
        escribe
        amigo
        sigue_a
    }

    type Plataforma {
        nombre
        precio_mensual
        moneda
        location
    }

    type Contenido {
        titulo
        tipo
        anio_estreno
        calificacion_prom
        esta_en
        secuela
        tiene
    }

    type Genero {
        nombre
    }

    type Persona {
        nombre
        rol_principal
        pertenece
    }

    type Resena {
        estrellas
        texto
        resena_de
    }

    # Indices de texto
    nombre: string @index(exact, term) .
    titulo: string @index(exact, term) .
    email: string @index(exact) @upsert .
    pais: string @index(exact) .
    tipo: string @index(exact) .
    rol_principal: string @index(exact) .
    moneda: string .
    texto: string .

    # Indices numericos
    calificacion_prom: float @index(float) .
    anio_estreno: int @index(int) .
    estrellas: int @index(int) .
    precio_mensual: float .

    # Geo: ubicacion de la sede de la plataforma
    location: geo @index(geo) .

    # Relaciones (todas se pueden recorrer en reversa con ~)
    ve: [uid] @reverse @count .
    suscrito: [uid] @reverse .
    esta_en: [uid] @reverse .
    escribe: [uid] @reverse .
    resena_de: [uid] @reverse .
    amigo: [uid] @reverse .
    sigue_a: [uid] @reverse .
    secuela: [uid] @reverse .
    tiene: [uid] @reverse @count .
    pertenece: [uid] @reverse .
    """
    return client.alter(pydgraph.Operation(schema=schema))


# ---------------------------------------------------------------------------
# CARGA DE DATOS (CSV)
# ---------------------------------------------------------------------------
def _read_csv(filename):
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _usuario(row):
    return {"nombre": row["nombre"], "email": row["email"], "pais": row["pais"]}


def _plataforma(row):
    return {
        "nombre": row["nombre"],
        "precio_mensual": float(row["precio_mensual"]),
        "moneda": row["moneda"],
        # GeoJSON usa [longitud, latitud]
        "location": {"type": "Point",
                     "coordinates": [float(row["lon"]), float(row["lat"])]},
    }


def _contenido(row):
    return {
        "titulo": row["titulo"],
        "tipo": row["tipo"],
        "anio_estreno": int(row["anio_estreno"]),
        "calificacion_prom": float(row["calificacion_prom"]),
    }


def _genero(row):
    return {"nombre": row["nombre"]}


def _persona(row):
    return {"nombre": row["nombre"], "rol_principal": row["rol_principal"]}


def _resena(row):
    return {"estrellas": int(row["estrellas"]), "texto": row["texto"]}


# archivo CSV -> (dgraph.type, funcion que convierte la fila)
NODE_FILES = [
    ("usuarios.csv", "Usuario", _usuario),
    ("plataformas.csv", "Plataforma", _plataforma),
    ("contenidos.csv", "Contenido", _contenido),
    ("generos.csv", "Genero", _genero),
    ("personas.csv", "Persona", _persona),
    ("resenas.csv", "Resena", _resena),
]


def load_nodes(client):
    """Crea todos los nodos. Regresa {id_csv: uid_real}."""
    nodes = []
    for filename, dtype, convert in NODE_FILES:
        for row in _read_csv(filename):
            node = convert(row)
            node["uid"] = "_:" + row["id"]       # blank node sin espacios
            node["dgraph.type"] = dtype
            nodes.append(node)

    txn = client.txn()
    try:
        res = txn.mutate(set_obj=nodes)
        txn.commit()
        print(f"{len(nodes)} nodos creados")
        return res.uids
    finally:
        txn.discard()


def load_edges(client, uids):
    """Crea las relaciones leyendo relaciones.csv (origen, relacion, destino)."""
    txn = client.txn()
    count = 0
    try:
        for row in _read_csv("relaciones.csv"):
            txn.mutate(set_obj={
                "uid": uids[row["origen"]],
                row["relacion"]: {"uid": uids[row["destino"]]},
            })
            count += 1
        txn.commit()   # un solo commit para todo el lote
        print(f"{count} relaciones creadas")
    finally:
        txn.discard()


def load_data(client):
    uids = load_nodes(client)
    load_edges(client, uids)


# ---------------------------------------------------------------------------
# QUERIES
# ---------------------------------------------------------------------------
def _run(client, query, variables=None):
    res = client.txn(read_only=True).query(query, variables=variables)
    data = json.loads(res.json)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return data


def buscar_contenido_por_titulo(client, palabras):
    """1. Campo de texto indexado (titulo @index(term)) con anyofterms."""
    query = """query q($p: string) {
        contenidos(func: anyofterms(titulo, $p)) {
            titulo
            tipo
            anio_estreno
            calificacion_prom
        }
    }"""
    return _run(client, query, {"$p": palabras})


def contenido_por_calificacion(client, minimo):
    """2. Campo numerico indexado (calificacion_prom @index(float)) con ge."""
    query = """query q($min: float) {
        contenidos(func: ge(calificacion_prom, $min)) {
            titulo
            calificacion_prom
        }
    }"""
    return _run(client, query, {"$min": str(minimo)})


def contenido_con_generos_y_plataformas(client):
    """3. Varios tipos de nodo: Contenido -> Genero, Plataforma, Persona."""
    query = """{
        contenidos(func: type(Contenido)) {
            titulo
            tiene { nombre }
            esta_en { nombre precio_mensual moneda }
            ~pertenece { nombre rol_principal }
        }
    }"""
    return _run(client, query)


def usuarios_que_vieron(client, titulo):
    """4. Relacion en reversa: Contenido <- ve - Usuario (~ve)."""
    query = """query q($t: string) {
        contenido(func: eq(titulo, $t)) {
            titulo
            vistos_por: ~ve {
                nombre
                pais
            }
        }
    }"""
    return _run(client, query, {"$t": titulo})


def contenido_ordenado(client):
    """5. Ordenar: contenidos por calificacion_prom descendente."""
    query = """{
        ranking(func: type(Contenido), orderdesc: calificacion_prom) {
            titulo
            calificacion_prom
            anio_estreno
        }
    }"""
    return _run(client, query)


def contar_contenidos_por_genero(client):
    """6. count: cuantos contenidos tiene cada genero (count(~tiene))."""
    query = """{
        generos(func: type(Genero), orderasc: nombre) {
            nombre
            total_contenidos: count(~tiene)
        }
        total(func: type(Contenido)) {
            total_contenidos: count(uid)
        }
    }"""
    return _run(client, query)


def contenido_paginado(client, pagina, tamano=5):
    """7. Paginacion con first y offset."""
    query = """query q($first: int, $offset: int) {
        pagina(func: type(Contenido), orderasc: titulo,
               first: $first, offset: $offset) {
            titulo
            anio_estreno
        }
    }"""
    offset = (pagina - 1) * tamano
    return _run(client, query, {"$first": str(tamano), "$offset": str(offset)})


def plataformas_cercanas(client, lon, lat, metros):
    """Extra: funcion geo near sobre location (metros)."""
    query = """{
        cercanas(func: near(location, [%f, %f], %d)) {
            nombre
            location
        }
    }""" % (float(lon), float(lat), int(metros))
    return _run(client, query)


# ---------------------------------------------------------------------------
# DELETES
# ---------------------------------------------------------------------------
def delete_usuario_por_email(client, email):
    """Delete con condicion: borra el usuario cuyo email coincide."""
    query = """query q($e: string) {
        usuarios(func: eq(email, $e)) { uid nombre }
    }"""
    res = client.txn(read_only=True).query(query, variables={"$e": email})
    usuarios = json.loads(res.json)["usuarios"]
    if not usuarios:
        print(f"No existe usuario con email {email}")
        return

    txn = client.txn()
    try:
        for u in usuarios:
            txn.mutate(del_obj={"uid": u["uid"]})
            print(f"Eliminado: {u['nombre']} ({u['uid']})")
        txn.commit()
    finally:
        txn.discard()


def delete_resenas_menores_a(client, estrellas):
    """Delete con condicion: borra reseñas con menos de N estrellas."""
    query = """query q($s: int) {
        resenas(func: lt(estrellas, $s)) { uid estrellas texto }
    }"""
    res = client.txn(read_only=True).query(query, variables={"$s": str(estrellas)})
    resenas = json.loads(res.json)["resenas"]
    txn = client.txn()
    try:
        for r in resenas:
            txn.mutate(del_obj={"uid": r["uid"]})
            print(f"Eliminada reseña ({r['estrellas']}*): {r['texto']}")
        txn.commit()
        print(f"{len(resenas)} reseñas eliminadas")
    finally:
        txn.discard()


def drop_all(client):
    """Borra todos los datos y el esquema."""
    return client.alter(pydgraph.Operation(drop_all=True))
