def formato_moneda(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0
    texto = f"{numero:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"${texto}"


def formato_numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    if numero.is_integer():
        return str(int(numero))

    return f"{numero:.2f}"


def leer_importe(texto):
    valor = str(texto).strip().replace("$", "").replace(" ", "")
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    return float(valor)


def estado_visible(estado):
    estados = {
        "pendiente": "Pendiente",
        "en preparacion": "En preparaciÃ³n",
        "listo": "Listo",
        "en camino": "En camino",
        "entregado": "Entregado",
        "cancelado": "Cancelado",
    }
    texto = str(estado).strip().lower()
    return estados.get(texto, str(estado).replace("_", " ").capitalize())


def nombre_ingrediente_visible(nombre):
    ingredientes = {
        "jamon": "jamÃ³n",
        "morron": "morrÃ³n",
        "jamon_queso": "jamÃ³n y queso",
        "tapas_empanada": "tapas de empanada",
    }
    texto = str(nombre).strip()
    return ingredientes.get(texto.lower(), texto.replace("_", " "))


def capitalizar_visible(texto):
    texto_visible = nombre_ingrediente_visible(texto)
    if not texto_visible:
        return ""
    return texto_visible[0].upper() + texto_visible[1:]


def normalizar_ingrediente_ingresado(nombre):
    ingredientes = {
        "jamÃ³n": "jamon",
        "morrÃ³n": "morron",
        "jamÃ³n y queso": "jamon_queso",
        "tapas de empanada": "tapas_empanada",
    }
    texto = str(nombre).strip().lower()
    return ingredientes.get(texto, texto)


def obtener_resumen_productos(pedido):
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
