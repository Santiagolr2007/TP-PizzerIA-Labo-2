import threading
from src.modelos.pedido import Pedido
from src.utils.excepciones import (PedidoInvalidoError,ProductoNoEncontradoError)
from src.utils.decoradores import registrar_log


class Pizzeria:
    def __init__(self, inventario, dinero_inicial=0):
        self.inventario = inventario # Guarda el inventario que utilizará la pizzería.
        self.__catalogo = {} # Guarda los productos usando el nombre como clave.
        self.__pedidos = [] # Guarda todos los pedidos creados.
        self.__ventas = [] # Guarda todas las ventas realizadas.
        self.__candado_ventas = threading.Lock() # Evita que dos hilos modifiquen las ventas al mismo tiempo.
        self.__dinero = dinero_inicial # Guarda el dinero inicial con el que cuenta la pizzería.

########

    def reponer_stock(self, ingrediente, cantidad):
        # Calcula el costo total de la reposición.
        costo_total = self.inventario.calcular_costo_reposicion(ingrediente,cantidad)
        # Verifica y descuenta el dinero antes de reponer.
        self.restar_dinero(costo_total)
        # Si hay dinero suficiente, repone el stock.
        self.inventario.reponer(ingrediente,cantidad)
        return costo_total

########

    def restar_dinero(self, monto):
        # Resta dinero de la caja de la pizzería.
        if monto < 0:
            raise ValueError("No se puede restar un monto negativo.")

        if monto > self.__dinero:
            raise ValueError(f"No hay dinero suficiente. Disponible: ${self.__dinero:.2f}, costo: ${monto:.2f}")
        self.__dinero -= monto

########

    def sumar_dinero(self, monto):
        # Suma dinero a la caja de la pizzería.
        if monto < 0:
            raise ValueError("No se puede sumar un monto negativo.")
        self.__dinero += monto

########

    def obtener_dinero(self):
        # Devuelve el dinero disponible de la pizzería.
        return self.__dinero

########

    def registrar_producto(self, producto):
        nombre_producto = producto.nombre # Obtiene el nombre del producto.
        self.__catalogo[nombre_producto] = producto # Agrega el producto al catálogo.

########

    def obtener_catalogo(self):
        catalogo = [] # Crea una lista para guardar los productos.
        for producto in self.__catalogo.values(): # Recorre todos los productos del diccionario.
            catalogo.append(producto)# Agrega cada producto a la lista.
        return catalogo

########

    @registrar_log
    def crear_pedido(self, cliente, items):
        if len(items) == 0:
            raise PedidoInvalidoError("Debe agregar al menos un producto.") # Verifica que el pedido tenga al menos un producto.

        pedido = Pedido(cliente) # Crea un nuevo pedido para el cliente.

        for item in items: # Recorre todos los productos solicitados.
            nombre_producto = item[0]
            cantidad = item[1]

            # Verifica que el producto exista en el catálogo.
            if nombre_producto not in self.__catalogo:
                raise ProductoNoEncontradoError(f"No existe el producto '{nombre_producto}'.")

            # Obtiene el objeto producto desde el catálogo.
            producto = self.__catalogo[nombre_producto]

            # Agrega el producto al pedido.
            pedido.agregar_producto(producto,cantidad)

        # Guarda el pedido en la lista general.
        self.__pedidos.append(pedido)

        return pedido

########

    def obtener_pedidos(self):
        copia_pedidos = [] # Crea una lista para devolver una copia de los pedidos.

        # Copia cada pedido a la nueva lista.
        for pedido in self.__pedidos:
            copia_pedidos.append(pedido)

        return copia_pedidos

########

    def obtener_pedidos_pendientes(self):
        pedidos_pendientes = [] # Crea una lista para guardar los pedidos pendientes.

        for pedido in self.__pedidos: # Recorre todos los pedidos.

            # Agrega solamente los pedidos pendientes.
            if pedido.estado == "pendiente":
                pedidos_pendientes.append(pedido)

        return pedidos_pendientes

#########

    @registrar_log
    def registrar_venta(self, pedido):
        # Suma el total del pedido al dinero recaudado.
        self.sumar_dinero(pedido.calcular_total())

        # Bloquea la lista para que dos hilos no registren ventas al mismo tiempo.
        with self.__candado_ventas:
            items_venta = pedido.generar_items_venta()
            for item_venta in items_venta:
                self.__ventas.append(item_venta)

#########

    @registrar_log
    def cargar_datos(self, datos):
        # Carga el dinero guardado si existe.
        self.__dinero = datos.get("dinero", self.__dinero)
        self.inventario.reemplazar_stock(datos["stock"])
        # Reemplaza el stock actual por el stock guardado.)
        pedidos_cargados = []
        mayor_id = 0

        # Reconstruye todos los objetos Pedido.
        for datos_pedido in datos["pedidos"]:
            pedido = Pedido.desde_dict(datos_pedido,self.__catalogo)
            pedidos_cargados.append(pedido)

            # Guarda el ID más alto encontrado.
            if pedido.pedido_id > mayor_id:
                mayor_id = pedido.pedido_id

        # Reemplaza los pedidos actuales por los pedidos cargados.
        self.__pedidos = pedidos_cargados
        # Evita que los nuevos pedidos repitan IDs existentes.
        Pedido._contador = mayor_id
        # Protege la lista mientras restaura las ventas.
        with self.__candado_ventas:
            self.__ventas = []

            for venta in datos["ventas"]:
                self.__ventas.append(venta)
        

#########

    def obtener_ventas(self):
        with self.__candado_ventas: # Bloquea el acceso mientras se copian las ventas.
            copia_ventas = [] # Crea una lista para devolver una copia.

            for venta in self.__ventas: # Copia cada venta a la nueva lista.
                copia_ventas.append(venta)

        return copia_ventas