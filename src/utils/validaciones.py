#Revisa que el correo del cliente tenga un formato real y valido
"""def validar_email(email: str):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not isinstance(email, str) or not re.match(patron, email):
        return False
    return True"""

#Revisa que los campos de texto no estén vacíos, se asegura de que el mensaje de error sea claro al incluir el nombre del campo que no cumple con la validación.
def validar_texto(valor, nombre_campo):
    texto = str(valor).strip()
    if not texto:
        raise ValueError(f"El campo '{nombre_campo}' no puede estar vacío.")
    return texto

#Se asegura de que los valores que representan dinero o stock sean numeros validos, reales, positivos y nombra el campo para que el mensaje de error sea mas claro.
def validar_entero_positivo(valor, nombre_campo):
    try:
        numero = int(valor)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{nombre_campo}' debe ser un número entero.") from error

    if numero <= 0:
        raise ValueError(f"El campo '{nombre_campo}' debe ser mayor que cero.")
    return numero

#Se asegura de que los valores que representan dinero sean numeros validos, reales, positivos
def validar_precio(valor):
    try:
        precio = float(valor)
    except (TypeError, ValueError) as error:
        raise ValueError("El precio debe ser numérico.") from error

    if precio <= 0:
        raise ValueError("El precio debe ser mayor que cero.")
    return precio


#revisa la estructura completa de un pedido
"""
def validar_estructura_pedido(pedido: dict):
    if not isinstance(pedido, dict):
        raise ValidacionDatosError("El pedido debe ser estrictamente un diccionario.")
        
    claves_obligatorias = ["cliente", "productos", "total"]
    for clave in claves_obligatorias:
        if clave not in pedido:
            raise ValidacionDatosError(f"Estructura de pedido invalida: falta la clave obligatoria '{clave}'.")
            
    if not isinstance(pedido["productos"], list) or len(pedido["productos"]) == 0:
        raise ValidacionDatosError("El campo 'productos' debe ser una lista poblada.")"""
