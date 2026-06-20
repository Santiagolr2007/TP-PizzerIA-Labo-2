import json
from pathlib import Path


def obtener_carpeta_respaldo():
    # Obtiene la carpeta principal TP-PizzerIA-Labo-2.
    ruta_proyecto = Path(__file__).resolve().parents[2]
    # Define la carpeta donde se guardarán los archivos JSON.
    carpeta_respaldo = ruta_proyecto / "respaldo"
    # Crea la carpeta respaldo si todavía no existe.
    carpeta_respaldo.mkdir(parents=True, exist_ok=True)
    return carpeta_respaldo


def obtener_ruta_respaldo(ruta):
    # Convierte la ruta recibida en un objeto Path.
    ruta_recibida = Path(ruta)

    # Mantiene la ruta si ya es absoluta.
    if ruta_recibida.is_absolute():
        return ruta_recibida

    # Guarda el archivo dentro de la carpeta respaldo.
    carpeta_respaldo = obtener_carpeta_respaldo()
    return carpeta_respaldo / ruta_recibida.name


def guardar_json(datos, ruta):
    # Obtiene la ubicación completa del archivo.
    destino = obtener_ruta_respaldo(ruta)

    with open(destino, "w", encoding="utf-8") as archivo:
        json.dump(datos,archivo,ensure_ascii=False,indent=4)

    return str(destino)


def cargar_json(ruta, valor_por_defecto=None):
    # Obtiene la ubicación completa del archivo.
    origen = obtener_ruta_respaldo(ruta)
    # Devuelve el valor predeterminado si el archivo no existe.
    if not origen.exists():
        return valor_por_defecto

    try:
        with open(origen, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        return datos
    
    # Devuelve el valor predeterminado si el JSON está dañado.
    except (OSError, json.JSONDecodeError):
        return valor_por_defecto


def cargar_respaldo_pizzeria(pizzeria,ruta="respaldo_pizzeria.json"):
    # Intenta leer el archivo de respaldo.
    datos = cargar_json(ruta, None)

    # Informa si no existe un respaldo válido.
    if datos is None:
        raise FileNotFoundError(f"No se encontró un respaldo válido llamado '{ruta}'.")

    campos_obligatorios = ["stock","pedidos","ventas"]

    # Comprueba que el JSON tenga todos los datos necesarios.
    for campo in campos_obligatorios:
        if campo not in datos:
            raise ValueError(f"El guardado no contiene el campo '{campo}'.")
        
    # Envía los datos a Pizzeria para reconstruir el sistema.
    pizzeria.cargar_datos(datos)
    return datos