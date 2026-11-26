#!/usr/bin/env python3
"""CineGrafo - cliente de consola para Dgraph (pydgraph)."""
import os

import pydgraph

import model

DGRAPH_URI = os.getenv('DGRAPH_URI', 'localhost:9080')

MENU = {
    1: "Cargar datos desde CSV",
    2: "Buscar contenido por titulo (texto indexado)",
    3: "Contenido con calificacion >= X (numerico indexado)",
    4: "Contenidos con generos, plataformas y personas (2+ tipos)",
    5: "Usuarios que vieron un contenido (reversa ~ve)",
    6: "Ranking por calificacion (orden)",
    7: "Contenidos por genero (count)",
    8: "Listar contenidos paginados (first/offset)",
    9: "Plataformas cercanas a un punto (geo near)",
    10: "Eliminar usuario por email (delete con condicion)",
    11: "Eliminar reseñas con menos de N estrellas (delete con condicion)",
    12: "Drop All (borrar todo)",
    0: "Salir",
}


def print_menu():
    print("\n===== CineGrafo =====")
    for key, label in MENU.items():
        print(f"{key:>2} -- {label}")


def create_client_stub():
    return pydgraph.DgraphClientStub(DGRAPH_URI)


def create_client(client_stub):
    return pydgraph.DgraphClient(client_stub)


def run_option(client, option):
    if option == 1:
        model.load_data(client)
    elif option == 2:
        model.buscar_contenido_por_titulo(client, input("Palabras del titulo: "))
    elif option == 3:
        model.contenido_por_calificacion(client, float(input("Calificacion minima: ")))
    elif option == 4:
        model.contenido_con_generos_y_plataformas(client)
    elif option == 5:
        model.usuarios_que_vieron(client, input("Titulo exacto: "))
    elif option == 6:
        model.contenido_ordenado(client)
    elif option == 7:
        model.contar_contenidos_por_genero(client)
    elif option == 8:
        model.contenido_paginado(client, int(input("Pagina (1, 2, 3...): ")))
    elif option == 9:
        lon = float(input("Longitud (ej. -103.35): "))
        lat = float(input("Latitud (ej. 20.67): "))
        km = float(input("Radio en km: "))
        model.plataformas_cercanas(client, lon, lat, km * 1000)  # near usa metros
    elif option == 10:
        model.delete_usuario_por_email(client, input("Email: "))
    elif option == 11:
        model.delete_resenas_menores_a(client, int(input("Estrellas minimas a conservar: ")))
    elif option == 12:
        model.drop_all(client)
        model.set_schema(client)   # se recrea el schema para seguir usando el cliente
        print("Datos eliminados (schema recreado)")
    else:
        print("Opcion no valida")


def main():
    client_stub = create_client_stub()
    client = create_client(client_stub)
    try:
        model.set_schema(client)
        print(f"Conectado a {DGRAPH_URI} y schema creado")

        while True:
            print_menu()
            try:
                option = int(input("Opcion: "))
            except ValueError:
                print("Escribe un numero")
                continue
            if option == 0:
                break
            try:
                run_option(client, option)
            except ValueError:
                print("Valor invalido, intenta de nuevo")
            except Exception as e:
                print(f"Error: {e}")
    finally:
        client_stub.close()


if __name__ == '__main__':
    main()
