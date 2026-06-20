import json
from pathlib import Path


def guardar_json(datos, ruta):
    destino = Path(ruta)

    with open(destino, "w", encoding="utf-8") as archivo:
        json.dump(
            datos,
            archivo,
            ensure_ascii=False,
            indent=4,
        )

    return str(destino)
#Escribe el guardado en un JSON, devolviendo un valor por defecto si el archivo no existe o no se puede leer.

def cargar_json(ruta, valor_por_defecto=None):
    origen = Path(ruta)

    if not origen.exists():
        return valor_por_defecto

    with open(origen, "r", encoding="utf-8") as archivo:
        return json.load(archivo)
#leer el JSON desde un archivo, devolviendo un valor por defecto si el archivo no existe o no se puede leer. 
# Lee el guardado

def cargar_respaldo_pizzeria(pizzeria,ruta="respaldo_pizzeria.json"):
    # Intenta leer el archivo de respaldo.
    datos = cargar_json(ruta, None)

    # Informa si todavía no existe ningún guardado.
    if datos is None:
        raise FileNotFoundError(f"No se encontró el archivo '{ruta}'.")

    campos_obligatorios = ["stock","pedidos","ventas"]

    # Comprueba que el JSON tenga todos los datos necesarios.
    for campo in campos_obligatorios:

        if campo not in datos:
            raise ValueError(f"El guardado no contiene el campo '{campo}'.")

    # Envía los datos a la clase Pizzeria para reconstruir el sistema.
    pizzeria.cargar_datos(datos)
    return datos