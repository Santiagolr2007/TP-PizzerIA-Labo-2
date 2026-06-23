import queue
import threading
import time

from src.utils.decoradores import medir_tiempo, registrar_log


TIEMPOS_PRODUCTO = {
    "Pizza": 6,
    "Empanada": 2,
    "Bebida": 1,
}

ESTACIONES_PRODUCTO = {
    "Pizza": "Horno",
    "Empanada": "Empanadas",
    "Bebida": "Bebidas",
}


def calcular_tiempo_estimado(pedido):
    minutos = 0

    for producto, cantidad in pedido.productos:
        tipo = producto.__class__.__name__
        minutos += TIEMPOS_PRODUCTO.get(tipo, 3) * cantidad

    return max(1, min(minutos, 45))


def determinar_estaciones_pedido(pedido):
    estaciones = []

    for producto, _cantidad in pedido.productos:
        tipo = producto.__class__.__name__
        estacion = ESTACIONES_PRODUCTO.get(tipo, "General")
        if estacion not in estaciones:
            estaciones.append(estacion)

    if len(estaciones) == 1:
        return estaciones[0]

    return "Mixta: " + ", ".join(estaciones)


def _emitir(callback, evento):
    if callback is not None:
        callback(evento)


def _crear_evento(tipo, pedido, mensaje):
    return {
        "tipo": tipo,
        "pedido_id": pedido.pedido_id,
        "cliente": pedido.cliente,
        "estado": pedido.estado,
        "cocinero": pedido.cocinero_asignado or "-",
        "estacion": pedido.estacion_cocina or "-",
        "tiempo_estimado": pedido.tiempo_estimado,
        "tiempo_restante": pedido.tiempo_restante,
        "mensaje": mensaje,
    }


@registrar_log
def _cocinero(nombre, cola_pedidos, pizzeria, callback=None, velocidad=0.15):
    while True:
        pedido = cola_pedidos.get()

        try:
            if pedido is None:
                return

            estacion = determinar_estaciones_pedido(pedido)
            tiempo_estimado = calcular_tiempo_estimado(pedido)
            pedido.asignar_cocina(nombre, estacion, tiempo_estimado)
            pedido.cambiar_estado("en preparacion")

            ingredientes = pedido.obtener_ingredientes_totales()
            pizzeria.inventario.descontar(ingredientes)
            _emitir(
                callback,
                _crear_evento(
                    "inicio",
                    pedido,
                    f"{nombre} tomo el pedido #{pedido.pedido_id} en {estacion}.",
                ),
            )

            for restante in range(tiempo_estimado, 0, -1):
                pedido.actualizar_tiempo_restante(restante)
                time.sleep(velocidad)

            pedido.finalizar_cocina()
            pedido.cambiar_estado("listo")
            _emitir(
                callback,
                _crear_evento(
                    "listo",
                    pedido,
                    f"{nombre} dejo listo el pedido #{pedido.pedido_id}.",
                ),
            )

        except Exception as error:
            try:
                if pedido is not None and pedido.estado in {"pendiente", "en preparacion"}:
                    pedido.registrar_cancelacion(error)
                    pedido.cambiar_estado("cancelado")
                    _emitir(
                        callback,
                        _crear_evento(
                            "cancelado",
                            pedido,
                            f"Pedido #{pedido.pedido_id} cancelado en cocina: {error}",
                        ),
                    )
            except Exception:
                pass

        finally:
            cola_pedidos.task_done()


@medir_tiempo
def procesar_pedidos_con_hilos(pizzeria, cantidad_cocineros=2, callback=None, velocidad=0.15):
    pedidos = pizzeria.obtener_pedidos_pendientes()

    if not pedidos:
        return []

    cola_pedidos = queue.Queue()
    hilos = []

    for numero in range(cantidad_cocineros):
        hilo = threading.Thread(
            target=_cocinero,
            args=(f"Cocinero {numero + 1}", cola_pedidos, pizzeria, callback, velocidad),
            daemon=False,
        )
        hilo.start()
        hilos.append(hilo)

    for pedido in pedidos:
        cola_pedidos.put(pedido)

    cola_pedidos.join()

    for _hilo in hilos:
        cola_pedidos.put(None)

    cola_pedidos.join()

    for hilo in hilos:
        hilo.join()

    return pedidos
