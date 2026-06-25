#Revisa que los campos de texto no estén vacíos, se asegura de que el mensaje de error sea claro al incluir el nombre del campo que no cumple con la validación.
def validar_texto(valor, nombre_campo):
    # Normaliza cadenas antes de guardarlas y obliga a que los campos visibles
    # tengan contenido real, no solo espacios.
    texto = str(valor).strip()
    if not texto:
        raise ValueError(f"El campo '{nombre_campo}' no puede estar vacío.")
    return texto

#Se asegura de que los valores que representan dinero o stock sean numeros validos, reales, positivos y nombra el campo para que el mensaje de error sea mas claro.
def validar_entero_positivo(valor, nombre_campo):
    # Se usa para cantidades de productos y stock: deben ser enteros mayores a cero.
    try:
        numero = int(valor)
    except (TypeError, ValueError) as error:
        raise ValueError(f"El campo '{nombre_campo}' debe ser un número entero.") from error

    if numero <= 0:
        raise ValueError(f"El campo '{nombre_campo}' debe ser mayor que cero.")
    return numero

#Se asegura de que los valores que representan dinero sean numeros validos, reales, positivos
def validar_precio(valor):
    # Se usa para precios y costos: acepta valores numericos y rechaza cero o negativos.
    try:
        precio = float(valor)
    except (TypeError, ValueError) as error:
        raise ValueError("El precio debe ser numérico.") from error

    if precio <= 0:
        raise ValueError("El precio debe ser mayor que cero.")
    return precio
