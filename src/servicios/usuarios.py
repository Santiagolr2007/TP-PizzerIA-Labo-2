import json
from pathlib import Path


USUARIOS_INICIALES = {
    # Usuarios base del sistema. Las contrasenias quedan en texto plano
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
    # Usa la misma carpeta de respaldo que el resto del sistema para que los
    # cambios de contraseña sobrevivan al cierre del programa.
    ruta_proyecto = Path(__file__).resolve().parents[2]
    carpeta_respaldo = ruta_proyecto / "respaldo"
    carpeta_respaldo.mkdir(parents=True, exist_ok=True)
    return carpeta_respaldo / "usuarios_sistema.json" #Crea la ruta donde se crea la carpeta respaldo


def _crear_usuarios_iniciales():
    # Genera una copia nueva de los usuarios por defecto.
    # Esto evita modificar accidentalmente la constante USUARIOS_INICIALES.
    usuarios = {}
    for usuario, datos in USUARIOS_INICIALES.items(): #Crea los usuarios iniciales
        usuarios[usuario] = {
            "nombre": datos["nombre"],
            "rol": datos["rol"],
            "contrasenia": datos["contrasenia"],
        }
    return usuarios


def _asegurar_contrasenias_visibles(usuarios):
    # Normaliza el archivo viejo o incompleto para conservar solamente los datos
    # que necesita el login actual: nombre, rol y contrasenia visible.
    usuarios_base = _crear_usuarios_iniciales()

    for usuario, datos_base in usuarios_base.items():
        if usuario not in usuarios:
            usuarios[usuario] = datos_base
            continue

        # Mantiene solo los datos que usa el login: nombre, rol y contraseña.
        usuarios[usuario] = {
            "nombre": usuarios[usuario].get("nombre", datos_base["nombre"]),
            "rol": usuarios[usuario].get("rol", datos_base["rol"]),
            "contrasenia": usuarios[usuario].get("contrasenia", datos_base["contrasenia"]),
        }

    return usuarios


def cargar_usuarios():
    # Punto de entrada para leer usuarios: crea el archivo si falta, repara datos incompletos y vuelve a guardarlos ya normalizados.
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
    # Persiste usuarios y contrasenias en JSON legible, igual que los respaldos.
    ruta = obtener_ruta_usuarios()
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(usuarios, archivo, ensure_ascii=False, indent=4)
    return str(ruta)


def validar_usuario(nombre_usuario, contrasenia):
    # Compara usuario y contrasenia contra el archivo guardado.
    # Devuelve solo datos publicos de sesion, no toda la estructura del JSON.
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
    # Solo modifica la clave del usuario elegido y conserva su nombre y rol.
    # La validacion minima evita guardar claves vacias por accidente.
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
