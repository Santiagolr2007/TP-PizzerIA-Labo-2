import json
from pathlib import Path


def obtener_carpeta_respaldo():
    # Obtiene la carpeta principal TP-PizzerIA-Labo-2.
    ruta_proyecto = Path(__file__).resolve().parents[2]
    # Define la carpeta donde se guardarán los archivos JSON y le agrega "respaldo" a la ruta.
    carpeta_respaldo = ruta_proyecto / "respaldo"
    # Crea la carpeta respaldo si todavía no existe.
    carpeta_respaldo.mkdir(parents=True, exist_ok=True)
    return carpeta_respaldo


def obtener_ruta_respaldo(ruta):
    # Convierte la ruta recibida en un objeto Path.
    ruta_recibida = Path(ruta)

    # Mantiene la ruta si ya es absoluta, osea empieza con "\"
    if ruta_recibida.is_absolute(): 
        return ruta_recibida

    #Si no empezo con "\", osea la ruta no era absoluta
    carpeta_respaldo = obtener_carpeta_respaldo()
    return carpeta_respaldo / ruta_recibida.name #ruta_recibida.name devuelve el ultimo nombre de la ruta


def guardar_json(datos, ruta):
    # Obtiene la ubicación completa del archivo.
    destino = obtener_ruta_respaldo(ruta)

    with open(destino, "w", encoding="utf-8") as archivo:
        json.dump(datos,archivo,ensure_ascii=False,indent=4) #escribe un archivo json en el archivo abierto prviamente en destino

    return str(destino)


def cargar_json(ruta, valor_por_defecto=None):
    # Obtiene la ubicación completa del archivo.
    origen = obtener_ruta_respaldo(ruta)
    # Devuelve el valor predeterminado si el archivo no existe.
    if not origen.exists(): #.exists() valor booleano dice si existe la ruta o no.
        return valor_por_defecto

    try:
        with open(origen, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo) #carga el archivo del respaldo en la variable "datos"
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
            raise ValueError(f"El guardado no contiene el campo '{campo}'.") #Da error si la falta un campo obligatorio
        
    # Envía los datos a Pizzeria para reconstruir el sistema.
    pizzeria.cargar_datos(datos) #Llama un metodo de pizzeria.
    return datos