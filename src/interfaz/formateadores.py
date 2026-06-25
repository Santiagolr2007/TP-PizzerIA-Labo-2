# Funciones de presentación: convierten valores internos del sistema en texto prolijo para botones, tablas, tickets y mensajes de la interfaz gráfica.


def formato_moneda(valor):
    # Convierte cualquier numero a texto de dinero con separadores locales. Si llega un dato invalido, muestra $0,00 para no romper la interfaz.
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0
    texto = f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"${texto}"


def formato_numero(valor):
    # Evita mostrar decimales innecesarios cuando una cantidad es entera.
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    if numero.is_integer():
        return str(int(numero))

    return f"{numero:.2f}"


def leer_importe(texto):
    # Hace el camino inverso de formato_moneda: limpia simbolos y separadores para convertir lo escrito por el usuario en float.
    valor = str(texto).strip().replace("$", "").replace(" ", "")
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


def estado_visible(estado):
    # Traduce estados internos a texto legible para botones, tablas y tickets.
    estados = {
        "pendiente": "Pendiente",
        "en preparacion": "En preparación",
        "listo": "Listo",
        "en camino": "En camino",
        "entregado": "Entregado",
        "cancelado": "Cancelado",
    }
    texto = str(estado).strip().lower()
    return estados.get(texto, str(estado).replace("_", " ").capitalize())


def nombre_ingrediente_visible(nombre):
    # Convierte nombres internos del stock a nombres mas naturales. Por ejemplo, jamon_queso pasa a verse como jamon y queso.
    ingredientes = {
        "jamon": "jamón",
        "morron": "morrón",
        "jamon_queso": "jamón y queso",
        "tapas_empanada": "tapas de empanada",
    }
    texto = str(nombre).strip()
    return ingredientes.get(texto.lower(), texto.replace("_", " "))


def capitalizar_visible(texto):
    # Capitaliza manteniendo las correcciones de nombre_ingrediente_visible.
    texto_visible = nombre_ingrediente_visible(texto)
    if not texto_visible:
        return ""
    return texto_visible[0].upper() + texto_visible[1:]


def normalizar_ingrediente_ingresado(nombre):
    # Convierte lo que escribe el usuario a la clave interna usada por inventario.
    # Esto permite aceptar nombres visibles sin romper el stock.
    ingredientes = {
        "jamón": "jamon",
        "morrón": "morron",
        "jamón y queso": "jamon_queso",
        "tapas de empanada": "tapas_empanada",
    }
    texto = str(nombre).strip().lower()
    return ingredientes.get(texto, texto)


def obtener_resumen_productos(pedido):
    # Agrupa productos repetidos del pedido para mostrar una descripcion corta
    # en tablas y reportes, incluyendo una marca cuando hubo promocion.
    productos_agrupados = {}

    for linea in pedido.iterar_lineas_detalle():
        nombre = linea["nombre"]
        if nombre not in productos_agrupados:
            productos_agrupados[nombre] = {"cantidad": 0, "subtotal": 0, "descuento": 0}

        productos_agrupados[nombre]["cantidad"] += linea["cantidad"]
        productos_agrupados[nombre]["subtotal"] += linea["subtotal"]
        productos_agrupados[nombre]["descuento"] += linea["descuento"]

    textos = []
    for nombre_producto, datos in productos_agrupados.items():
        texto = f"{nombre_producto} x{datos['cantidad']} ({formato_moneda(datos['subtotal'])})"
        if datos["descuento"]:
            texto += " promo"
        textos.append(texto)

    return ", ".join(textos)
