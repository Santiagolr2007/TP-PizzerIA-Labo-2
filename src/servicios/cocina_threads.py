import queue
import threading
import time

from src.utils.decoradores import medir_tiempo, registrar_log


@registrar_log
def _cocinero(nombre, cola_pedidos, pizzeria):
    while True:
        pedido = cola_pedidos.get()

        try:
            if pedido is None:
                return

            print(f"{nombre} comenzo el pedido #{pedido.pedido_id}.")
            pedido.cambiar_estado("en preparacion")
            time.sleep(1)
            ingredientes = pedido.obtener_ingredientes_totales()
            pizzeria.inventario.descontar(ingredientes)
            pedido.cambiar_estado("listo")
            print(f"{nombre} dejo listo el pedido #{pedido.pedido_id}.")

        except Exception as error:
            try:
                if pedido is not None and pedido.estado in {"pendiente", "en preparacion"}:
                    pedido.cambiar_estado("cancelado")
            except Exception:
                pass

            print(f"{nombre} no pudo procesar el pedido: {error}")

        finally:
            cola_pedidos.task_done()


@medir_tiempo
def procesar_pedidos_con_hilos(pizzeria, cantidad_cocineros=2):
    pedidos = pizzeria.obtener_pedidos_pendientes()

    if not pedidos:
        print("No hay pedidos pendientes.")
        return

    cola_pedidos = queue.Queue()
    hilos = []

    for numero in range(cantidad_cocineros):
        hilo = threading.Thread(
            target=_cocinero,
            args=(f"Cocinero {numero + 1}", cola_pedidos, pizzeria),
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

    print("Todos los pedidos fueron procesados.")
