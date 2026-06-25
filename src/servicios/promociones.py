from src.modelos.producto import Bebida, Empanada, Pizza


# Cada promocion define requisitos minimos por categoria y un porcentaje.
# La lista esta ordenada por prioridad: primero combos grandes, despues promos simples.
PROMOCIONES = (
    {
        "tipo": "combo_completo",
        "nombre": "Combo pizza + 2 empanadas + 2 bebidas",
        "descripcion": "15% de descuento en el combo completo",
        "porcentaje": 0.15,
        "requisitos": {"pizzas": 1, "empanadas": 2, "bebidas": 2},
    },
    {
        "tipo": "pizza_empanadas",
        "nombre": "Combo pizza + media docena",
        "descripcion": "12% de descuento en pizzas y empanadas",
        "porcentaje": 0.12,
        "requisitos": {"pizzas": 1, "empanadas": 6, "bebidas": 0},
    },
    {
        "tipo": "pizzas",
        "nombre": "Promo 3 pizzas",
        "descripcion": "12% de descuento en pizzas",
        "porcentaje": 0.12,
        "requisitos": {"pizzas": 3, "empanadas": 0, "bebidas": 0},
    },
    {
        "tipo": "empanadas",
        "nombre": "Promo docena de empanadas",
        "descripcion": "15% de descuento en empanadas",
        "porcentaje": 0.15,
        "requisitos": {"pizzas": 0, "empanadas": 12, "bebidas": 0},
    },
    {
        "tipo": "pizzas",
        "nombre": "Promo 2 pizzas",
        "descripcion": "8% de descuento en pizzas",
        "porcentaje": 0.08,
        "requisitos": {"pizzas": 2, "empanadas": 0, "bebidas": 0},
    },
    {
        "tipo": "empanadas",
        "nombre": "Promo media docena de empanadas",
        "descripcion": "10% de descuento en empanadas",
        "porcentaje": 0.10,
        "requisitos": {"pizzas": 0, "empanadas": 6, "bebidas": 0},
    },
)


def _categoria(producto):
    # Traduce la clase real del producto a una categoria de negocio.
    # Las promociones trabajan con estas categorias simples y no con nombres de clases.
    if isinstance(producto, Pizza):
        return "pizzas"
    if isinstance(producto, Empanada):
        return "empanadas"
    if isinstance(producto, Bebida):
        return "bebidas"
    return "otros"


def _obtener_lineas(productos):
    # Normaliza el pedido a una lista con indice estable para poder repartir descuentos.
    lineas = []
    for indice, (producto, cantidad) in enumerate(productos):
        cantidad_entera = int(cantidad)
        subtotal = producto.calcular_precio() * cantidad_entera
        lineas.append(
            {
                "indice": indice,
                "producto": producto,
                "categoria": _categoria(producto),
                "cantidad": cantidad_entera,
                "subtotal": subtotal,
            }
        )
    return lineas


def _contar_categorias(lineas):
    # Suma cuantas unidades hay de cada categoria dentro del pedido normalizado.
    # Este conteo permite saber si el pedido alcanza los minimos de una promocion.
    cantidades = {"pizzas": 0, "empanadas": 0, "bebidas": 0}
    for linea in lineas:
        categoria = linea["categoria"]
        if categoria in cantidades:
            cantidades[categoria] += linea["cantidad"]
    return cantidades


def _cumple_requisitos(cantidades, requisitos):
    # Recorre los requisitos de una promocion y corta apenas falta una categoria.
    # Asi los combos no se aplican de forma parcial por error.
    for categoria, minimo in requisitos.items():
        if cantidades.get(categoria, 0) < minimo:
            return False
    return True


def _lineas_promocion(lineas, requisitos):
    # Devuelve solamente las lineas del pedido afectadas por la promo.
    # Por ejemplo, una promo de empanadas no debe descontar bebidas.
    categorias = [categoria for categoria, minimo in requisitos.items() if minimo > 0]
    return [linea for linea in lineas if linea["categoria"] in categorias]


def _calcular_descuentos_y_promos(productos):
    # Motor central de promociones: normaliza el pedido, revisa cada promo posible
    # y guarda el mejor descuento por linea para evitar acumulaciones duplicadas.
    lineas = _obtener_lineas(productos)
    cantidades = _contar_categorias(lineas)
    descuentos = {}
    promociones_por_linea = {}

    for promocion in PROMOCIONES:
        if not _cumple_requisitos(cantidades, promocion["requisitos"]):
            continue

        # Si dos promociones afectan la misma linea, se conserva el mayor descuento.
        # Asi evitamos descontar dos veces el mismo producto en combos superpuestos.
        for linea in _lineas_promocion(lineas, promocion["requisitos"]):
            descuento = linea["subtotal"] * promocion["porcentaje"]
            indice = linea["indice"]
            if descuento > descuentos.get(indice, 0):
                descuentos[indice] = descuento
                promociones_por_linea[indice] = promocion

    return lineas, descuentos, promociones_por_linea


def calcular_descuentos_por_linea(productos):
    # Funcion pensada para el detalle del pedido: devuelve el descuento por indice
    # de producto y permite calcular totales linea por linea.
    _lineas, descuentos, _promociones = _calcular_descuentos_y_promos(productos)
    return descuentos


def calcular_promociones_pedido(productos):
    # Funcion pensada para mostrar informacion visible: agrupa descuentos por promo
    # para que el ticket y la interfaz tengan un resumen claro.
    lineas, descuentos, promociones_por_linea = _calcular_descuentos_y_promos(productos)
    resumen = {}

    # Agrupa el descuento final por nombre de promocion para mostrarlo en carrito,
    # ticket y reportes sin depender de detalles internos de cada producto.
    for linea in lineas:
        descuento = descuentos.get(linea["indice"], 0)
        promocion = promociones_por_linea.get(linea["indice"])
        if not promocion or descuento <= 0:
            continue

        clave = promocion["nombre"]
        if clave not in resumen:
            resumen[clave] = {
                "tipo": promocion["tipo"],
                "nombre": promocion["nombre"],
                "descripcion": promocion["descripcion"],
                "cantidad": 0,
                "porcentaje": promocion["porcentaje"],
                "subtotal_base": 0,
                "descuento": 0,
            }

        resumen[clave]["cantidad"] += linea["cantidad"]
        resumen[clave]["subtotal_base"] += linea["subtotal"]
        resumen[clave]["descuento"] += descuento

    return list(resumen.values())
