#Revisa que el correo del cliente tenga un formato real y valido
def validar_email(email: str):
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not isinstance(email, str) or not re.match(patron, email):
        return False
    return True

#Se asegura de que los valores que representan dinero o stock sean numeros validos, reales y positivos
def validar_precio_o_cantidad(valor):
    try:
        num = float(valor)
        return num >= 0
    except (ValueError, TypeError):
        return False

#revisa la estructura completa de un pedido
def validar_estructura_pedido(pedido: dict):
    if not isinstance(pedido, dict):
        raise ValidacionDatosError("El pedido debe ser estrictamente un diccionario.")
        
    claves_obligatorias = ["cliente", "productos", "total"]
    for clave in claves_obligatorias:
        if clave not in pedido:
            raise ValidacionDatosError(f"Estructura de pedido invalida: falta la clave obligatoria '{clave}'.")
            
    if not isinstance(pedido["productos"], list) or len(pedido["productos"]) == 0:
        raise ValidacionDatosError("El campo 'productos' debe ser una lista poblada.")
