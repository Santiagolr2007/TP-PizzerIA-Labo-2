from src.modelos.producto import Bebida, Empanada, Pizza
from src.servicios.cocina_threads import calcular_tiempo_estimado, determinar_estaciones_pedido
from src.interfaz.formateadores import (
    capitalizar_visible,
    estado_visible,
    formato_moneda,
    formato_numero,
    nombre_ingrediente_visible,
    obtener_resumen_productos,
)


def resumen_estados(pizzeria):
    resumen = {
        "pendiente": 0,
        "en preparacion": 0,
        "listo": 0,
        "en camino": 0,
        "entregado": 0,
        "cancelado": 0,
    }
    for pedido in pizzeria.obtener_pedidos():
        if pedido.estado in resumen:
            resumen[pedido.estado] += 1
    return resumen


def detalle_producto(producto):
    if isinstance(producto, Pizza):
        extras = []
        for ingrediente, cantidad in producto.ingredientes_extra.items():
            extras.append(f"{nombre_ingrediente_visible(ingrediente)} x{cantidad}")
        detalle = f"TamaÃ±o {producto.tamanio}"
        if extras:
            detalle += " | " + ", ".join(extras)
        return detalle

    if isinstance(producto, Empanada):
        return f"Relleno: {nombre_ingrediente_visible(producto.ingrediente_relleno)}"

    if isinstance(producto, Bebida):
        ingrediente = producto.ingrediente_stock or "sin control"
        return f"Stock asociado: {nombre_ingrediente_visible(ingrediente)}"

    return ""


def filas_catalogo(pizzeria, filtro=""):
    filtro = filtro.lower().strip()
    filas = []
    for numero, producto in enumerate(pizzeria.obtener_catalogo(), start=1):
        fila = {
            "numero": numero,
            "producto": producto.nombre,
            "categoria": producto.__class__.__name__,
            "detalle": detalle_producto(producto),
            "precio": formato_moneda(producto.calcular_precio()),
        }
        texto_busqueda = f"{fila['producto']} {fila['categoria']} {fila['detalle']}".lower()
        if filtro and filtro not in texto_busqueda:
            continue
        filas.append(fila)
    return filas


def filas_pedidos(pizzeria):
    filas = []
    for pedido in pizzeria.obtener_pedidos():
        filas.append(
            {
                "pedido_id": pedido.pedido_id,
                "cliente": pedido.cliente,
                "entrega": pedido.tipo_entrega,
                "direccion": pedido.direccion or "-",
                "estado": estado_visible(pedido.estado),
                "productos": obtener_resumen_productos(pedido),
                "descuento": formato_moneda(pedido.calcular_descuento_total()),
                "total": formato_moneda(pedido.calcular_total()),
            }
        )
    return filas


def tiempo_pedido_visible(pedido):
    if pedido.estado == "en preparacion":
        return f"{pedido.tiempo_restante or pedido.tiempo_estimado} min"

    if pedido.estado == "pendiente":
        return f"{calcular_tiempo_estimado(pedido)} min est."

    if pedido.estado == "listo":
        return "Listo"

    return "-"


def filas_cocina(pizzeria):
    # Cocina muestra pedidos activos: pendientes, en preparacion, listos y delivery en camino.
    # Se excluyen entregados/cancelados porque ya no necesitan trabajo operativo.
    filas = []
    estados_cocina = {"pendiente", "en preparacion", "listo", "en camino"}

    for pedido in pizzeria.obtener_pedidos():
        if pedido.estado not in estados_cocina:
            continue

        filas.append(
            {
                "pedido_id": pedido.pedido_id,
                "cliente": pedido.cliente,
                "estado": estado_visible(pedido.estado),
                "estacion": pedido.estacion_cocina or determinar_estaciones_pedido(pedido),
                "cocinero": pedido.cocinero_asignado or "-",
                "tiempo": tiempo_pedido_visible(pedido),
                "entrega": pedido.tipo_entrega,
                "direccion": pedido.direccion or "-",
            }
        )

    return filas


def filas_estaciones(pizzeria):
    resumen = {}

    for pedido in pizzeria.obtener_pedidos():
        if pedido.estado in {"entregado", "cancelado"}:
            continue

        estacion = pedido.estacion_cocina or determinar_estaciones_pedido(pedido)
        if estacion not in resumen:
            resumen[estacion] = {"estacion": estacion, "pendientes": 0, "en_preparacion": 0, "listos": 0}

        if pedido.estado == "pendiente":
            resumen[estacion]["pendientes"] += 1
        elif pedido.estado == "en preparacion":
            resumen[estacion]["en_preparacion"] += 1
        elif pedido.estado == "listo":
            resumen[estacion]["listos"] += 1

    return list(resumen.values())


def filas_eventos_cocina(cocina_eventos):
    filas = []
    for evento in cocina_eventos[:10]:
        filas.append(
            {
                "pedido_id": evento.get("pedido_id", "-"),
                "evento": estado_visible(evento.get("tipo", "")),
                "cocinero": evento.get("cocinero", "-"),
                "estacion": evento.get("estacion", "-"),
                "tiempo": f"{evento.get('tiempo_restante', 0)} min",
                "mensaje": evento.get("mensaje", ""),
            }
        )
    return filas


def filas_stock(pizzeria):
    filas = []
    for fila in pizzeria.inventario.obtener_stock_detallado():
        cantidad = fila["cantidad"]
        filas.append(
            {
                "ingrediente": capitalizar_visible(fila["ingrediente"]),
                "cantidad": formato_numero(cantidad),
                "precio_unitario": formato_moneda(fila["precio_unitario"]),
                "valor_total_stock": formato_moneda(fila["valor_total_stock"]),
                "estado": "Reponer" if cantidad <= 5 else "Disponible",
            }
        )
    filas.sort(key=lambda fila: fila["ingrediente"])
    return filas


def stock_bajo(pizzeria):
    cantidad = 0
    for fila in pizzeria.inventario.obtener_stock_detallado():
        if fila["cantidad"] <= 5:
            cantidad += 1
    return cantidad


def datos_grafico_estados(pizzeria):
    estados = resumen_estados(pizzeria)
    return [
        ("Pend.", estados["pendiente"]),
        ("Prep.", estados["en preparacion"]),
        ("Listos", estados["listo"]),
        ("Camino", estados["en camino"]),
        ("Entreg.", estados["entregado"]),
        ("Cancel.", estados["cancelado"]),
    ]


def datos_grafico_productos(pizzeria):
    ventas_por_producto = {}
    for venta in pizzeria.obtener_ventas():
        producto = str(venta.get("producto", "")).strip()
        if not producto:
            continue
        ventas_por_producto[producto] = ventas_por_producto.get(producto, 0) + float(venta.get("subtotal", 0) or 0)

    datos = sorted(ventas_por_producto.items(), key=lambda item: item[1], reverse=True)
    return datos[:6]


def datos_grafico_stock_bajo(pizzeria):
    filas = []
    for item in pizzeria.inventario.obtener_stock_detallado():
        filas.append((capitalizar_visible(item["ingrediente"]), float(item["cantidad"])))
    filas.sort(key=lambda item: item[1])
    return filas[:6]


def datos_grafico_descuentos(pizzeria):
    total_descuento = 0
    for venta in pizzeria.obtener_ventas():
        total_descuento += float(venta.get("descuento", 0) or 0)
    return [("Promos", total_descuento)] if total_descuento else []
