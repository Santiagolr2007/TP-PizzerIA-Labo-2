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
#Lee el guardado