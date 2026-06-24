import json
from pathlib import Path


USUARIOS_INICIALES = {
    "administrador": {
        "nombre": "Administrador",
        "rol": "Administrador",
        "contrasenia": "admin123",
    },
    "empleado": {
        "nombre": "Empleado",
        "rol": "Empleado",
        "contrasenia": "empleado123",
    },
}


def obtener_ruta_usuarios():
    ruta_proyecto = Path(__file__).resolve().parents[2]
    carpeta_respaldo = ruta_proyecto / "respaldo"
    carpeta_respaldo.mkdir(parents=True, exist_ok=True)
    return carpeta_respaldo / "usuarios_sistema.json"


def _crear_usuarios_iniciales():
    usuarios = {}
    for usuario, datos in USUARIOS_INICIALES.items():
        usuarios[usuario] = {
            "nombre": datos["nombre"],
            "rol": datos["rol"],
            "contrasenia": datos["contrasenia"],
        }
    return usuarios


def _asegurar_contrasenias_visibles(usuarios):
    usuarios_base = _crear_usuarios_iniciales()

    for usuario, datos_base in usuarios_base.items():
        if usuario not in usuarios:
            usuarios[usuario] = datos_base
            continue

        # Mantiene solo los datos que usa el login: nombre, rol y contrasenia.
        usuarios[usuario] = {
            "nombre": usuarios[usuario].get("nombre", datos_base["nombre"]),
            "rol": usuarios[usuario].get("rol", datos_base["rol"]),
            "contrasenia": usuarios[usuario].get("contrasenia", datos_base["contrasenia"]),
        }

    return usuarios


def cargar_usuarios():
    ruta = obtener_ruta_usuarios()
    if not ruta.exists():
        usuarios = _crear_usuarios_iniciales()
        guardar_usuarios(usuarios)
        return usuarios

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            usuarios = json.load(archivo)
    except (OSError, json.JSONDecodeError):
        usuarios = _crear_usuarios_iniciales()

    usuarios = _asegurar_contrasenias_visibles(usuarios)
    guardar_usuarios(usuarios)
    return usuarios


def guardar_usuarios(usuarios):
    ruta = obtener_ruta_usuarios()
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(usuarios, archivo, ensure_ascii=False, indent=4)
    return str(ruta)


def validar_usuario(nombre_usuario, contrasenia):
    usuario = str(nombre_usuario).strip().lower()
    clave = str(contrasenia)
    usuarios = cargar_usuarios()

    if usuario not in usuarios:
        raise ValueError("Usuario o contraseña incorrectos.")

    if clave != usuarios[usuario].get("contrasenia"):
        raise ValueError("Usuario o contraseña incorrectos.")

    datos = usuarios[usuario]
    return {
        "usuario": usuario,
        "nombre": datos.get("nombre", usuario.capitalize()),
        "rol": datos.get("rol", "Empleado"),
    }


def cambiar_contrasenia(usuario, nueva_contrasenia):
    usuario_normalizado = str(usuario).strip().lower()
    nueva = str(nueva_contrasenia)
    if len(nueva.strip()) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")

    usuarios = cargar_usuarios()
    if usuario_normalizado not in usuarios:
        raise ValueError("El usuario seleccionado no existe.")

    usuarios[usuario_normalizado]["contrasenia"] = nueva
    guardar_usuarios(usuarios)
    return usuarios[usuario_normalizado]
