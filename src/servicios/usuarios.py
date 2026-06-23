import hashlib
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


def _hashear_contrasenia(usuario, contrasenia):
    texto = f"{usuario}:{contrasenia}".encode("utf-8")
    return hashlib.sha256(texto).hexdigest()


def _crear_usuarios_iniciales():
    usuarios = {}
    for usuario, datos in USUARIOS_INICIALES.items():
        usuarios[usuario] = {
            "nombre": datos["nombre"],
            "rol": datos["rol"],
            "hash": _hashear_contrasenia(usuario, datos["contrasenia"]),
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
        guardar_usuarios(usuarios)

    for usuario, datos in _crear_usuarios_iniciales().items():
        if usuario not in usuarios:
            usuarios[usuario] = datos

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

    hash_ingresado = _hashear_contrasenia(usuario, clave)
    if hash_ingresado != usuarios[usuario].get("hash"):
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

    usuarios[usuario_normalizado]["hash"] = _hashear_contrasenia(usuario_normalizado, nueva)
    guardar_usuarios(usuarios)
    return usuarios[usuario_normalizado]
